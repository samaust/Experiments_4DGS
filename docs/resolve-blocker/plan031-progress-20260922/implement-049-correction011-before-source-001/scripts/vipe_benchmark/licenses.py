"""Hash-bound review of exact asset and installed dependency license evidence."""
from .backends import REQUIRED_ASSETS
from .config import load
from .files import object_hash, read_json, verify_record
from .ledger import Ledger


def subject_manifest(component, qualification):
    inventory = qualification.get('runtime', {}).get('inventory')
    if not inventory:
        raise ValueError('exact installed runtime inventory is missing')
    packages = read_json(verify_record(inventory)['path'])['packages']
    assets = qualification.get('assets', {})
    subjects = {'asset:' + key: assets[key] for key in REQUIRED_ASSETS.get(component, ())}
    for package in packages:
        key = 'package:' + package['name'].lower().replace('_', '-') + '==' + package['version']
        if key in subjects:
            raise ValueError('duplicate installed dependency identity')
        subjects[key] = package
    return dict(component=component, inventory=inventory, subjects=subjects)


def assess(local, component, qualification):
    manifest = subject_manifest(component, qualification)
    scope_hash = object_hash(manifest)
    reviews = [event for event in Ledger(local / 'ledger.jsonl', load()).events()
               if event['event'] == 'license_assessment' and event.get('component') == component]
    missing = dict(commercial_permission='unverified', non_agpl='unverified',
                   license_evidence=dict(status='unverified', subject_manifest_sha256=scope_hash,
                       subject_count=len(manifest['subjects']), reasons=[
                           'No completed license review binds this exact asset and installed dependency closure.']))
    if not reviews:
        return missing
    record = reviews[-1]['evidence']
    review = read_json(verify_record(record)['path'])
    if review.get('subject_manifest_sha256') != scope_hash or review.get('component') != component:
        raise ValueError('license review does not match exact current assets and installed runtime')
    if not review.get('reviewer') or not review.get('reviewed_utc'):
        raise ValueError('license evidence requires identified dated review')
    entries = review.get('subjects', {})
    if set(entries) != set(manifest['subjects']):
        raise ValueError('license review omitted or invented closure subjects')
    reasons = []
    for subject, entry in entries.items():
        for preference in ('commercial_permission', 'non_agpl'):
            if entry.get(preference) not in ('verified', 'restricted', 'unverified'):
                raise ValueError('invalid license preference assessment')
            if entry[preference] == 'verified' and not entry.get('evidence'):
                raise ValueError('verified permission requires exact evidence')
            if entry[preference] != 'verified':
                reasons.append(f'{subject}: {preference} {entry[preference]}: {entry.get("reason", "no supporting grant")}')
        if not entry.get('reason'):
            raise ValueError('license assessment requires a reason for every subject')
        for evidence in entry.get('evidence', []):
            verify_record(evidence)
    decisions = {}
    for preference in ('commercial_permission', 'non_agpl'):
        statuses = {entry[preference] for entry in entries.values()}
        decisions[preference] = ('restricted' if 'restricted' in statuses else
                                'unverified' if 'unverified' in statuses or not statuses else 'verified')
    return dict(decisions, license_evidence=dict(status='reviewed', assessment=record,
                subject_manifest_sha256=scope_hash, subject_count=len(entries), reasons=reasons,
                platform_terms=review.get('platform_terms', [])))

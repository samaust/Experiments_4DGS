"""Remaining map-stage bounds after independently accepted, retained setup assets."""
from pathlib import Path

from .files import object_hash, read_json, verify_record


def _require(condition, reason):
    if not condition:
        raise ValueError(reason)


def remaining_map_allocation(proposal, setup, events, run_root, assets, *, verifier=verify_record):
    """Credit only verified required assets already included in live used totals.

    Callers must supply events from the checked ledger; the allocator recomputes
    this under its lock. No runtime, cache, source or historical allocation is
    credited. The approved proposal and cumulative used totals remain unchanged.
    """
    candidate = proposal['candidate']
    job = f'plan069-{candidate}-setup-001'
    root = Path(run_root).resolve()
    setup_record = verifier(setup)
    _require(setup_record == setup and Path(setup_record['path']) == root / 'jobs' / job / 'result.json',
             'owned completed setup result required for map allowance')
    result = read_json(setup_record['path'])
    allocation = dict(proposal['allocation'])
    setup_schema = ('plan069-video-setup-result/v1' if candidate in ('D9', 'D10')
                    else 'plan069-depth-setup-result/v1')
    _require(result.get('schema') == setup_schema and
             result.get('record_kind') == 'actual' and result.get('status') == 'complete' and
             result.get('candidate') == candidate and result.get('job_id') == job and
             result.get('source_revision') == proposal['candidate_config']['code']['revision'] and
             result.get('weight_revision') == proposal['candidate_config']['weights']['revision'],
             'exact completed setup source and model required for map allowance')
    authorized = [e for e in events if e.get('event') == 'depth_setup_authorized' and
                  e.get('candidate') == candidate]
    reserves = [e for e in events if e.get('event') == 'reserve' and e.get('job_id') == job]
    finishes = [e for e in events if e.get('event') == 'finish' and e.get('job_id') == job]
    _require(len(authorized) == len(reserves) == len(finishes) == 1,
             'one accepted setup authorization reservation and finish required')
    grant, reserve, finish = authorized[0], reserves[0], finishes[0]
    _require(events.index(grant) < events.index(reserve) < events.index(finish),
             'accepted setup ledger transition order required')
    review = verifier(result['review'])
    authorization = verifier(result['authorization'])
    reviewed = read_json(review['path'])
    approved = read_json(authorization['path'])
    _require(proposal.get('max_attempts') == 1 and
             reviewed.get('schema') == 'plan069-depth-execution-review/v1' and reviewed.get('status') == 'REVIEW' and
             approved.get('schema') == 'plan069-depth-user-authorization/v1' and
             [p for p in reviewed.get('proposals', []) if p.get('candidate') == candidate] == [proposal] and
             approved.get('status') == 'DO' and approved.get('review') == review and
             any(g.get('candidate') == candidate and g.get('status') == 'approved' and
                 g.get('schema') == 'plan069-depth-execution-approval/v1' and g.get('max_attempts') == 1 and
                 g.get('proposal_sha256') == object_hash(proposal)
                 for g in approved.get('candidate_approvals', [])) and
             grant.get('review') == review and grant.get('authorization') == authorization and
             grant.get('proposal_sha256') == object_hash(proposal),
             'setup allocation approval lineage differs from map proposal')
    request_record = verifier(reserve['evidence']['request'])
    request = read_json(request_record['path'])
    _require(request_record == reserve['evidence']['request'] and
             Path(request_record['path']) == root / 'requests' / (job + '.json') and
             request.get('schema') == 'plan069-depth-setup-request/v1' and
             request.get('candidate') == candidate and request.get('job_id') == job and
             request.get('record_kind') == 'actual' and request.get('review') == review and
             request.get('authorization') == authorization and
             request.get('ledger_path') == str(root / 'ledger.jsonl') and
             reserve.get('resource') == 'setup' and reserve['evidence'].get('review') == review and
             reserve['evidence'].get('authorization') == authorization and
             finish.get('resource') == 'setup' and finish.get('status') == 'complete' and
             finish.get('result') == setup_record and finish.get('cleanup_confirmed') is True and
             finish.get('cleanup_uncertain') is False and finish.get('surviving_pids') == [] and
             finish.get('deadline_exceeded') is False,
             'clean exact setup completion required for map allowance')
    inventory = read_json(verifier(proposal['required_assets'])['path'])['candidates'][candidate]['files']
    expected = {(r['repository'], r['path']): r for r in inventory}
    by_key = {(r['repository'], r['path']): r for r in assets}
    _require(len(expected) == len(inventory) == len(by_key) == len(assets) and set(expected) == set(by_key),
             'exact required setup assets needed for map allowance')
    if result.get('assets') is not None:
        _require(result['assets'] == assets, 'map assets differ from accepted setup assets')
    else:
        _require(len(assets) == 1 and result.get('checkpoint') == assets[0]['record'],
                 'map checkpoint differs from accepted setup')
    sizes: dict[tuple[int, int], int] = {}
    for key, row in by_key.items():
        record = verifier(row['record'])
        path = Path(record['path'])
        required = expected[key]
        _require(record == row['record'] and path.is_relative_to(root / 'jobs' / job) and
                 not path.is_symlink() and record['bytes'] == required['bytes'] and
                 (required.get('lfs_sha256') is None or required['lfs_sha256'] == record['sha256']),
                 'retained exact owned setup asset required for map allowance')
        info = path.stat()
        sizes[info.st_dev, info.st_ino] = max(sizes.get((info.st_dev, info.st_ino), 0), record['bytes'])
    credit = sum(sizes.values())
    _require(type(result.get('bytes_received')) is int and
             credit <= result['bytes_received'] <= allocation['download_bytes'] and
             0 < credit < allocation['artifact_bytes'],
             'setup asset credit exceeds accounted approved bounds')
    for allocation_key in ('download_bytes', 'artifact_bytes'):
        allocation[allocation_key] -= credit
    return dict(allocation=allocation, credited_assets_bytes=credit,
                setup=setup_record, setup_finish_event_sha256=finish['event_sha256'])


def owned_slot_bytes(run_root, candidate):
    """Count all retained candidate job revisions, including preserved failures."""
    from .budgets import directory_bytes
    jobs = Path(run_root).resolve() / 'jobs'
    total = 0
    for path in jobs.glob(f'plan069-{candidate}-*'):
        _require(not path.is_symlink(), 'owned candidate job must not be a symlink')
        if path.is_dir():
            total += directory_bytes(path)
    return total


def bind_slot_byte_budget(proposal, stage, events, run_root, reading):
    """Freeze conservative shared setup overhead and unchanged whole-slot caps."""
    candidate = proposal['candidate']
    grants = [event for event in events if event.get('event') == 'depth_setup_authorized'
              and event.get('candidate') == candidate]
    _require(len(grants) == 1, 'exact setup baseline required for whole-slot budget')
    baseline = grants[0]['resource_snapshot']
    from .depth_budget_reconciliation import causal_credits
    later = [row for row in events if row.get('event') == 'depth_setup_bytes_reconciled'
             and row.get('sequence', -1) > grants[0].get('sequence', len(events))
             and row.get('candidate') != candidate]
    credits = causal_credits(run_root, grants[0], events) if later else None
    effective = dict(reading)
    if credits is not None:
        for key in ('download_bytes', 'artifact_bytes'):
            effective[key] = max(reading[key], credits['snapshot'][key]) - credits[key]
    limits = {}
    for key in ('download_bytes', 'artifact_bytes'):
        _require(type(baseline.get(key)) is int and baseline[key] >= 0 and
                 type(effective.get(key)) is int and effective[key] >= baseline[key],
                 'accounted monotonic setup baseline required for whole-slot budget')
        limits[key] = baseline[key] + proposal['allocation'][key]
        _require(effective[key] <= limits[key], key + ' whole-slot allocation exceeded')
    owned = owned_slot_bytes(run_root, candidate)
    overhead = max(0, effective['artifact_bytes'] - baseline['artifact_bytes'] - owned)
    _require(owned + overhead <= proposal['allocation']['artifact_bytes'],
             'retained setup artifacts exceed whole-slot allocation')
    budget = dict(schema='plan069-depth-slot-byte-budget/v1', candidate=candidate,
                proposal_sha256=object_hash(proposal), setup=stage['setup'],
                setup_finish_event_sha256=stage['setup_finish_event_sha256'],
                setup_baseline=baseline, absolute_limits=limits,
                shared_setup_artifact_bytes=overhead)
    if credits is not None:
        budget.update(schema='plan069-depth-slot-byte-budget/v2',
            setup_grant_sha256=grants[0]['event_sha256'],
            causal_reconciliation_events=credits['protected_events'])
    return budget


def check_slot_byte_budget(proposal, budget, run_root, reading, *, historical=False):
    """Check active whole-slot caps; late CPU diagnostics check retained scope.

    Historical CPU callers separately prove no new downloads during their stage.
    Their artifact guard retains frozen shared setup overhead without charging
    unrelated later jobs to the old candidate.
    """
    _require(budget.get('schema') in ('plan069-depth-slot-byte-budget/v1', 'plan069-depth-slot-byte-budget/v2') and
             budget.get('candidate') == proposal['candidate'] and
             budget.get('proposal_sha256') == object_hash(proposal) and
             type(budget.get('shared_setup_artifact_bytes')) is int and
             budget['shared_setup_artifact_bytes'] >= 0 and
             all(type(budget.get('setup_baseline', {}).get(key)) is int and
                 budget['setup_baseline'][key] >= 0 and
                 budget.get('absolute_limits', {}).get(key) ==
                    budget['setup_baseline'][key] + proposal['allocation'][key]
                 for key in ('download_bytes', 'artifact_bytes')),
             'exact approved whole-slot byte budget required')
    effective = dict(reading)
    if not historical and budget['schema'] == 'plan069-depth-slot-byte-budget/v2':
        from .config import load
        from .ledger import Ledger
        from .depth_budget_reconciliation import causal_credits
        events = Ledger(Path(run_root) / 'ledger.jsonl', load()).events()
        grants = [row for row in events if row.get('event') == 'depth_setup_authorized' and
                  row.get('event_sha256') == budget.get('setup_grant_sha256')]
        _require(len(grants) == 1 and grants[0].get('candidate') == proposal['candidate'] and
                 grants[0].get('resource_snapshot') == budget['setup_baseline'],
                 'exact protected v2 setup baseline required')
        credits = causal_credits(run_root, grants[0], events, budget.get('causal_reconciliation_events'))
        for key in ('download_bytes', 'artifact_bytes'):
            _require(type(reading.get(key)) is int, 'accounted live byte reading required')
            effective[key] = max(reading[key], credits['snapshot'][key]) - credits[key]
    if not historical:
        for key in ('download_bytes', 'artifact_bytes'):
            _require(type(effective.get(key)) is int and
                     budget['setup_baseline'][key] <= effective[key] <= budget['absolute_limits'][key],
                     key + ' whole-slot allocation exceeded')
    _require(owned_slot_bytes(run_root, proposal['candidate']) +
             budget['shared_setup_artifact_bytes'] <= proposal['allocation']['artifact_bytes'],
             'retained candidate artifacts exceed whole-slot allocation')


def historical_slot_byte_guard(ledger, candidate):
    """Return a no-download CPU guard for an already admitted native slot."""
    from .budgets import budget_snapshot
    events = ledger.events()
    allocations = [event for event in events if event.get('event') == 'depth_attempt_authorized'
                   and event.get('candidate') == candidate]
    if len(allocations) != 1 or allocations[0].get('slot_byte_budget') is None:
        _require(candidate not in ('D5', 'D6', 'D8', 'D9', 'D10', 'D11'),
                 'native depth diagnostics require whole-slot byte proof')
        return lambda: None
    allocation = allocations[0]
    review = read_json(verify_record(allocation['review'])['path'])
    proposal = next(row for row in review['proposals'] if row['candidate'] == candidate)
    budget = allocation['slot_byte_budget']
    setup_grants = [event for event in events if event.get('event') == 'depth_setup_authorized'
                    and event.get('candidate') == candidate]
    finishes = [event for event in events if event.get('event') == 'finish'
                and event.get('job_id') == f'plan069-{candidate}-setup-001']
    stage = allocation.get('map_stage_allowance') or {}
    _require(len(setup_grants) == len(finishes) == 1 and
             setup_grants[0].get('resource_snapshot') == budget.get('setup_baseline') and
             allocation.get('proposal_sha256') == budget.get('proposal_sha256') == object_hash(proposal) and
             stage.get('setup') == budget.get('setup') and
             stage.get('setup_finish_event_sha256') == budget.get('setup_finish_event_sha256') and
             finishes[0].get('event_sha256') == budget.get('setup_finish_event_sha256') and
             finishes[0].get('result') == budget.get('setup') and
             finishes[0].get('resource') == 'setup' and finishes[0].get('status') == 'complete' and
             finishes[0].get('cleanup_confirmed') is True and
             finishes[0].get('cleanup_uncertain') is False and
             finishes[0].get('surviving_pids') == [] and finishes[0].get('deadline_exceeded') is False,
             'historical whole-slot setup lineage changed')
    baseline = budget_snapshot(ledger.path.parent)['download_bytes']

    def check():
        reading = budget_snapshot(ledger.path.parent)
        _require(reading['download_bytes'] == baseline, 'CPU diagnostics must not acquire new downloads')
        check_slot_byte_budget(proposal, allocation['slot_byte_budget'], ledger.path.parent,
                               reading, historical=True)
    check()
    return check


def historical_slot_output_guard(ledger, candidate, output):
    """Check only the new CPU output directory between full historical checks.

    The caller first creates ``historical_slot_byte_guard`` for accepted setup
    lineage and download baseline, then repeats that full guard before accounting.
    Freeze all other retained revisions here; reserve exact shared overhead from
    the same immutable proposal rather than a second candidate allocation.
    """
    from .budgets import directory_bytes
    root = ledger.path.resolve().parent
    output = Path(output).resolve()
    _require(output.parent == root / 'jobs' and
             output.name.startswith(f'plan069-{candidate}-anchor-previews-'),
             'owned CPU preview output directory required')
    allocations = [event for event in ledger.events()
                   if event.get('event') == 'depth_attempt_authorized' and
                   event.get('candidate') == candidate]
    _require(len(allocations) == 1, 'exact whole-slot preview authorization required')
    allocation = allocations[0]
    budget = allocation.get('slot_byte_budget')
    _require(budget is not None, 'native depth diagnostics require whole-slot byte proof')
    review = verify_record(allocation['review'])
    _require(review == allocation['review'], 'exact preview review file record required')
    proposal = next(row for row in read_json(review['path'])['proposals']
                    if row['candidate'] == candidate)
    check_slot_byte_budget(proposal, budget, root, {}, historical=True)
    other_owned = owned_slot_bytes(root, candidate) - directory_bytes(output)
    available = proposal['allocation']['artifact_bytes'] - budget['shared_setup_artifact_bytes'] - other_owned

    def check(additional_bytes=0):
        _require(type(additional_bytes) is int and additional_bytes >= 0 and
                 directory_bytes(output) + additional_bytes <= available,
                 'next preview output exceeds remaining whole-slot artifact headroom')
    check()
    return check

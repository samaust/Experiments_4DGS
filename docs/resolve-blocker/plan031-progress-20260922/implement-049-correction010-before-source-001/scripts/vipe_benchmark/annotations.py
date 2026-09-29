"""Admission of independently reviewed human truth, never inferred candidate truth."""
import numpy as np

from .access import Identity, annotation_identities
from .files import load_array, object_hash, verify_record

HOURS = dict(primary=72., independent_review=24., adjudication=8., static_feature_review=8.)
INSTANCE_FLAGS = {'visibility', 'occlusion', 'blur', 'tiny_ball', 'role_uncertain'}
IMAGE_FLAGS = {'stationary_people', 'spectators', 'shadows', 'changing_displays', 'illumination_changes', 'uncertain_motion'}


def template(inputs, config):
    lookup = {Identity(**r['identity']).key(): r for r in inputs['rgb']}
    images = []
    for identity in annotation_identities(config):
        row = lookup[identity.key()]
        images.append(dict(identity=identity.record(), rgb=row['rgb'], K=row['K'], grid=row['grid'],
                           valid=row['valid'], static_feature_locations=row.get('static_feature_locations', []),
                           final_layers=None, instances=None, tags=None, primary_revision=None,
                           review_record=None, adjudication_record=None, static_feature_review=None,
                           status='awaiting external annotation and independent review'))
    pairs = [dict(camera=c, pair_start=t, associations=None)
             for c in config['diagnostic_cameras'] for t in config['pair_starts']]
    return dict(schema='vipe-benchmark-annotations/v1', status='incomplete',
                contributors={}, person_hours={k: 0. for k in HOURS}, images=images, pairs=pairs,
                blinded_to_candidate_outputs=True, truth_source='external human annotation required')


def validate(bundle, inputs, config):
    expected = template(inputs, config)
    contributors = bundle.get('contributors', {})
    for role_name in ('primary', 'independent_review'):
        person = contributors.get(role_name, {})
        if not person.get('id') or person.get('kind') != 'external_human' or not person.get('attestation'):
            raise ValueError(f'{role_name}: external contributor and attestation required')
        verify_record(person['attestation'])
    if contributors['primary']['id'] == contributors['independent_review']['id']:
        raise ValueError('primary annotator and independent reviewer must differ')
    if bundle.get('blinded_to_candidate_outputs') is not True:
        raise ValueError('independent review must be blinded to candidate outputs, IDs and scores')
    hours = bundle.get('person_hours', {})
    if set(hours) != set(HOURS) or any(not isinstance(hours[k], (int, float)) or
            not np.isfinite(hours[k]) or not 0 <= hours[k] <= cap for k, cap in HOURS.items()):
        raise ValueError('annotation hours missing or outside their separate allocations')
    expected_by_key = {Identity(**r['identity']).key(): r for r in expected['images']}
    actual_by_key = {Identity(**r['identity']).key(): r for r in bundle['images']}
    if len(actual_by_key) != len(bundle['images']) or set(actual_by_key) != set(expected_by_key):
        raise ValueError('all 232 unique annotation images are required exactly once')
    instance_ids = {}
    for key, row in actual_by_key.items():
        parent = expected_by_key[key]
        for field in ('rgb', 'K', 'grid', 'valid', 'static_feature_locations'):
            if row[field] != parent[field]:
                raise ValueError(f'{key}: changed image/grid/feature provenance')
        if row.get('status') != 'reviewed-adjudicated':
            raise ValueError(f'{key}: review/adjudication incomplete')
        for field in ('primary_revision', 'review_record', 'adjudication_record', 'final_layers'):
            if not row.get(field):
                raise ValueError(f'{key}: missing {field}')
            verify_record(row[field])
        from .files import read_json
        review = read_json(row['review_record']['path'])
        adjudication = read_json(row['adjudication_record']['path'])
        if (review.get('reviewer_id') != contributors['independent_review']['id'] or
                review.get('primary_revision_sha256') != row['primary_revision']['sha256'] or
                review.get('blind_to_outputs_methods_scores') is not True or
                adjudication.get('review_sha256') != row['review_record']['sha256'] or
                adjudication.get('final_layers_sha256') != row['final_layers']['sha256'] or
                adjudication.get('unresolved_disagreements') != 0):
            raise ValueError(f'{key}: review/adjudication evidence does not bind the final truth')
        if not isinstance(row.get('tags'), dict) or not IMAGE_FLAGS <= set(row['tags']):
            raise ValueError(f'{key}: missing image strata')
        with load_array(row['final_layers']) as layers:
            required = {'instances', 'changing', 'valid', 'ignored'}
            if not required <= set(layers.files) or any(layers[k].shape != (540, 960) for k in required):
                raise ValueError(f'{key}: missing annotation layers or wrong grid')
            labels = layers['instances']
            if labels.dtype != np.int32 or any(layers[k].dtype != np.bool_ for k in required - {'instances'}):
                raise ValueError(f'{key}: annotation dtypes changed')
            valid = load_array(row['valid'])
            if not np.array_equal(valid, layers['valid']) or (labels[~valid] != -1).any() or (labels[valid] < 0).any():
                raise ValueError(f'{key}: invalid footprint or instance labels')
            ids = {str(int(i)) for i in np.unique(labels) if i > 0}
            if row.get('instances') is None or set(row['instances']) != ids:
                raise ValueError(f'{key}: missing instance metadata')
            for iid, metadata in row['instances'].items():
                if metadata.get('class') not in ('person', 'basketball') or not INSTANCE_FLAGS <= set(metadata):
                    raise ValueError(f'{key}/{iid}: missing semantic/visibility metadata')
                if metadata['class'] == 'person' and metadata.get('role') not in ('player', 'other-person', 'uncertain'):
                    raise ValueError(f'{key}/{iid}: person role must be independently annotated')
            instance_ids[key] = {int(i) for i in ids}
        reviewed_features = row.get('static_feature_review')
        if not isinstance(reviewed_features, list) or len(reviewed_features) != len(parent['static_feature_locations']):
            raise ValueError(f'{key}: every selected static feature must be reviewed')
        if any(r.get('suitable') not in (True, False, 'uncertain') or r.get('index') != point['index']
               for r, point in zip(reviewed_features, parent['static_feature_locations'])):
            raise ValueError(f'{key}: static feature review mismatched')
    pairs = {(r['camera'], r['pair_start']): r for r in bundle['pairs']}
    if len(pairs) != len(bundle['pairs']) or set(pairs) != {(r['camera'], r['pair_start']) for r in expected['pairs']}:
        raise ValueError('all independently annotated reconstruction pair associations are required')
    for (camera, start), row in pairs.items():
        associations = row.get('associations')
        if not isinstance(associations, list):
            raise ValueError('pair associations incomplete')
        for field, frame in [('first_id', start), ('second_id', start + 1)]:
            key = Identity('reconstruction', camera, frame).key()
            ids = [r[field] for r in associations if r[field] is not None]
            if len(ids) != len(set(ids)) or set(ids) != instance_ids[key]:
                raise ValueError('missing/duplicate visible pair identities, births or disappearances')
        if any(r['first_id'] is None and r['second_id'] is None for r in associations):
            raise ValueError('empty pair association')
    return dict(status='reviewed', images=len(bundle['images']), pairs=len(pairs),
                frozen_annotation_sha256=object_hash(bundle), person_hours=hours,
                contributors=contributors)

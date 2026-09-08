"""Timing invariants and independent edge controls for Plan 024."""
import copy
import itertools
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from sync_timing import (SCHEMA, CONVENTION, validate_timing, corrected_timestamp,
                         normalized_timestamp, source_timestamp, rebase_timing,
                         common_training_keys, robust_offsets)


def artifact():
    return {'schema': SCHEMA, 'units': 'seconds', 'convention': CONVENTION,
            'camera_ids': ['1', '2', '3'], 'reference_camera': '1',
            'offset_seconds': {'1': 0.0, '2': 0.015, '3': None},
            'uncertainty_seconds': {'1': 0.0, '2': None, '3': None},
            'coverage': {'camera_ids': ['1', '2']},
            'source_support_seconds': {c: [0.0, 2.0] for c in ['1', '2', '3']},
            'source_window_seconds': [2.0, 6.0],
            'normalization': {'origin_seconds': -0.1, 'duration_seconds': 2.2},
            'kind': 'estimated', 'provenance': {'fixture': 'independent-offsets'}}


def test_subframe_sign_roundtrip_and_gauge():
    result = json.loads(json.dumps(artifact(), allow_nan=False))
    assert corrected_timestamp(result, '2', 0.8) == pytest.approx(0.785)
    rebased = rebase_timing(result, '2')
    assert rebased['offset_seconds']['1'] == pytest.approx(-0.015)
    for c in ['1', '2']:
        for t in [0.0, 0.813, 1.99]:
            n = normalized_timestamp(result, c, t)
            assert source_timestamp(result, c, n) == pytest.approx(t)
            assert normalized_timestamp(rebased, c, t) == pytest.approx(n)
    assert rebased['offset_seconds']['3'] is None
    assert artifact() == result  # rebase did not mutate source provenance


def test_unsupported_and_disconnected_are_not_zero():
    r = artifact()
    for t in [-0.01, 2.0, float('nan')]:
        with pytest.raises(ValueError): corrected_timestamp(r, '1', t)
    with pytest.raises(ValueError): corrected_timestamp(r, '3', 0.5)
    with pytest.raises(ValueError): rebase_timing(r, '3')
    with pytest.raises(ValueError): source_timestamp(r, '1', 1.0)


@pytest.mark.parametrize('change', [
    lambda r: r.update(units='milliseconds'),
    lambda r: r['offset_seconds'].update({'3': 0}),
    lambda r: r['offset_seconds'].update({'2': float('nan')}),
    lambda r: r['normalization'].update(duration_seconds=0),
    lambda r: r['uncertainty_seconds'].update({'2': -1}),
    lambda r: r.update(camera_ids=['1', '1', '3']),
])
def test_malformed_artifacts_rejected(change):
    r = artifact(); change(r)
    with pytest.raises(ValueError): validate_timing(r)


def test_union_temporal_exclusion_uses_identical_source_images():
    corrected = artifact()
    zero = copy.deepcopy(corrected)
    zero['offset_seconds']['2'] = 0
    zero['kind'] = 'operational-assumption'
    frames = [('2', f, t) for f, t in enumerate([0.79, 0.8, 0.99, 1.0, 1.02])]
    frames += [('1', 0, 0.2), ('3', 0, 0.2)]
    keys, exclusions = common_training_keys(frames, [zero, corrected], held_out=['1'])
    assert keys == [('2', 0), ('2', 4)]
    # 1.0 is outside zero's holdout but inside the corrected holdout.
    assert 'temporal-holdout-condition-1' in exclusions[2]['reasons']
    assert exclusions[-2]['reasons'] == ['held-out-camera']
    assert 'unsupported-condition-0' in exclusions[-1]['reasons']


def test_robust_redundant_graph_bad_edge_and_disconnection():
    ids = [str(i) for i in range(8)]
    truth = {str(i): i * 0.013 for i in range(6)}
    edges = [dict(i=i, j=j, delta_seconds=truth[i]-truth[j])
             for i, j in itertools.combinations(truth, 2)]
    edges[0]['delta_seconds'] += 0.5
    edges.append(dict(i='6', j='7', delta_seconds=0.04))
    fit = robust_offsets(ids, '0', edges, huber_seconds=0.001)
    assert max(abs(fit['offset_seconds'][c]-t) for c, t in truth.items()) < 0.001
    assert fit['offset_seconds']['6'] is None and fit['offset_seconds']['7'] is None
    assert fit['coverage'] == ids[:6]
    assert ['6', '7'] in fit['bridges']
    assert fit['uncertainty_seconds']['1'] is None


def test_bridge_has_no_outlier_validation_from_cycles():
    fit = robust_offsets(['1', '2', '3'], '1', [dict(i='1', j='2', delta_seconds=.7)], huber_seconds=.001)
    assert fit['offset_seconds']['2'] == pytest.approx(-.7)
    assert fit['bridges'] == [['1', '2']]
    assert fit['offset_seconds']['3'] is None


def test_conditions_must_share_normalization():
    first, second = artifact(), artifact()
    second['normalization']['origin_seconds'] += 1
    with pytest.raises(ValueError): common_training_keys([], [first, second], [])

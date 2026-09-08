import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from sync_motion_fixtures import run


def test_independent_motion_controls():
    cases = run()['cases']
    for name in ['fractional', 'occlusion', 'incorrect-correspondence', 'dropped-frames']:
        assert max(cases[name]['absolute_errors_seconds']) < 1e-4
    assert cases['stationary']['early']['offset_seconds'] is None
    assert cases['epipolar-direction-ambiguity']['offset_seconds'] is None
    assert cases['clock-rate-mismatch']['window_disagreement_seconds'] > .02
    assert cases['disconnected-graph']['offset_seconds']['3'] is None
    assert cases['disconnected-graph']['offset_seconds']['4'] is None

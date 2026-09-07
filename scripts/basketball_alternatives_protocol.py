"""Plan 006 protocol; deliberately independent of historical subset protocols."""
import math

PROTOCOL = 'basketball-alternatives/v1'
CAMERAS = tuple(range(34))
HELD_OUT = (0, 10, 20, 30)
TRAINING = tuple(c for c in CAMERAS if c not in HELD_OUT)
HISTORICAL = (1, 2, 3, 6, 7, 9, 12, 13, 14, 21, 22, 24, 25, 26, 27, 28, 29, 31, 32, 33)
EARLY = (50, 62, 75, 87, 99)
LATE = (100, 112, 125, 137, 149)
SNAPSHOT_PAIRS = ((50, 100), (75, 125), (99, 149))
METHODS = ('global', 'incremental', 'mast3r', 'vggsfm', 'vggt-omega', 'da3', 'pi3x', 'map-anything')


def manifest():
    return dict(schema=PROTOCOL, cameras=list(CAMERAS), training_cameras=list(TRAINING),
                held_out_cameras=list(HELD_OUT), excluded_cameras=[],
                fit_frames=list(range(50, 150)), selection_frames=list(range(150, 200)),
                validation_frames=list(range(200, 250)), downstream_frames=list(range(50)),
                snapshot_pairs=SNAPSHOT_PAIRS, early_frames=EARLY, late_frames=LATE,
                intrinsics='constant within physical camera; independent across windows',
                geocalib_trust_limit=.20, calibration_gpu_limit_seconds=None,
                rotation_limit_degrees=.5, center_limit_fraction=.01,
                historical_training_cameras=HISTORICAL)


def check_inputs(camera_ids, frames, *, held_out=False):
    expected = HELD_OUT if held_out else TRAINING
    if len(camera_ids) != len(expected) or set(camera_ids) != set(expected):
        raise ValueError('incomplete, duplicate or unexpected physical camera IDs')
    if not frames or len(frames) != len(set(frames)) or any(f not in range(50, 150) for f in frames):
        raise ValueError('only unique fitting frames allowed')


def screening_matrix():
    return [dict(method=m, frame=f, seed=0) for m in METHODS for pair in SNAPSHOT_PAIRS for f in pair]


def rank_complete(results):
    """Require all three complete pairs; null/NaN or missing cameras cannot win."""
    ranking = []
    for method in METHODS:
        rows = [r for r in results if r['method'] == method]
        if len(rows) != 3 or {tuple(r['frames']) for r in rows} != set(SNAPSHOT_PAIRS):
            continue
        if any(not r.get('complete') or r.get('cameras') != list(TRAINING) for r in rows):
            continue
        values = [r[k] for r in rows for k in ('max_rotation_degrees', 'max_center_fraction', 'wall_seconds')]
        if any(v is None or not math.isfinite(v) or v < 0 for v in values):
            continue
        rotation = max(r['max_rotation_degrees'] for r in rows)
        center = max(r['max_center_fraction'] for r in rows)
        ranking.append(dict(method=method, score=max(rotation/.5, center/.01),
                            max_rotation_degrees=rotation, max_center_fraction=center,
                            wall_seconds=sum(r['wall_seconds'] for r in rows)))
    return sorted(ranking, key=lambda r: (r['score'], r['max_rotation_degrees'],
                                         r['max_center_fraction'], r['wall_seconds']))

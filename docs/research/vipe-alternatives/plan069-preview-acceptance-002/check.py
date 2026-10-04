"""Independent, CPU-only revision 002 PNG acceptance; no producer imports."""
import hashlib
import json
import os
from pathlib import Path
import resource
import signal
import sys
import time

started = time.monotonic()
signal.signal(signal.SIGALRM, lambda *_: sys.exit('60-second acceptance limit'))
signal.alarm(60)
os.environ['CUDA_VISIBLE_DEVICES'] = ''
os.environ['OPENBLAS_NUM_THREADS'] = '1'
import numpy as np
from PIL import Image


def checked(record):
    path = Path(record['path'])
    assert 'prompts' not in path.resolve().parts
    assert path.stat().st_size == record['bytes'], str(path)
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(chunk)
    assert digest.hexdigest() == record['sha256'], str(path)
    return path


def record(path):
    return dict(path=str(path.resolve()), sha256=hashlib.sha256(path.read_bytes()).hexdigest(), bytes=path.stat().st_size)


path = Path(sys.argv[1])
receipt = json.loads(path.read_text())
assert receipt['schema'] == 'plan069-depth-anchor-preview-result/v1'
assert receipt['preview_revision'] == '002' and receipt['status'] == 'complete'
assert receipt['record_kind'] == 'actual' and receipt['rendered_frames'] == 60
assert receipt['physical_accuracy'] == 'unverified' and receipt['human_review'] == 'pending'
context = json.loads(checked(receipt['context']).read_text())
accepted = {(a['camera'], a['frame']): a['accepted_rgb'] for a in context['anchors']}
assert len(accepted) == 60
assert {(a['camera'], a['frame']) for a in receipt['anchors']} == set(accepted)
assert len(receipt['anchors']) == 60
for binding in receipt['sources'].values():
    checked(binding)
checked(receipt['config'])
checked(receipt['inputs'])
for binding in receipt['slot']['provenance'].values():
    if isinstance(binding, dict) and 'path' in binding:
        checked(binding)
for binding in receipt['slot']['evidence'].values():
    if isinstance(binding, dict) and 'path' in binding:
        checked(binding)
counts = dict(invalid=0, above_20=0, valid=0)
for anchor in receipt['anchors']:
    assert anchor['source_rgb'] == accepted[anchor['camera'], anchor['frame']]
    assert anchor['grid'] == 'scale-opencv-integer'
    with Image.open(checked(anchor['source_rgb'])) as source:
        assert source.mode == 'RGB' and source.size == (960, 540)
    with np.load(checked(anchor['prediction']), allow_pickle=False) as data:
        metric = anchor['domain'] == 'camera_z_metres'
        values = data['depth' if metric else 'relative']
        valid = data['valid']
        assert values.shape == valid.shape == (540, 960)
        assert values.dtype == np.float32 and valid.dtype == np.bool_
        assert valid.any() and np.isfinite(values[valid]).all()
        assert np.isnan(values[~valid]).all()
        display = anchor['display']
        assert display['domain'] == anchor['domain']
        assert display['normalization_scope'] == 'one frozen anchor frame'
        if metric:
            assert (values[valid] > 0).all()
            assert display['range_metres'] == [0, 20]
            assert display['clipped_above_metres'] == 20
            assert display['direction'] == 'larger means farther'
            assert display['invalid_color'] == 'magenta' and display['above_20_metres_color'] == 'red'
            normalized = np.minimum(np.maximum(values / 20, 0), 1)
        else:
            low, high = float(values[valid].min()), float(values[valid].max())
            assert display['raw_range'] == [low, high]
            assert display['units'] == 'relative arbitrary values'
            assert display['direction'] == ('larger means nearer' if anchor['domain'] == 'relative_inverse' else 'larger means farther')
            normalized = np.full(values.shape, .5, dtype=np.float32) if low == high else np.minimum(np.maximum((values-low)/(high-low), 0), 1)
        expected = np.repeat((np.nan_to_num(normalized, nan=0) * 255).astype(np.uint8)[:, :, None], 3, axis=2)
        above = valid & (values > 20) if metric else np.zeros(valid.shape, dtype=bool)
        expected[above] = (255, 0, 0)
        expected[~valid] = (255, 0, 255)
        with Image.open(checked(anchor['record'])) as png:
            assert png.mode == 'RGB' and png.size == (960, 540)
            assert np.array_equal(np.asarray(png), expected), anchor['record']['path']
        counts['invalid'] += int((~valid).sum())
        counts['above_20'] += int(above.sum())
        counts['valid'] += int(valid.sum())
assert receipt['source_rgb'] == [a['source_rgb'] for a in receipt['anchors']]
output = dict(schema='plan069-independent-preview-acceptance/v1', status='pass', candidate=receipt['candidate'], preview_revision='002', receipt=record(path), checker=record(Path(__file__)), anchors_verified=60, pixel_counts=counts, elapsed_seconds=time.monotonic()-started, maximum_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss, gpu_used=False, ledger_modified=False, physical_accuracy='unverified', human_review='pending')
Path(sys.argv[2]).write_text(json.dumps(output, indent=2)+'\n')
print(json.dumps(output))

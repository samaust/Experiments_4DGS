"""Post-hoc CPU investigation of the reported Plan 027 crossing artifacts.

Read existing metrics and lossless renders only. Keep this descriptive analysis
separate from the frozen experiment's metrics, crops, and bootstrap estimates.
"""
import argparse
from collections import defaultdict
import csv
import json
import math
from pathlib import Path
from statistics import mean

from basketball_study import CURVE, MANIFEST, ROOT, digest, write_new

ARMS = ('stg-full', 'freetimegs-sparse', 'freetimegs-dense-coarse', 'freetimegs-dense-cropped')
CAMERAS = ('0', '10', '20', '30')
GAP = tuple(range(20, 25))
ADJACENT = (17, 18, 19, 25, 26, 27)
FRAMES = (17, 19, 20, 21, 22, 23, 24, 25, 27)
# Selected from ground truth after the human report. Fixed across arms and seeds.
CROPS = {'0': (150, 70, 410, 260), '10': (340, 40, 560, 250),
         '20': (610, 100, 830, 315), '30': (660, 160, 945, 365)}
MEASURES = ('full/psnr', 'dynamic/psnr', 'dynamic/lpips_alex', 'motion_pixels/mae')
EXPECTED = {(c, f) for c in CAMERAS for f in range(50)} | {
    (str(c), f) for c in range(34) if str(c) not in CAMERAS for f in GAP}


def checked_json(path, expected_hash, sources):
    path = Path(path)
    observed = digest(path)
    if observed != expected_hash:
        raise ValueError(f'changed source: {path}')
    sources[str(path.resolve())] = observed
    return json.loads(path.read_text())


def value(row, name):
    for part in name.split('/'):
        row = row[part]
    if not math.isfinite(row):
        raise ValueError('nonfinite metric')
    return float(row)


def validate_metrics(record, metrics):
    rows = metrics['frames']
    if (not metrics['complete'] or metrics['seed'] != record['seed'] or
            metrics['iteration'] != record['iteration'] or
            metrics['render_sha256'] != record['render_sha256']):
        raise ValueError('metric provenance mismatch')
    if len(rows) != 350 or {(r['camera'], r['frame_id']) for r in rows} != EXPECTED:
        raise ValueError('metric camera/frame coverage mismatch')
    for r in rows:
        expected_split = 'heldout-camera' if r['camera'] in CAMERAS else 'temporal-interpolation'
        if r['split'] != expected_split or abs(r['normalized_time'] - r['frame_id']/50) > 1e-9:
            raise ValueError('metric split/time mismatch')
        for name in MEASURES:
            value(r, name)
    return rows


def window_summary(rows):
    if len(rows) != 50 or {r['frame_id'] for r in rows} != set(range(50)):
        raise ValueError('window comparison requires all fifty frames from one camera/seed')
    result = {}
    for name in MEASURES:
        adjacent = mean(value(r, name) for r in rows if r['frame_id'] in ADJACENT)
        gap = mean(value(r, name) for r in rows if r['frame_id'] in GAP)
        result[name] = dict(adjacent=adjacent, gap=gap, gap_minus_adjacent=gap-adjacent,
                            gap_over_adjacent=gap/adjacent if adjacent else None)
    maximum = max(value(r, 'motion_pixels/mae') for r in rows)
    result['motion_mae_peak_frames'] = [r['frame_id'] for r in rows
                                      if value(r, 'motion_pixels/mae') == maximum]
    return result


def plot_series(series, output):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(2, 2, figsize=(12, 7), constrained_layout=True)
    colors = ('#999999', '#b8860b', '#0072b2', '#d55e00')
    for row, measure in enumerate(('motion_pixels/mae', 'dynamic/lpips_alex')):
        for col, dense_only in enumerate((False, True)):
            ax = axes[row, col]
            for arm, color in zip(ARMS, colors):
                if dense_only and arm in ARMS[:2]:
                    continue
                selected = sorted([r for r in series if r['arm'] == arm and r['iteration'] == 50000],
                                  key=lambda r: r['frame_id'])
                ax.plot([r['seconds'] for r in selected], [r[measure] for r in selected],
                        label=arm.replace('freetimegs-', 'FTGS '), color=color)
            ax.axvspan(.8, 1., color='#888888', alpha=.18, label='No training images [0.80, 1.00) s')
            ax.axvline(.88, color='#444444', linestyle=':', linewidth=1)
            ax.set_title(measure + (' — dense detail' if dense_only else ' — four arms'))
            ax.set_xlabel('Source time (seconds)')
            ax.set_ylabel('Mean error (lower is better)')
            ax.grid(alpha=.2)
    axes[0, 0].legend(fontsize=8)
    fig.suptitle('50k checkpoints: four held-out cameras × three seeds; descriptive means')
    fig.savefig(output / 'frame-errors.png', dpi=150)
    plt.close(fig)


def panels(records, manifest, assets, output, sources):
    from PIL import Image, ImageDraw, ImageFont
    cameras = {c['id']: c for c in manifest['cameras']}
    renders = {}
    for r in records:
        if r['iteration'] != 50000:
            continue
        p = Path(r['render'])
        d = checked_json(p, r['render_sha256'], sources)
        if not d['complete'] or d['iteration'] != 50000 or d['checkpoint_sha256'] != r['checkpoint_sha256']:
            raise ValueError('render endpoint/provenance mismatch')
        if len(d['frames']) != 350 or {(v['camera'], v['frame_id']) for v in d['frames']} != EXPECTED:
            raise ValueError('render camera/frame coverage mismatch')
        renders[r['arm'], r['seed']] = (p.parent, {(v['camera'], v['frame_id']): v for v in d['frames']})
    if set(renders) != {(a, s) for a in ARMS for s in range(3)}:
        raise ValueError('incomplete endpoint panels')

    def read(path, sha):
        if digest(path) != sha:
            raise ValueError(f'changed image: {path}')
        sources[str(path.resolve())] = sha
        with Image.open(path) as image:
            if image.size != (960, 540):
                raise ValueError('image resolution mismatch')
            return image.convert('RGB')

    labels = ('Ground truth', 'STG Full', 'FTGS sparse', 'FTGS dense coarse', 'FTGS dense cropped')
    font = ImageFont.load_default(size=13)
    artifacts = []
    for camera, box in CROPS.items():
        w, h = box[2]-box[0], box[3]-box[1]
        for seed in range(3):
            canvas = Image.new('RGB', (5*w, len(FRAMES)*(h+25)))
            draw = ImageDraw.Draw(canvas)
            overview = Image.new('RGB', (3*w, 3*(h+25))) if camera == '0' and seed == 0 else None
            for i, f in enumerate(FRAMES):
                gt = cameras[camera]['frames'][f]
                images = [read(MANIFEST.parent / gt['path'], gt['sha256'])]
                for arm in ARMS:
                    folder, frames = renders[arm, seed]
                    r = frames[camera, f]
                    if r['target_sha256'] != gt['sha256']:
                        raise ValueError('render ground-truth pairing mismatch')
                    images.append(read(folder/r['path'], r['sha256']))
                for j, (im, label) in enumerate(zip(images, labels)):
                    canvas.paste(im.crop(box), (j*w, i*(h+25)+25))
                    draw.text((j*w+3, i*(h+25)+5), f'{label} f{f} / {f/25:.2f}s', fill='white', font=font)
                if overview is not None and f in (19, 22, 25):
                    y = (19, 22, 25).index(f)*(h+25)
                    od = ImageDraw.Draw(overview)
                    for j, index in enumerate((0, 3, 4)):
                        overview.paste(images[index].crop(box), (j*w, y+25))
                        od.text((j*w+3, y+5), f'{labels[index]} f{f} / {f/25:.2f}s', fill='white', font=font)
            path = assets/f'camera{camera}-seed{seed}-sequence.png'
            canvas.save(path)
            artifacts.append(dict(camera=camera, seed=seed, path=str(path.resolve()), sha256=digest(path),
                                  frames=list(FRAMES), crop=list(box), columns=list(labels)))
            if overview is not None:
                overview.save(output/'crossing-before-during-after.png')
    return artifacts


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--index', type=Path, default=ROOT/'docs/experiments/basketball-dense-training/analysis-final/artifact-index.json')
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--assets', type=Path, required=True)
    a = p.parse_args()
    if a.output.exists() or a.assets.exists():
        raise FileExistsError('use new output and asset directories')
    sources = {}
    records = checked_json(a.index, digest(a.index), sources)['records']
    expected = {(arm, seed, step) for arm in ARMS for seed in range(3) for step in CURVE}
    if len(records) != 60 or {(r['arm'], r['seed'], r['iteration']) for r in records} != expected:
        raise ValueError('requires all sixty original curve records')
    m = checked_json(MANIFEST, digest(MANIFEST), sources)
    expected_training = {(str(c), f) for c in range(34) if str(c) not in CAMERAS
                         for f in range(50) if f not in GAP}
    if (len(m['training_keys']) != 1350 or {tuple(k) for k in m['training_keys']} != expected_training or
            m['source_fps'] != 25 or m['temporal_holdout_seconds'] != [.8, 1.]):
        raise ValueError('frozen training split/cadence mismatch')
    windows, groups = [], defaultdict(list)
    for record in records:
        metrics = checked_json(record['metrics'], record['metrics_sha256'], sources)
        rows = validate_metrics(record, metrics)
        for camera in CAMERAS:
            subset = [r for r in rows if r['camera'] == camera]
            windows.append(dict(arm=record['arm'], seed=record['seed'], iteration=record['iteration'],
                                camera=camera, **window_summary(subset)))
            for r in subset:
                groups[record['arm'], record['iteration'], r['frame_id']].append(r)
    series = []
    for (arm, step, frame), rows in sorted(groups.items()):
        if len(rows) != 12:
            raise ValueError('unbalanced camera/seed aggregate')
        series.append(dict(arm=arm, iteration=step, frame_id=frame, seconds=frame/25,
                           **{name: mean(value(r, name) for r in rows) for name in MEASURES}))
    a.output.mkdir(parents=True)
    a.assets.mkdir(parents=True)
    with (a.output/'frame-means.csv').open('x', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(series[0]), lineterminator='\n')
        writer.writeheader()
        writer.writerows(series)
    plot_series(series, a.output)
    artifacts = panels(records, m, a.assets, a.output, sources)
    for relative in ('scripts/basketball_dense_crossing_audit.py', 'scripts/basketball_scene.py',
                     'scripts/freetimegs_source.py',
                     '.local/FreeTimeGsVanilla/src/simple_trainer_freetime_4d_pure_relocation.py'):
        path = ROOT/relative
        sources[str(path)] = digest(path)
    write_new(a.output/'evidence.json', dict(schema='basketball-crossing-audit/v1',
        scope='post-hoc descriptive investigation; existing frozen metrics/renders only; no new GPU work',
        metric_records=60, metric_frame_rows=21000, training_images=1350,
        gap_frames=list(GAP), gap_seconds=[.8, 1.], gap_end_exclusive=True,
        adjacent_frames=list(ADJACENT), summary_unit='one camera/seed/checkpoint; equal frame means',
        limitation='selected after observing the videos; one temporal gap coincides with the crossing; no causal intervention',
        windows=windows, panels=artifacts, files=sources,
        generated_files={f: digest(a.output/f) for f in ('frame-means.csv', 'frame-errors.png', 'crossing-before-during-after.png')}))
    print(json.dumps(dict(metric_records=60, camera_seed_windows=len(windows), panels=len(artifacts),
                          output=str(a.output), gpu_jobs=0)))


if __name__ == '__main__':
    main()

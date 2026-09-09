"""Plan 027 four-arm matched seed/block curves and predeclared contrasts."""
import argparse
from collections import defaultdict
import csv
import json
from pathlib import Path

import numpy as np

from basketball_study import CURVE, ROOT, digest, write_new
from basketball_dense_training import ARTIFACTS, DOCS, ARMS as DENSE_ARMS
from basketball_reconstruction_metrics import block_interval

ARMS = ('stg-full', 'freetimegs-sparse', *DENSE_ARMS)
SPLITS = ('heldout-camera', 'temporal-interpolation')
METRICS = ('full/psnr', 'full/ssim', 'full/lpips_alex', 'dynamic/psnr', 'dynamic/ssim',
           'dynamic/lpips_alex', 'motion_pixels/psnr', 'motion_pixels/mae', 'temporal_difference_mae')


def block_means(rows, split, name):
    groups = defaultdict(list)
    for row in rows:
        if row['split'] != split:
            continue
        value = row
        for key in name.split('/'):
            value = value.get(key) if isinstance(value, dict) else None
        if value is not None:
            if not np.isfinite(value):
                raise ValueError('nonfinite metric')
            groups[row['frame_id']//5].append(value)
    return {block: float(np.mean(values)) for block, values in groups.items()}


def matched_table(runs, split, name):
    runs = sorted(runs, key=lambda r: r['seed'])
    if [r['seed'] for r in runs] != [0, 1, 2]:
        raise ValueError('requires exactly three seeds')
    groups = [block_means(r['frames'], split, name) for r in runs]
    blocks = sorted(groups[0])
    if not blocks or any(set(g) != set(blocks) for g in groups):
        raise ValueError('mismatched temporal block coverage')
    return blocks, np.array([[g[b] for b in blocks] for g in groups])


def training_time(record, history):
    if record['arm'] not in DENSE_ARMS:
        return record['accumulated_training_seconds']
    total = 0.
    for endpoint in (5000, 50000):
        folder = ARTIFACTS/f"training/{record['arm']}-seed{record['seed']}/{endpoint:06d}"
        if endpoint == 50000 and record['iteration'] == 5000:
            break
        origin = json.loads((folder/'timing.json').read_text())['optimizer_loop_start_monotonic']
        segment = ARTIFACTS/f"segments/train-{record['arm']}-seed{record['seed']}-{endpoint}"
        start = json.loads((segment/'process.json').read_text())['started_monotonic']
        target = min(record['iteration'], endpoint)
        row = next(json.loads(line) for line in (folder/'loss.jsonl').open() if json.loads(line)['iteration'] == target)
        total += origin-start+row['elapsed_seconds']
    return total


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--partial', action='store_true')
    a = p.parse_args()
    baseline = json.loads((DOCS / 'baseline-reuse.json').read_text())
    records = baseline['records'].copy()
    for arm in DENSE_ARMS:
        for step in CURVE:
            path = ARTIFACTS / f'metrics/{arm}/{step:06d}/records.json'
            if path.exists():
                records.extend(json.loads(path.read_text())['records'])
    expected = {(arm, seed, step) for arm in ARMS for seed in range(3) for step in CURVE}
    observed = {(r['arm'], r['seed'], r['iteration']) for r in records}
    if len(observed) != len(records) or not observed <= expected:
        raise ValueError('duplicate or unexpected study result')
    missing = sorted(expected-observed)
    if missing and not a.partial:
        raise ValueError('available-arm evaluations remain incomplete')
    history = json.loads((ROOT / 'docs/research/basketball-sync-pivot/gpu-budget.json').read_text())
    cohorts = defaultdict(list)
    index = []
    for record in records:
        path = Path(record['metrics'])
        if digest(path) != record['metrics_sha256']:
            raise ValueError('metric source changed')
        metrics = json.loads(path.read_text())
        if not metrics['complete'] or len(metrics['frames']) != 350 or metrics['seed'] != record['seed'] or metrics['iteration'] != record['iteration']:
            raise ValueError('metric coverage/pairing changed')
        metrics['training_seconds'] = training_time(record, history)
        cohorts[record['arm'], record['iteration']].append(metrics)
        index.append(dict(record, accumulated_training_seconds=metrics['training_seconds']))
    a.output.mkdir(parents=True, exist_ok=False)
    curves, tables = [], {}
    for (arm, step), runs in sorted(cohorts.items()):
        if len(runs) != 3:
            continue
        for split in SPLITS:
            for metric in METRICS:
                blocks, values = matched_table(runs, split, metric)
                summary = block_interval(values)
                tables[arm, step, split, metric] = (blocks, values)
                curves.append(dict(arm=arm, iteration=step, split=split, metric=metric,
                    training_seconds=float(np.mean([r['training_seconds'] for r in runs])),
                    block_ids=blocks, **summary))
    effects = {}
    for arm in ARMS:
        for split in SPLITS:
            for metric in METRICS:
                left = tables.get((arm, 5000, split, metric))
                right = tables.get((arm, 50000, split, metric))
                if left is not None and right is not None:
                    if left[0] != right[0]:
                        raise ValueError('duration contrast has mismatched blocks')
                    effects[f'{arm}/{split}/{metric}'] = dict(direction='50000 minus 5000', **block_interval(right[1]-left[1]))
    workflow = {}
    for step in CURVE:
        for split in SPLITS:
            for metric in METRICS:
                left, right = tables.get(('stg-full', step, split, metric)), tables.get(('freetimegs-sparse', step, split, metric))
                if left is not None and right is not None:
                    if left[0] != right[0]:
                        raise ValueError('workflow contrast has mismatched blocks')
                    workflow[f'{step}/{split}/{metric}'] = dict(direction='sparse FreeTimeGS minus STG Full', **block_interval(right[1]-left[1]))
    contrasts = {}
    for dense in DENSE_ARMS:
        for reference in ('freetimegs-sparse', 'stg-full'):
            for step in CURVE:
                for split in SPLITS:
                    for metric in METRICS:
                        left = tables.get((reference, step, split, metric))
                        right = tables.get((dense, step, split, metric))
                        if left is not None and right is not None:
                            if left[0] != right[0]:
                                raise ValueError('contrast block mismatch')
                            contrasts[f'{dense}-minus-{reference}/{step}/{split}/{metric}'] = block_interval(right[1]-left[1])
    interactions, recipe = {}, {}
    for split in SPLITS:
        for metric in METRICS:
            for dense in DENSE_ARMS:
                keys = [(dense,50000), (dense,5000), ('freetimegs-sparse',50000), ('freetimegs-sparse',5000)]
                selected = [tables.get((*key,split,metric)) for key in keys]
                if all(t is not None for t in selected):
                    if any(t[0] != selected[0][0] for t in selected):
                        raise ValueError('interaction block mismatch')
                    values = [t[1] for t in selected]
                    interactions[f'{dense}/{split}/{metric}'] = block_interval(values[0]-values[1]-values[2]+values[3])
            for step in CURVE:
                left = tables.get((DENSE_ARMS[0],step,split,metric))
                right = tables.get((DENSE_ARMS[1],step,split,metric))
                if left is not None and right is not None:
                    if left[0] != right[0]:
                        raise ValueError('recipe block mismatch')
                    recipe[f'{step}/{split}/{metric}'] = block_interval(right[1]-left[1])
    write_new(a.output/'artifact-index.json', dict(records=index, missing_results=missing))
    write_new(a.output/'statistics.json', dict(schema='basketball-dense-training-statistics/v1', curves=curves,
        training_duration_effects=effects, supplemental_sparse_workflow=workflow,
        initialization_and_stg_contrasts=contrasts, initialization_duration_interaction=interactions,
        cropped_minus_coarse=recipe, metric_coverage_complete=not missing,
        method='same 2000 seed/five-frame-block bootstrap draws, seed 0, 95% percentile intervals',
        limitation='three seeds; fixed cameras and one scene; temporal interpolation has one temporal block; initialization changes point count, geometry, and motion together'))
    with (a.output / 'curves.csv').open('x', newline='') as stream:
        fields = ['arm', 'iteration', 'split', 'metric', 'training_seconds', 'mean', 'lower', 'upper', 'seeds', 'blocks']
        writer = csv.DictWriter(stream, fieldnames=fields, extrasaction='ignore', lineterminator='\n')
        writer.writeheader()
        writer.writerows(curves)
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    for split in SPLITS:
        for axis in ('iteration', 'training_seconds'):
            fig, axes = plt.subplots(3, 3, figsize=(15, 12), constrained_layout=True)
            for panel, metric in zip(axes.flat, METRICS):
                for arm in ARMS:
                    selected = sorted([r for r in curves if r['arm'] == arm and r['split'] == split and r['metric'] == metric], key=lambda r: r['iteration'])
                    if selected:
                        x = [r[axis] for r in selected]
                        panel.plot(x, [r['mean'] for r in selected], marker='o', label=arm)
                        panel.fill_between(x, [r['lower'] for r in selected], [r['upper'] for r in selected], alpha=.15)
                panel.set_title(metric)
                panel.set_xlabel('Optimizer updates' if axis == 'iteration' else 'Accumulated charged training seconds')
                panel.grid(alpha=.2)
            axes.flat[0].legend()
            fig.suptitle(f'{split}: four-arm fixed initialization study')
            fig.savefig(a.output / f'{split}-{axis}.png', dpi=150)
            plt.close(fig)
    totals = defaultdict(float)
    for line in (ARTIFACTS / 'ledger.jsonl').read_text().splitlines():
        event = json.loads(line)
        if event['event'] in ('finish', 'failure'):
            totals[event['stage']] += event['charged_seconds']
    write_new(a.output / 'accounting.json', dict(study_gpu_job_wall_seconds=dict(totals),
        preledger_runtime_checks_seconds=0,
        historical_ledger_sha256=digest(ROOT / 'docs/research/basketball-sync-pivot/gpu-budget.json'),
        definition='charged GPU-job wall time includes startup and CPU work within that job; it is not GPU-kernel busy time',
        initial_cost='new full dense initialization shown separately; historical sparse initialization CPU cost was not separately measured',
        cpu_postprocessing='standalone CPU inspections, tests, video encoding and report preparation are not included in GPU-job accounting'))
    fig, panel = plt.subplots(figsize=(7, 4), constrained_layout=True)
    panel.bar(list(totals), [v/60 for v in totals.values()])
    panel.set_ylabel('New charged GPU-job wall minutes')
    panel.set_title('Initialization cost is separate from training and evaluation')
    fig.savefig(a.output / 'charged-compute.png', dpi=150)
    plt.close(fig)


if __name__ == '__main__':
    main()

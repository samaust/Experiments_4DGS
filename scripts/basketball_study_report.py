"""Matched seed/block curves and duration contrasts for the available study arms."""
import argparse
from collections import defaultdict
import csv
import json
from pathlib import Path

import numpy as np

from basketball_study import ARTIFACTS, CURVE, DOCS, ROOT, digest, write_new
from basketball_reconstruction_metrics import block_interval

ARMS = ('stg-full', 'freetimegs-sparse')
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
    method = 'freetimegs' if record['arm'] == 'freetimegs-sparse' else record['arm']
    role = f"{method}-basketball-zero-seed{record['seed']}"
    old = [r for r in history['attempts'] if r['role'] == role and r['status'] == 'completed']
    if len(old) != 1:
        raise ValueError('ambiguous historical training consumption')
    seconds = old[0]['charged_seconds']
    if record['iteration'] == 5000:
        return seconds
    name = f"{record['arm']}-seed{record['seed']}"
    training = ARTIFACTS / 'training' / name
    origin = json.loads((training / 'timing.json').read_text())['optimizer_loop_start_monotonic']
    segment = json.loads((ARTIFACTS / 'segments' / name / 'process.json').read_text())['started_monotonic']
    for line in (training / 'loss.jsonl').open():
        row = json.loads(line)
        if row['iteration'] == record['iteration']:
            return seconds + origin-segment + row['elapsed_seconds']
    raise ValueError('missing measured update time')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--partial', action='store_true')
    a = p.parse_args()
    baseline = json.loads((DOCS / 'baseline-reuse.json').read_text())
    records = baseline['records'].copy()
    for step in CURVE[1:]:
        path = ARTIFACTS / f'metrics/{step:06d}/records.json'
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
    write_new(a.output / 'artifact-index.json', dict(records=index, missing_available_results=missing,
        dense_arm='stopped at initialization prerequisite; no trained dense results exist'))
    write_new(a.output / 'statistics.json', dict(schema='basketball-study-statistics/v1', curves=curves,
        training_duration_effects=effects, supplemental_sparse_workflow=workflow,
        initialization_effect='unavailable: dense prerequisite failed',
        initialization_duration_interaction='unavailable: dense prerequisite failed',
        planned_stg_vs_dense_workflow='unavailable: dense prerequisite failed',
        full_study_complete=False, available_arm_evaluations_complete=not missing,
        method='same 2000 seed/five-frame-block bootstrap draws, seed 0, 95% percentile intervals',
        limitation='three seeds; fixed cameras and one scene; temporal interpolation has one temporal block'))
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
            fig.suptitle(f'{split}: available sparse arms; dense prerequisite failed')
            fig.savefig(a.output / f'{split}-{axis}.png', dpi=150)
            plt.close(fig)
    totals = defaultdict(float)
    for line in (ARTIFACTS / 'ledger.jsonl').read_text().splitlines():
        event = json.loads(line)
        if event['event'] in ('finish', 'failure'):
            totals[event['stage']] += event['charged_seconds']
    write_new(a.output / 'accounting.json', dict(study_gpu_job_wall_seconds=dict(totals),
        preledger_runtime_checks_seconds=2.658+2.564,
        historical_ledger_sha256=digest(ROOT / 'docs/research/basketball-sync-pivot/gpu-budget.json'),
        definition='charged GPU-job wall time includes startup and CPU work within that job; it is not GPU-kernel busy time',
        initial_cost='new dense pilot preparation shown separately; historical sparse initialization CPU cost was not separately measured',
        cpu_postprocessing='standalone CPU inspections, tests, video encoding and report preparation are not included in GPU-job accounting'))
    fig, panel = plt.subplots(figsize=(7, 4), constrained_layout=True)
    panel.bar(list(totals), [v/60 for v in totals.values()])
    panel.set_ylabel('New charged GPU-job wall minutes')
    panel.set_title('Initialization cost is separate from training and evaluation')
    fig.savefig(a.output / 'charged-compute.png', dpi=150)
    plt.close(fig)


if __name__ == '__main__':
    main()

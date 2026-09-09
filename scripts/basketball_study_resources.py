"""Audit completed study trajectories and plot measured loss and point counts."""
import argparse
import json
from pathlib import Path

import numpy as np

from basketball_study import ARTIFACTS, CURVE, digest, write_new


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--partial', action='store_true')
    args = parser.parse_args()
    records, series, missing = [], {}, []
    for arm in ('stg-full', 'freetimegs-sparse'):
        for seed in range(3):
            name = f'{arm}-seed{seed}'
            folder = ARTIFACTS / 'training' / name
            result_path = folder / 'worker-result.json'
            if not result_path.exists():
                missing.append(name)
                continue
            result = json.loads(result_path.read_text())
            if result['iteration'] != 50000:
                raise ValueError(f'incomplete endpoint: {name}')
            path = folder / 'loss.jsonl'
            rows = [json.loads(line) for line in path.read_text().splitlines()]
            if [r['iteration'] for r in rows] != list(range(5001, 50001)):
                raise ValueError(f'noncontiguous continuation: {name}')
            for row in rows:
                if not all(np.isfinite(row[k]) for k in ('loss', 'points', 'elapsed_seconds')):
                    raise ValueError(f'nonfinite trajectory: {name}')
            if any(b['elapsed_seconds'] < a['elapsed_seconds'] for a, b in zip(rows, rows[1:])):
                raise ValueError(f'nonmonotonic timing: {name}')
            checkpoints = []
            for step in CURVE[1:]:
                checkpoint = folder / f'checkpoint-{step:06d}.pt'
                checkpoints.append(dict(iteration=step, path=str(checkpoint),
                    bytes=checkpoint.stat().st_size, sha256=digest(checkpoint)))
            series[name] = rows
            records.append(dict(arm=arm, seed=seed, updates=45000,
                initial_observed_loss=rows[0]['loss'], final_loss=rows[-1]['loss'],
                final_points=rows[-1]['points'], peak_points=max(r['points'] for r in rows),
                optimizer_loop_seconds=rows[-1]['elapsed_seconds'],
                peak_allocated_bytes=result['peak_allocated_bytes'],
                peak_reserved_bytes=result['peak_reserved_bytes'],
                loss_path=str(path), loss_sha256=digest(path), checkpoints=checkpoints))
    if missing and not args.partial:
        raise ValueError(f'missing completed trajectories: {missing}')
    args.output.mkdir(parents=True, exist_ok=False)
    write_new(args.output / 'trajectories.json', dict(records=records, missing=missing,
        loss_comparison='Native training losses differ between methods; compare trends within each method.',
        memory='PyTorch peak allocated/reserved memory excludes other CUDA and driver allocations.'))
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(2, 2, figsize=(12, 8), constrained_layout=True)
    for column, arm in enumerate(('stg-full', 'freetimegs-sparse')):
        for seed in range(3):
            rows = series.get(f'{arm}-seed{seed}')
            if rows is None:
                continue
            blocks = [rows[i:i+100] for i in range(0, len(rows), 100)]
            updates = [b[-1]['iteration'] for b in blocks]
            axes[0, column].plot(updates, [np.mean([r['loss'] for r in b]) for b in blocks], label=f'seed {seed}')
            axes[1, column].plot(updates, [b[-1]['points'] for b in blocks], label=f'seed {seed}')
        axes[0, column].set_title(arm)
        axes[0, column].set_ylabel('Native loss (100-update mean)')
        axes[1, column].set_ylabel('Point count')
        for panel in axes[:, column]:
            panel.set_xlabel('Absolute optimizer update')
            panel.grid(alpha=.2)
            if panel.lines:
                panel.legend()
    fig.savefig(args.output / 'training-trajectories.png', dpi=150)
    plt.close(fig)


if __name__ == '__main__':
    main()

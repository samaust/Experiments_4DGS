"""Run the frozen 350-frame metric worker over all Plan 028 endpoints."""
import argparse
import json
from pathlib import Path

from basketball_reconstruction_metrics import digest
from basketball_study import ROOT, supervise, write_new


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--artifact-root', type=Path, default=ROOT/'.local/basketball-crossing-repair')
    p.add_argument('--runtime', type=Path, default=ROOT/'docs/experiments/basketball-dense-temporal/metric-runtime.json')
    a = p.parse_args()
    records = []
    for path in sorted(a.artifact_root.glob('evaluation/*/record-070000.json')):
        record = json.loads(path.read_text())
        if record.get('iteration') != 70000 or not record.get('reload', {}).get('complete'):
            raise ValueError(f'incomplete endpoint: {path}')
        if digest(record['render']) != record['render_sha256']:
            raise ValueError(f'render provenance changed: {path}')
        records.append(record)
    expected = {(arm, seed, train, life) for arm in ('freetimegs-dense-coarse', 'freetimegs-dense-cropped')
                for seed in range(3) for train in ('holdout', 'all-times') for life in ('original', 'repaired')}
    actual = {(r['arm'], r['seed'], r['training_policy'], r['lifetime_policy']) for r in records}
    if actual != expected:
        raise ValueError(f'endpoint coverage mismatch: {len(actual)} of {len(expected)}')
    runtime = json.loads(a.runtime.read_text())
    all_results = []
    for arm in ('freetimegs-dense-coarse', 'freetimegs-dense-cropped'):
        for train in ('holdout', 'all-times'):
            for life in ('original', 'repaired'):
                selected = [r for r in records if (r['arm'], r['training_policy'], r['lifetime_policy']) == (arm, train, life)]
                inputs = a.artifact_root/f'metric-inputs-{arm}-{train}-{life}.json'
                write_new(inputs, dict(runs=[dict(method='freetimegs', seed=r['seed'], render=r['render']) for r in selected]))
                output = a.artifact_root/f'metrics/{arm}/{train}-{life}'
                if (output/'summary.json').exists():
                    result_paths = [output/f'freetimegs-seed{s}.json' for s in range(3)]
                    if not all(x.exists() for x in result_paths):
                        raise ValueError(f'partial existing metrics: {output}')
                else:
                    command = ['docker', 'run', '--rm', '--name', f'plan028-metrics-{arm}-{train}-{life}',
                               '--network', 'none', '--gpus', 'all', '--user', '1000:1000',
                               '-e', 'TRAINING_STOP_MONOTONIC=inf', '-e', 'MPLCONFIGDIR=/tmp/matplotlib',
                               '--entrypoint', 'python', '-v', f'{ROOT}:{ROOT}', '-w', str(ROOT), runtime['image'],
                               'scripts/basketball_reconstruction_metrics.py', '--inputs', str(inputs), '--output', str(output)]
                    segment = supervise(command, 'evaluation', a.artifact_root/f'segments/metrics-{arm}-{train}-{life}')
                    if segment['exit_code'] or segment['interrupted']:
                        raise SystemExit('metrics stopped; inspect retained segment and worker logs')
                for path in result_paths:
                    metric = json.loads(path.read_text())
                    source = next(r for r in selected if r['seed'] == metric['seed'])
                    if not metric['complete'] or len(metric['frames']) != 350 or metric['render_sha256'] != source['render_sha256']:
                        raise ValueError(f'incomplete metric result: {path}')
                    for row in metric['frames']:
                        row.update(arm=arm, training_policy=train, lifetime_policy=life, seed=metric['seed'])
                    all_results.append(dict(arm=arm, training_policy=train, lifetime_policy=life,
                                           seed=metric['seed'], iteration=70000, frames=metric['frames'],
                                           render_sha256=metric['render_sha256'], metrics_sha256=digest(path)))
    write_new(a.artifact_root/'metrics/records.json', dict(schema='basketball-crossing-metrics/v1',
        iteration=70000, endpoint_count=len(all_results), frame_count=sum(len(r['frames']) for r in all_results),
        runtime=runtime, records=all_results, complete=True))


if __name__ == '__main__':
    main()

"""Serial queue for remaining authorized sparse trajectories and curve evaluations."""
import argparse
import json
import os
from pathlib import Path
import sys

from basketball_study import ARTIFACTS, DOCS, ROOT, digest, supervise, write_new
from training_budget import atomic_json

ORDER = [('stg-full', 0), ('freetimegs-sparse', 0), ('stg-full', 1),
         ('freetimegs-sparse', 1), ('stg-full', 2), ('freetimegs-sparse', 2)]


def state(**values):
    path = ARTIFACTS / 'run-state.json'
    current = json.loads(path.read_text()) if path.exists() else {}
    current.update(values, controller_pid=os.getpid())
    atomic_json(path, current)


def invoke(function, args):
    previous = sys.argv
    try:
        sys.argv = [function.__module__, *args]
        function()
    finally:
        sys.argv = previous


def main():
    argparse.ArgumentParser(description=__doc__).parse_args()
    baseline = json.loads((DOCS / 'baseline-reuse.json').read_text())
    storage = json.loads((DOCS / 'storage-001.json').read_text())
    import shutil
    if not storage['fits'] or shutil.disk_usage(ROOT).free < storage['projected_total_bytes']:
        raise RuntimeError('storage pause: resolve projected retention space before execution')
    write_new(ARTIFACTS / 'queue-process.json', dict(pid=os.getpid(), adapter_sha256=digest(__file__)))
    try:
        for arm, seed in ORDER:
            output = ARTIFACTS / f'training/{arm}-seed{seed}'
            result_path = output / 'worker-result.json'
            if result_path.exists() and json.loads(result_path.read_text())['iteration'] == 50000:
                continue
            if output.exists():
                raise RuntimeError(f'incomplete existing trajectory requires explicit recovery path: {output}')
            record = next(r for r in baseline['records'] if r['arm'] == arm and r['seed'] == seed)
            if digest(record['checkpoint']) != record['checkpoint_sha256']:
                raise ValueError('historical parent changed')
            environment = 'stg-render' if arm == 'stg-full' else 'freetimegs'
            state(stage='training', active_arm=arm, active_seed=seed, target_update=50000,
                  active_segment=str(ARTIFACTS / f'segments/{arm}-seed{seed}'))
            command = [str(ROOT / f'.local/envs/{environment}/bin/python'), 'scripts/basketball_study_train.py',
                '--arm', arm, '--seed', str(seed), '--initialization', str(ROOT / '.local/sync-pivot/basketball-static-init'),
                '--resume', record['checkpoint'], '--target-update', '50000', '--output', str(output)]
            segment = supervise(command, 'training', ARTIFACTS / f'segments/{arm}-seed{seed}')
            if segment['exit_code'] or segment['interrupted']:
                raise RuntimeError('training stopped; preserve the recovery and inspect segment logs')
            if json.loads(result_path.read_text())['iteration'] != 50000:
                raise ValueError('training did not reach the absolute target')
            print(json.dumps(dict(stage='training-completed', arm=arm, seed=seed)), flush=True)
        from basketball_study_evaluate import main as evaluate
        for arm, seed in ORDER:
            state(stage='curve-rendering', active_arm=arm, active_seed=seed)
            invoke(evaluate, ['--arm', arm, '--seed', str(seed)])
        from basketball_study_metrics import main as metrics
        for step in (10000, 20000, 30000, 50000):
            state(stage='curve-metrics', active_iteration=step)
            invoke(metrics, ['--iteration', str(step)])
        state(stage='available-arms-trained-and-evaluated', next='final report, curves and 50000-update visuals',
              full_study_complete=False, dense_arm='stopped: initialization prerequisite failed')
        write_new(ARTIFACTS / 'queue-result.json', dict(available_trajectories=6, target_update=50000,
            new_curve_evaluations=24, full_study_complete=False, dense_arm='initialization prerequisite failed'))
    except BaseException as error:
        state(stop_reason=f'{type(error).__name__}: {error}')
        raise


if __name__ == '__main__':
    main()

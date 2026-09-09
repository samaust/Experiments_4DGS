"""Plan 027 serial validation and fixed production queue; absolute update targets."""
import argparse
import json
import os
from pathlib import Path
import sys

from basketball_dense_training import ARTIFACTS, DOCS, ARMS, ORDER, configure
from basketball_study import CURVE, ROOT, digest, supervise, write_new
from training_budget import atomic_json


def state(**values):
    path = ARTIFACTS/'run-state.json'
    current = json.loads(path.read_text()) if path.exists() else {}
    current.update(values, controller_pid=os.getpid())
    atomic_json(path, current)


def job(command, stage, name):
    output = ARTIFACTS/'segments'/name
    state(stage=stage, active_segment=str(output), command=command)
    result = supervise(command, stage, output)
    if result['exit_code'] or result['interrupted']:
        raise RuntimeError(f'{stage} stopped: inspect {output}/worker.log')


def train(arm, seed, target, output, resume=None, stage='training', name=None):
    command = [str(ROOT/'.local/envs/freetimegs/bin/python'), 'scripts/basketball_dense_train.py',
        '--arm', arm, '--seed', str(seed), '--dense-initialization', str(ARTIFACTS/'initializers'/arm),
        '--target-update', str(target), '--output', str(output)]
    if resume:
        command += ['--resume', str(resume)]
    job(command, stage, name or f'train-{arm}-seed{seed}-{target}')
    result = json.loads((output/'worker-result.json').read_text())
    if not result['completed'] or result['iteration'] != target:
        raise ValueError('absolute update target not reached')


def invoke(module, args):
    old = sys.argv
    try:
        sys.argv = [module.__name__, *args]
        module.main()
    finally:
        sys.argv = old


def validate():
    for arm in ARMS:
        folder = ARTIFACTS/'validation'/arm
        train(arm, 0, 2, folder/'save', stage='validation', name=f'validate-{arm}-save')
        train(arm, 0, 3, folder/'reload', resume=folder/'save/checkpoint-000002.pt',
            stage='validation', name=f'validate-{arm}-reload')
    from basketball_dense_resources import projection
    resources = projection()
    write_new(DOCS/'resources.json', resources)
    if not resources['fits']:
        raise RuntimeError('storage pause: measured full-initializer retention exceeds available space')
    state(stage='full-initializer-validation-completed', production_updates=0)


def production():
    from basketball_dense_resources import projection
    if not projection()['fits']:
        raise RuntimeError('storage pause: measured full-initializer retention exceeds available space')
    import basketball_dense_evaluate as evaluate
    import basketball_dense_metrics as metrics
    # Both recipes are frozen before any evaluation; every seed reaches 5000
    # before any continuation. Each recipe is shared by all three seeds.
    for arm, seed in ORDER:
        folder = ARTIFACTS/f'training/{arm}-seed{seed}/005000'
        train(arm, seed, 5000, folder)
        invoke(evaluate, ['--arm', arm, '--seed', str(seed), '--iteration', '5000', '--training', str(folder)])
    for arm in ARMS:
        invoke(metrics, ['--arm', arm, '--iteration', '5000'])
    for arm, seed in ORDER:
        base = ARTIFACTS/f'training/{arm}-seed{seed}'
        train(arm, seed, 50000, base/'050000', resume=base/'005000/checkpoint-005000.pt')
        for step in CURVE[1:]:
            invoke(evaluate, ['--arm', arm, '--seed', str(seed), '--iteration', str(step), '--training', str(base/'050000')])
    for step in CURVE[1:]:
        for arm in ARMS:
            invoke(metrics, ['--arm', arm, '--iteration', str(step)])
    state(stage='training-and-metrics-completed', production_updates=300000,
        remaining='endpoint visuals, training-view diagnostic inspection, resource curves, final report and audit', complete=False)


def main():
    configure()
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('stage', choices=('validate', 'production'))
    a = p.parse_args()
    try:
        (validate if a.stage == 'validate' else production)()
    except BaseException as error:
        state(stop_reason=f'{type(error).__name__}: {error}', complete=False)
        raise


if __name__ == '__main__':
    main()

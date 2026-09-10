"""Serial Plan 028 preflight, qualification, and production controller."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess

import basketball_study
from basketball_study import MANIFEST, ROOT, digest, write_new
from basketball_dense_training import ARMS

STUDY = ROOT/'.local/basketball-crossing-repair'
OLD = ROOT/'.local/basketball-dense-training'
PARENT = {arm: OLD/f'training/{arm}-seed{{seed}}/050000/checkpoint-050000.pt' for arm in ARMS}
POLICIES = (('holdout', 'original'), ('holdout', 'repaired'),
            ('all-times', 'original'), ('all-times', 'repaired'))


def preflight():
    selection = json.loads((ROOT/'.local/sync-pivot/evaluation-inputs.json').read_text())
    parents = []
    for run in selection['runs']:
        path = ROOT/run['checkpoint']['path']
        if digest(path) != run['checkpoint']['sha256']:
            raise ValueError('historical parent changed: '+str(path))
        provenance = path.parent/'provenance.json'
        files = json.loads(provenance.read_text())['files']
        for source, expected in files.items():
            if digest(source) != expected:
                raise ValueError('historical source changed: '+source)
        parents.append(dict(method=run['method'], seed=run['seed'], path=str(path.resolve()),
                            sha256=digest(path), bytes=path.stat().st_size))
    manifest = json.loads(MANIFEST.read_text())
    expected = {(str(camera), frame) for camera in range(34) if str(camera) not in {'0','10','20','30'}
                for frame in range(50) if not 20 <= frame <= 24}
    if set(map(tuple, manifest['training_keys'])) != expected:
        raise ValueError('original training split changed')
    free = shutil.disk_usage(ROOT).free
    if free < 20*1024**3:
        raise RuntimeError('less than the required 20 GiB free-space reserve')
    result = dict(schema='basketball-crossing-repair-preflight/v1', plan=28,
        manifest_sha256=digest(MANIFEST), parents=parents,
        free_bytes=free, reserve_bytes=20*1024**3, artifact_ceiling_bytes=180*1024**3,
        gpu_concurrency=1, production_updates=480000,
        policies=[dict(training_policy=t, lifetime_policy=l) for t,l in POLICIES])
    STUDY.mkdir(parents=True, exist_ok=True)
    write_new(STUDY/'preflight.json', result)
    return result


def command_for(arm, seed, target, output, training_policy, lifetime_policy, resume):
    command = [str(ROOT/'.local/envs/freetimegs/bin/python'), 'scripts/basketball_crossing_train.py',
               '--arm', arm, '--seed', str(seed), '--dense-initialization', str(OLD/f'initializers/{arm}'),
               '--target-update', str(target), '--training-policy', training_policy,
               '--lifetime-policy', lifetime_policy, '--output', str(output), '--resume', str(resume)]
    return command


def fresh_segment(base):
    base = Path(base)
    if not base.exists():
        return base
    index = 2
    while (base.parent / f'{base.name}-retry{index}').exists():
        index += 1
    return base.parent / f'{base.name}-retry{index}'


def qualify():
    (STUDY/'qualification').mkdir(parents=True, exist_ok=True)
    records = []
    for arm in ARMS:
        for training_policy, lifetime_policy in POLICIES:
            output = STUDY/'qualification'/f'{arm}-{training_policy}-{lifetime_policy}.json'
            command = [str(ROOT/'.local/envs/freetimegs/bin/python'), 'scripts/basketball_crossing_qualify.py',
                       '--initializer', str(OLD/f'initializers/{arm}'), '--output', str(output)]
            subprocess.run(command, cwd=ROOT, check=True, env=dict(os.environ, PYTHONPATH=str(ROOT/'scripts')))
            records.append(dict(arm=arm, training_policy=training_policy,
                                lifetime_policy=lifetime_policy, output=str(output.resolve())))
    write_new(STUDY/'qualification.json', dict(schema='basketball-crossing-repair-qualifications/v1',
        records=records, max_disposable_updates=12))


def production():
    if not (STUDY/'preflight.json').exists():
        preflight()
    if not (STUDY/'qualification.json').exists():
        qualify()
    basketball_study.ARTIFACTS = STUDY
    (STUDY/'initializers').mkdir(parents=True, exist_ok=True)
    for arm in ARMS:
        link = STUDY/'initializers'/arm
        if not link.exists():
            link.symlink_to((OLD/'initializers'/arm).resolve(), target_is_directory=True)
    ledger = []
    for seed in range(3):
        for arm in ARMS:
            parent = str(PARENT[arm]).format(seed=seed)
            for training_policy, lifetime_policy in POLICIES:
                branch = STUDY/f'training/{arm}/seed{seed}/{training_policy}-{lifetime_policy}'
                marker = STUDY/f'completed-{arm}-seed{seed}-{training_policy}-{lifetime_policy}.json'
                if marker.exists():
                    ledger.append(json.loads(marker.read_text()))
                    continue
                worker_result = branch/'worker-result.json'
                if not worker_result.exists() or not json.loads(worker_result.read_text()).get('completed'):
                    result = basketball_study.supervise(command_for(arm, seed, 70000, branch,
                        training_policy, lifetime_policy, parent), 'production-training',
                        fresh_segment(STUDY/f'segments/train-{arm}-seed{seed}-{training_policy}-{lifetime_policy}'))
                    if result['exit_code'] or result['interrupted']:
                        raise RuntimeError('training stopped: '+str(branch))
                evaluation = [str(ROOT/'.local/envs/freetimegs/bin/python'), 'scripts/basketball_dense_evaluate.py',
                    '--arm', arm, '--seed', str(seed), '--iteration', '70000', '--training', str(branch),
                    '--artifact-root', str(STUDY), '--training-policy', training_policy,
                    '--lifetime-policy', lifetime_policy]
                evaluation_json = STUDY/f'evaluation/{arm}-seed{seed}/{training_policy}-{lifetime_policy}/070000/evaluation.json'
                if not evaluation_json.exists():
                    folder = evaluation_json.parent
                    if folder.exists() and not any(folder.iterdir()):
                        folder.rmdir()
                    result = basketball_study.supervise(evaluation, 'evaluation',
                        fresh_segment(STUDY/f'segments/evaluate-{arm}-seed{seed}-{training_policy}-{lifetime_policy}'))
                    if result['exit_code'] or result['interrupted']:
                        raise RuntimeError('evaluation stopped: '+str(branch))
                ledger.append(dict(arm=arm, seed=seed, training_policy=training_policy,
                                   lifetime_policy=lifetime_policy, training=str(branch)))
                write_new(marker, ledger[-1])
    write_new(STUDY/'production.json', dict(schema='basketball-crossing-repair-production/v1',
        records=ledger, production_updates=480000, serial=True, complete=True))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stage', choices=('preflight', 'qualify', 'production'))
    args = parser.parse_args()
    {'preflight': preflight, 'qualify': qualify, 'production': production}[args.stage]()


if __name__ == '__main__':
    main()

#!/usr/bin/env python3
"""Sequential ATGS offline reloads, matched metrics and fixed evidence packaging."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import time


def compare_reports(first, second):
    for field in ('bundle', 'runtime', 'renderer_sha256', 'manifest_sha256', 'iteration', 'model', 'sweep'):
        if first[field] != second[field]:
            raise ValueError('reload metadata mismatch: ' + field)
    for field, expected in (('frames', 60), ('sweep_frames', 20)):
        a, b = first[field], second[field]
        if len(a) != expected or len(b) != expected:
            raise ValueError('incomplete reload sequence')
        if a != b:
            raise ValueError('reload image metadata/hashes differ: ' + field)
    return dict(float_exact=True, held_out_frames=60, sweep_poses=20)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    repo = Path(__file__).resolve().parents[1]
    parser.add_argument('--atgs-python', type=Path, default=repo / '.local/envs/atgs/bin/python')
    parser.add_argument('--checkout', type=Path, default=repo / '.local/ATGS')
    for name in ('manifest', 'checkpoint', 'training-config', 'provenance', 'crops', 'torch-cache', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    for name, value in vars(args).items():
        # Preserve virtualenv interpreter spelling; resolving its symlink would
        # execute the base interpreter without the environment's packages.
        setattr(args, name, value.absolute())
    if args.output.exists():
        parser.error('choose a new evaluation output directory')
    manifest = json.loads(args.manifest.read_text())
    cameras = [c for c in manifest['cameras'] if c['split'] == 'test']
    if len(cameras) != 1 or cameras[0]['id'] != '0015' or len(cameras[0]['frames']) != 60:
        parser.error('requires the shared SelfCap held-out profile')
    reference = (args.manifest.parent / cameras[0]['frames'][0]['path']).parent
    if not (args.torch_cache / 'hub/checkpoints/alexnet-owt-7be5be79.pth').is_file():
        parser.error('cached AlexNet weights required before offline evaluation')
    args.output.mkdir(parents=True)
    started = time.monotonic()
    helpers = Path(__file__).parent
    env = dict(os.environ, TORCH_HOME=str(args.torch_cache), OMP_NUM_THREADS='2', MKL_NUM_THREADS='2')
    stages = []

    def run(label, interpreter, command):
        command = [str(interpreter), *map(str, command)]
        stage = dict(label=label, command=command, status='running')
        stages.append(stage)
        (args.output / 'commands.json').write_text(json.dumps(stages, indent=2) + '\n')
        log = args.output / (label + '.log')
        print('Running ' + label, flush=True)
        tick = time.monotonic()
        try:
            with log.open('x') as stream:
                result = subprocess.run(command, env=env, stdout=stream, stderr=subprocess.STDOUT)
            stage.update(exit_code=result.returncode, status='completed' if result.returncode == 0 else 'failed')
            if result.returncode:
                print('Failed command: ' + repr(command) + '\n' + log.read_text(), file=sys.stderr)
                raise SystemExit(result.returncode)
        except OSError as error:
            stage.update(status='launch-error', error=str(error))
            print('Failed command: ' + repr(command) + '\n' + str(error), file=sys.stderr)
            raise
        finally:
            stage['wall_seconds'] = time.monotonic() - tick
            (args.output / 'commands.json').write_text(json.dumps(stages, indent=2) + '\n')

    for label in ('reload-a', 'reload-b'):
        command = [helpers / 'render-atgs-manifest.py', '--checkout', args.checkout,
                   '--manifest', args.manifest, '--checkpoint', args.checkpoint,
                   '--training-config', args.training_config, '--provenance', args.provenance,
                   '--output', args.output / label]
        if label == 'reload-a':
            command.append('--benchmark')
        run(label, args.atgs_python, command)
    first = json.loads((args.output / 'reload-a/render.json').read_text())
    second = json.loads((args.output / 'reload-b/render.json').read_text())
    equality = compare_reports(first, second)
    comparisons = {}
    for label, directory, count in [('heldout', 'images/0015', 60), ('sweep', 'sweep', 20)]:
        path = args.output / ('compare-' + label + '.json')
        run('compare-' + label, sys.executable, [helpers / 'compare-render-reloads.py',
            '--first', args.output / 'reload-a' / directory, '--second', args.output / 'reload-b' / directory,
            '--expected-count', count, '--output', path])
        comparisons[label] = {k: v for k, v in json.loads(path.read_text()).items() if k != 'per_frame'}
    run('metrics', sys.executable, [helpers / 'offline-python.py', helpers / 'evaluate-reconstruction.py',
        '--predictions', args.output / 'reload-a/images/0015', '--ground-truth', reference,
        '--output', args.output / 'metrics.json', '--lpips-alex'])
    run('package', sys.executable, [helpers / 'package-stg-evidence.py', '--render-directory',
        args.output / 'reload-a', '--manifest', args.manifest, '--crops', args.crops,
        '--output', args.output / 'evidence'])
    report = dict(status='completed', model='atgs', iteration=first['iteration'],
                  manifest_sha256=first['manifest_sha256'], bundle=first['bundle'], runtime=first['runtime'],
                  incomplete_training=first['incomplete_training'], benchmark=first['benchmark'],
                  checkpoint_bytes=first['checkpoint_bytes'], equality=equality, comparisons=comparisons,
                  metrics=json.loads((args.output / 'metrics.json').read_text())['aggregate'],
                  wall_seconds=time.monotonic() - started, stages=stages)
    (args.output / 'evaluation.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({k: v for k, v in report.items() if k in ('iteration', 'metrics', 'wall_seconds')}, indent=2))


if __name__ == '__main__':
    main()

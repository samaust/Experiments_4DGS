#!/usr/bin/env python3
"""Run sequential offline STG reloads, strict comparisons, metrics and packaging.

Evaluation only: does not train or alter the training budget. Any subprocess
failure stops the pipeline with its exact command and log; no network fallback.
"""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time


def main():
    started = time.monotonic()
    started_utc = datetime.datetime.now(datetime.timezone.utc).isoformat()
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--checkout', type=Path, required=True)
    p.add_argument('--manifest', type=Path, required=True)
    p.add_argument('--checkpoint', type=Path, required=True)
    p.add_argument('--crops', type=Path, required=True)
    p.add_argument('--torch-cache', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    for key, value in vars(a).items():
        setattr(a, key, value.resolve())
    if a.output.exists():
        p.error('choose a new output directory')
    manifest = json.loads(a.manifest.read_text())
    tests = [c for c in manifest['cameras'] if c['split'] == 'test']
    if len(tests) != 1 or tests[0]['id'] != '0015' or len(tests[0]['frames']) != 60:
        p.error('this adapter requires the SelfCap dance1 held-out profile')
    camera = tests[0]
    reference = (a.manifest.parent/camera['frames'][0]['path']).parent
    # LPIPS must use already cached weights, without attempting a download.
    if not (a.torch_cache/'hub/checkpoints/alexnet-owt-7be5be79.pth').is_file():
        p.error('cached AlexNet weights required before offline evaluation')
    a.output.mkdir(parents=True)
    helpers = Path(__file__).resolve().parent
    env = dict(os.environ, TORCH_HOME=str(a.torch_cache), OMP_NUM_THREADS='2', MKL_NUM_THREADS='2')
    commands = []

    def run(label, arguments):
        command = [sys.executable, *map(str, arguments)]
        log = a.output/(label+'.log')
        stage = dict(label=label, command=command, log=str(log), status='running',
                     started_utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
        commands.append(stage)
        def record():
            (a.output/'commands.json').write_text(json.dumps(commands, indent=2)+'\n')
        record()
        print('Running '+label, flush=True)
        tick = time.monotonic()
        try:
            with log.open('x') as stream:
                result = subprocess.run(command, env=env, stdout=stream, stderr=subprocess.STDOUT)
            stage.update(exit_code=result.returncode,
                         status='completed' if result.returncode == 0 else 'failed')
        except OSError as error:
            stage.update(status='launch-error', error=str(error))
            print('Failed command: '+repr(command)+'\n'+str(error), file=sys.stderr)
            raise
        finally:
            stage.update(wall_seconds=time.monotonic()-tick,
                         ended_utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
            record()
        if result.returncode:
            print('Failed command: '+repr(command)+'\n'+log.read_text(), file=sys.stderr)
            raise SystemExit(result.returncode)

    for label in ('reload-a', 'reload-b'):
        args = [helpers/'offline-python.py', helpers/'render-stg-manifest.py',
                '--checkout', a.checkout, '--manifest', a.manifest,
                '--checkpoint', a.checkpoint, '--output', a.output/label]
        if label == 'reload-a':
            args.append('--benchmark')
        run(label, args)
    render = json.loads((a.output/'reload-a/render.json').read_text())
    second = json.loads((a.output/'reload-b/render.json').read_text())
    for key in ('checkpoint_sha256', 'manifest_sha256', 'iteration', 'model', 'sweep'):
        if render[key] != second[key]:
            p.error('reload provenance differs: '+key)
    comparisons = {}
    for label, directory, count in [('heldout', 'images/0015', 60), ('sweep', 'sweep', 20)]:
        run('compare-'+label, [helpers/'compare-render-reloads.py',
            '--first', a.output/'reload-a'/directory, '--second', a.output/'reload-b'/directory,
            '--expected-count', count, '--output', a.output/('compare-'+label+'.json')])
        comparisons[label] = {k: v for k, v in
            json.loads((a.output/('compare-'+label+'.json')).read_text()).items() if k != 'per_frame'}
    run('metrics', [helpers/'offline-python.py', helpers/'evaluate-reconstruction.py',
        '--predictions', a.output/'reload-a/images/0015', '--ground-truth', reference,
        '--output', a.output/'metrics.json', '--lpips-alex'])
    run('package', [helpers/'package-stg-evidence.py', '--render-directory', a.output/'reload-a',
        '--manifest', a.manifest, '--crops', a.crops, '--output', a.output/'evidence'])
    report = dict(status='completed', iteration=render['iteration'], model=render['model'],
        started_utc=started_utc, ended_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        wall_seconds=time.monotonic()-started, stages=commands,
        incomplete_training=render['incomplete_training'], benchmark=render['benchmark'],
        reload_comparisons=comparisons, checkpoint_bytes=render['checkpoint_bytes'],
        metrics=json.loads((a.output/'metrics.json').read_text())['aggregate'],
        checkpoint_sha256=render['checkpoint_sha256'], manifest_sha256=render['manifest_sha256'],
        helpers_sha256={f.name: hashlib.sha256(f.read_bytes()).hexdigest() for f in
            [Path(__file__), *[helpers/n for n in ('offline-python.py', 'render-stg-manifest.py',
             'compare-render-reloads.py', 'evaluate-reconstruction.py', 'package-stg-evidence.py')]]},
        cpu_threads=2, gpu_execution='sequential; no GPU training should overlap this command')
    (a.output/'evaluation.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps({k: v for k, v in report.items() if k != 'benchmark'}, indent=2))


if __name__ == '__main__':
    main()

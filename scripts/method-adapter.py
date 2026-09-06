#!/usr/bin/env python3
"""Run a method command against a shared manifest and retain provenance.

Adapters for individual research repositories can use this small wrapper.  It
does not translate representations or alter arguments; it records the exact
manifest digest, command, method configuration, and result in the run folder.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time


def sha256(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--manifest', type=Path, required=True)
    p.add_argument('--method', required=True)
    p.add_argument('--config', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--cwd', type=Path, required=True)
    p.add_argument('command', nargs=argparse.REMAINDER)
    a = p.parse_args()
    command = a.command[1:] if a.command[:1] == ['--'] else a.command
    if not command:
        p.error('a method command is required after --')
    if a.output.exists():
        p.error('refusing to overwrite existing run directory')
    manifest = json.loads(a.manifest.read_text())
    if manifest.get('schema') != 'dynamic-gaussian-scene/v1':
        p.error('unsupported manifest schema')
    a.output.mkdir(parents=True)
    record = {'method': a.method, 'manifest': str(a.manifest.resolve()),
              'manifest_sha256': sha256(a.manifest), 'config': str(a.config.resolve()),
              'config_sha256': sha256(a.config), 'command': command,
              'cwd': str(a.cwd.resolve()), 'environment': {
                  key: os.environ[key] for key in ('CUDA_HOME', 'TORCH_CUDA_ARCH_LIST')
                  if key in os.environ}}
    (a.output / 'command.json').write_text(json.dumps(record, indent=2) + '\n')
    start = time.monotonic()
    with (a.output / 'run.log').open('w') as log:
        result = subprocess.run(command, cwd=a.cwd, env=os.environ.copy(),
                                stdout=log, stderr=subprocess.STDOUT)
    result_record = dict(record, exit_code=result.returncode,
                         wall_seconds=time.monotonic() - start)
    (a.output / 'result.json').write_text(json.dumps(result_record, indent=2) + '\n')
    print(json.dumps(result_record, indent=2))
    raise SystemExit(result.returncode)


if __name__ == '__main__':
    main()

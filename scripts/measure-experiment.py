"""Run a command with a two-second GPU baseline and 200 ms device sampling."""
import argparse
import csv
import datetime
import json
import os
from pathlib import Path
import subprocess
import time

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--output', type=Path, required=True)
p.add_argument('--cwd', type=Path, required=True)
p.add_argument('--env', action='append', default=[])
p.add_argument('command', nargs=argparse.REMAINDER)
a = p.parse_args()
command = a.command[1:] if a.command[:1] == ['--'] else a.command
a.output.mkdir(parents=True, exist_ok=False)
env = dict(os.environ)
root = Path(__file__).resolve().parents[1]
work = root / '.local'
env.update(CUDA_HOME='/usr/local/cuda-13.0', CC='/usr/bin/gcc', CXX='/usr/bin/g++',
           TORCH_CUDA_ARCH_LIST='8.9', MAX_JOBS='8', PYTHONUNBUFFERED='1',
           HF_HOME=str(work / 'cache/huggingface'), TORCH_HOME=str(work / 'cache/torch'),
           UV_CACHE_DIR=str(work / 'cache/uv'), XDG_CACHE_HOME=str(work / 'cache/xdg'),
           MPLCONFIGDIR=str(work / 'cache/matplotlib'))
env['PATH'] = '/usr/local/cuda-13.0/bin:' + env['PATH']
for assignment in a.env:
    key, value = assignment.split('=', 1)
    env[key] = value
record = dict(command=command, cwd=str(a.cwd.resolve()), environment={k:env[k] for k in
              ['CUDA_HOME','CC','CXX','TORCH_CUDA_ARCH_LIST','MAX_JOBS','HF_HOME','TORCH_HOME',
               'UV_CACHE_DIR','XDG_CACHE_HOME','MPLCONFIGDIR']},
              started_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
              sampling_note='200 ms device-wide usage, two-second pre-run baseline; may miss brief peaks')
record['environment'].update(dict(assignment.split('=',1) for assignment in a.env))
(a.output / 'command.json').write_text(json.dumps(record, indent=2)+'\n')
with (a.output / 'gpu.csv').open('w') as gpu, (a.output / 'run.log').open('w') as log:
    sampler = subprocess.Popen(['nvidia-smi','--query-gpu=timestamp,memory.used,utilization.gpu',
                                '--format=csv,nounits','-lms','200'], stdout=gpu, stderr=subprocess.STDOUT)
    try:
        time.sleep(2)
        record['command_started_utc'] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        start = time.monotonic()
        result = subprocess.run(command, cwd=a.cwd, env=env, stdout=log, stderr=subprocess.STDOUT)
        record.update(exit_code=result.returncode, wall_seconds=time.monotonic()-start,
                      command_ended_utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
    finally:
        sampler.terminate()
        sampler.wait(timeout=10)
rows = list(csv.DictReader((a.output / 'gpu.csv').open()))
try:
    memory_key = next(key for key in rows[0] if key.strip().startswith('memory.used'))
    memory = [float(row[memory_key]) for row in rows]
    record.update(gpu_samples=len(memory), baseline_mib=memory[:10], sampled_peak_mib=max(memory))
except (KeyError, ValueError, IndexError, StopIteration):
    record['gpu_sampling_error'] = 'See gpu.csv'
(a.output / 'measurement.json').write_text(json.dumps(record, indent=2)+'\n')
print(json.dumps(record, indent=2), flush=True)
raise SystemExit(record['exit_code'])

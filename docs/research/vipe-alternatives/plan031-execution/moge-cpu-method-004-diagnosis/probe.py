import importlib,json,sys,time
from pathlib import Path
started=time.monotonic()
source=Path('/home/auss/git_repos/samaust/Experiments_4DGS/.local/vipe-alternatives/plan031-20260913T032700Z/jobs/plan069-D6-setup-001/source')
sys.path.insert(0,str(source))
import torch
assert not torch.cuda.is_initialized()
try:
 importlib.import_module('moge.model.v3')
except RuntimeError as exc:
 print(json.dumps(dict(status='red',exact_symptom='0 active drivers' in str(exc),error=str(exc),elapsed_seconds=time.monotonic()-started,cuda_initialized=torch.cuda.is_initialized())),flush=True)
 raise SystemExit(1)
print(json.dumps(dict(status='green',elapsed_seconds=time.monotonic()-started,cuda_initialized=torch.cuda.is_initialized())),flush=True)

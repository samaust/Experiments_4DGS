import functools,importlib,inspect,json,sys,time
from pathlib import Path
started=time.monotonic()
sys.path.insert(0,'/home/auss/git_repos/samaust/Experiments_4DGS/.local/vipe-alternatives/plan031-20260913T032700Z/jobs/plan069-D6-setup-001/source')
import torch,triton
assert not torch.cuda.is_initialized()
from triton.runtime import driver
original=triton.runtime.Autotuner.__init__
signature=inspect.signature(original)
counts=dict(adapted=0,bench_calls=0)
def deferred_benchmark(*args,**kwargs):
 counts['bench_calls']+=1
 raise PermissionError('CPU qualification prohibits GPU benchmark execution')
@functools.wraps(original)
def constructor(self,*args,**kwargs):
 bound=signature.bind(self,*args,**kwargs)
 if bound.arguments.get('do_bench') is None:
  bound.arguments['do_bench']=deferred_benchmark
  counts['adapted']+=1
 return original(*bound.args,**bound.kwargs)
triton.runtime.Autotuner.__init__=constructor
try:
 module=importlib.import_module('moge.model.v3')
finally:
 triton.runtime.Autotuner.__init__=original
assert hasattr(module,'MoGeModel')
assert counts['bench_calls']==0
assert not torch.cuda.is_initialized()
print(json.dumps(dict(status='green',elapsed_seconds=time.monotonic()-started,counts=counts,cuda_initialized=torch.cuda.is_initialized(),constructor_restored=triton.runtime.Autotuner.__init__ is original)),flush=True)

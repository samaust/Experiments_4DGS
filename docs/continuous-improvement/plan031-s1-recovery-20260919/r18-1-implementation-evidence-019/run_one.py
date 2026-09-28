import sys, os, time, tempfile, unittest
from pathlib import Path
ROOT = Path('/home/auss/git_repos/samaust/Experiments_4DGS')
sys.path.insert(0, str(ROOT/'scripts'))
sys.path.insert(0, str(ROOT/'tests'))
os.environ['PYTHONPATH'] = str(ROOT/'scripts')
for k in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS','OPENCV_FOR_THREADS_NUM'):
    os.environ[k]='1'
os.environ['VIPE_CPU_VALIDATION']='1'
os.environ.pop('S1_HELPER_DIAGNOSTIC',None); os.environ.pop('S1_RECEIPT_DIAGNOSTIC',None)
os.environ['S1_VALIDATION_RUN_DIRECTORY'] = tempfile.mkdtemp(prefix='s1run-')
try: os.setsid()
except Exception: pass
loader = unittest.TestLoader()
suite = unittest.TestSuite()
import test_vipe_benchmark_supervisor as T
cls = T.HelperSessionTests
for name in sys.argv[1:]:
    suite.addTests(loader.loadTestsFromName(name, cls))
start=time.time()
res = unittest.TextTestRunner(verbosity=2).run(suite)
print('ELAPSED', round(time.time()-start,1), 'errors', len(res.errors), 'failures', len(res.failures))
for e in res.errors[:5]: print('ERR', e[0].id(), str(e[1])[:200])

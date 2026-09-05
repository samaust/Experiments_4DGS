"""Save source, environment and artifact provenance for the five experiments."""
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT / '.local'
OUT = WORK / 'runs/evidence-inventory-20260905'
OUT.mkdir(exist_ok=False)

def run(command, cwd=ROOT):
    result = subprocess.run(command, cwd=cwd, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    return {'command':command, 'exit_code':result.returncode, 'output':result.stdout}

report = {'sources':{}, 'environments':{}, 'artifacts':{}}
for name in ['splaTV','SpacetimeGaussians','Mango-GS','NoPo4D','pytorch3d']:
    report['sources'][name] = {key:run(command, WORK/name) for key,command in {
        'revision':['git','rev-parse','HEAD'], 'submodules':['git','submodule','status','--recursive'],
        'changes':['git','status','--short']}.items()}
for name in ['stg-render','mango-render','nopo4d','downloads']:
    py = str(WORK/'envs'/name/'bin/python')
    packages = run(['uv','pip','freeze','--cache-dir',str(WORK/'cache/uv'),'--python',py])
    (OUT/(name+'-installed.txt')).write_text(packages['output'])
    report['environments'][name] = run([py,'-c',
        'import sys,sysconfig; print(sys.executable,sys.version); print("Py_GIL_DISABLED",sysconfig.get_config_var("Py_GIL_DISABLED"))'])
    if name != 'downloads':
        report['environments'][name]['torch_assertions'] = run([py,'-c',
            'import torch,torchvision; assert torch.__version__=="2.13.0+cu130"; assert torchvision.__version__=="0.28.0+cu130"; print(torch.__version__,torchvision.__version__,torch.version.cuda)'])
        report['environments'][name]['pip_check'] = run(['uv','pip','check','--cache-dir',str(WORK/'cache/uv'),'--python',py])
for key,command in {'uv':['uv','--version'],'node':['node','--version'], 'os':['uname','-a'],
                    'compiler':['/usr/bin/g++','--version'], 'nvcc':['/usr/local/cuda-13.0/bin/nvcc','--version'],
                    'disk':['du','-sb',*[str(WORK/x) for x in ['data','weights','envs','cache','runs']]]}.items():
    report[key] = run(command)
paths = [WORK/'splaTV/model.splatv', WORK/'splaTV/sear-steak-lite.splatv',
         WORK/'downloads/stg/n3d_sear_steak_lite_allcam.zip', WORK/'downloads/sear_steak.zip',
         *sorted((WORK/'weights').rglob('*.ply')), *sorted((WORK/'weights').rglob('deform.pth')),
         *sorted((ROOT/'patches').glob('*.patch')), ROOT/'environments/constraints-cu130.txt']
for path in paths:
    if not path.is_file(): continue
    h=hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda:stream.read(1024*1024), b''): h.update(chunk)
    report['artifacts'][str(path.relative_to(ROOT))] = {'bytes':path.stat().st_size,'sha256':h.hexdigest()}
(OUT/'inventory.json').write_text(json.dumps(report,indent=2)+'\n')
print(OUT)

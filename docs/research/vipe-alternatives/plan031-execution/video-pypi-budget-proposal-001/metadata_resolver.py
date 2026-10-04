import time,json,urllib.request,hashlib
from pathlib import Path
from packaging.requirements import Requirement
from packaging.specifiers import SpecifierSet
from packaging.version import Version,InvalidVersion
from packaging.utils import canonicalize_name,parse_wheel_filename
from packaging.markers import default_environment
start=time.monotonic();out=Path(__file__).parent/'pypi-closure-004';out.mkdir(exist_ok=False);received=0;cache={};
prior=Path(__file__).parent/'pypi-closure'
for source in (prior,Path(__file__).parent/'pypi-closure-002',Path(__file__).parent/'pypi-closure-003'):
 for saved in source.glob('*.json'):
  if '.receipt.' not in saved.name and saved.name!='failure.json':cache[saved.stem]=(json.loads(saved.read_text()),saved)
preferred={canonicalize_name(row['name']):row['version'] for row in json.loads(Path('/home/auss/git_repos/samaust/Experiments_4DGS/.local/vipe-alternatives/plan031-20260913T032700Z/prepare/plan069-D5-native-cpu-002/installed-dependencies.json').read_text())['packages']}
preferred.update({'torch':'2.14.1','torchvision':'0.29.1','contourpy':'1.3.2','matplotlib':'3.10.8','opencv-python':'4.11.0.86','triton':'3.8.0','cuda-bindings':'13.0.3','nvidia-nvjitlink':'13.4.92'})
environment=dict(default_environment(),python_version='3.11',python_full_version='3.11.15',implementation_version='3.11.15',sys_platform='linux',platform_system='Linux',platform_machine='x86_64',extra='')
recipe=json.loads((Path.cwd()/'configs/vipe-alternatives/video-environment-v2.json').read_text());roots=[Requirement(x.replace('2.14.1+cu130','2.14.1').replace('0.29.1+cu130','0.29.1')) for x in recipe['requirements']+recipe['constraints']]
def fetch(name,version=None):
 global received
 key=name+'-'+(version or 'index')
 if key in cache:
  data=cache[key][1].read_bytes();(out/(key+'.json')).write_bytes(data);return cache[key][0]
 assert time.monotonic()-start<120,'metadata deadline'
 url='https://pypi.org/pypi/'+name+('/'+version if version else '')+'/json'
 with urllib.request.urlopen(url,timeout=15) as r:data=r.read(2**21+1);assert len(data)<=2**21
 received+=len(data);assert received<=16*2**20,'metadata aggregate byte limit'
 (out/(key+'.json')).write_bytes(data);(out/(key+'.receipt.json')).write_text(json.dumps({'url':url,'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest(),'elapsed_from_start':time.monotonic()-start})+'\n');x=json.loads(data);cache[key]=(x,out/(key+'.json'));return x

def wheel(x):
 matches=[]
 for f in x['urls']:
  if f['yanked'] or not f['filename'].endswith('.whl'):continue
  _,_,_,tags=parse_wheel_filename(f['filename']);scores=[]
  for tag in tags:
   interpreter=tag.interpreter;abi=tag.abi;platform=tag.platform
   python_ok=interpreter in ('py3','py2.py3','cp311') or (abi=='abi3' and interpreter.startswith('cp') and interpreter[2:].isdigit() and int(interpreter[2:])<=311)
   platform_ok=platform=='any' or (platform.endswith('x86_64') and (platform.startswith('manylinux') or platform=='linux_x86_64'))
   if python_ok and platform_ok and abi in ('none','abi3','cp311'):scores.append(3 if interpreter=='cp311' else 2 if abi=='abi3' else 1)
  if scores:matches.append((max(scores),f['filename'],f))
 return max(matches,key=lambda item:(item[0],item[1]))[2] if matches else None

def applicable(req,extras):return req.marker is None or any(req.marker.evaluate(dict(environment,extra=extra)) for extra in ({''}|set(extras)))
def candidate(name,spec,constraints):
 versions=[]
 exacts=[s.version.rstrip('.*') for s in spec if s.operator=='==']
 if exacts:versions=[Version(exacts[0])]
 elif name in preferred and spec.contains(preferred[name]):versions=[Version(preferred[name])]
 else:
  index=fetch(name)
  for value in index['releases']:
   try:v=Version(value)
   except InvalidVersion:continue
   if not v.is_prerelease and not v.is_devrelease and spec.contains(v):versions.append(v)
 for version in sorted(versions,reverse=True):
  x=fetch(name,str(version));f=wheel(x)
  if not f or x['info'].get('requires_python') and not SpecifierSet(x['info']['requires_python']).contains('3.11.15'):continue
  bad=False
  for value in x['info'].get('requires_dist') or []:
   req=Requirement(value);other=canonicalize_name(req.name)
   if applicable(req,()) and other in constraints:
    exacts=[s.version for s in constraints[other] if s.operator=='==' and '*' not in s.version]
    if exacts and any(not req.specifier.contains(v) for v in exacts):bad=True;break
  if not bad:return x,f
 raise ValueError('no compatible metadata wheel for '+name+' '+str(spec))
selected={};constraints={};extras={}
for iteration in range(20):
 reqs=list(roots)
 for name,(x,f) in selected.items():
  reqs += [Requirement(value) for value in x['info'].get('requires_dist') or [] if applicable(Requirement(value),extras.get(name,set()))]
 new={};newextras={}
 for req in reqs:
  name=canonicalize_name(req.name);new[name]=SpecifierSet(str(new.get(name,''))+(',' if name in new else '')+str(req.specifier));newextras.setdefault(name,set()).update(req.extras)
 changed=False
 for name,spec in sorted(new.items()):
  if name not in selected or not spec.contains(selected[name][0]['info']['version']):selected[name]=candidate(name,spec,new);changed=True
 if set(selected)-set(new):
  for name in set(selected)-set(new):selected.pop(name)
  changed=True
 if extras!=newextras:changed=True
 constraints=new;extras=newextras
 if not changed:break
else:raise ValueError('metadata closure failed to converge')
rows=[]
for name,(x,f) in sorted(selected.items()):
 requires=[]
 for value in x['info'].get('requires_dist') or []:
  req=Requirement(value)
  if applicable(req,extras.get(name,set())):
   other=canonicalize_name(req.name);assert other in selected and req.specifier.contains(selected[other][0]['info']['version']),(name,req)
   requires.append(value)
 rows.append(dict(name=name,version=x['info']['version'],filename=f['filename'],url=f['url'],bytes=f['size'],sha256=f['digests']['sha256'],requires_python=x['info'].get('requires_python'),requires_dist=requires,requested_extras=sorted(extras.get(name,set())),license=x['info'].get('license'),license_expression=x['info'].get('license_expression'),metadata_url=f'https://pypi.org/pypi/{name}/{x["info"]["version"]}/json'))
result=dict(status='resolved-primary-release-metadata-not-installed',distribution='distinct PyPI unsuffixed Torch/Vision; pending explicit user distribution choice',target=environment,iterations=iteration+1,packages=rows,total_selected_wheel_bytes=sum(r['bytes'] for r in rows),metadata_received_bytes=received,cpu_elapsed_seconds=time.monotonic()-start,installed_artifact_forecast=None,limitations=['release JSON dependency declarations; wheel-specific METADATA must be verified before actual lock','installed/temporary disk growth not yet known','no cache reuse credit or setup authority'])
(out/'closure.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'packages':len(rows),'wheel_bytes':result['total_selected_wheel_bytes'],'metadata_bytes':received,'elapsed':result['cpu_elapsed_seconds']}))

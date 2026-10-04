import urllib.request,time,json,hashlib,email
from pathlib import Path
from packaging.requirements import Requirement
from packaging.version import Version
from packaging.utils import canonicalize_name
start=time.monotonic();base=Path(__file__).parent;out=base/'wheel-pep658-metadata-002';out.mkdir(exist_ok=False);closure=json.loads((base/'pypi-closure-004/closure.json').read_text());selected={r['name']:r for r in closure['packages']};received=0;rows=[]
for row in closure['packages']:
 url=row['url']+'.metadata';t=time.monotonic();deadline=120-(time.monotonic()-start);assert deadline>0
 try:
  saved=base/'wheel-pep658-metadata-001'/(row['name']+'.metadata')
  if saved.exists():data=saved.read_bytes()
  else:
   with urllib.request.urlopen(url,timeout=min(20,deadline)) as r:
    data=r.read(2**20+1);assert len(data)<=2**20
   received+=len(data);assert received<=4*2**20
  (out/(row['name']+'.metadata')).write_bytes(data);metadata=email.message_from_bytes(data);assert canonicalize_name(metadata['Name'])==row['name'] and Version(metadata['Version'])==Version(row['version'])
  dependencies=[]
  for value in metadata.get_all('Requires-Dist',[]):
   req=Requirement(value);applies=req.marker is None or any(req.marker.evaluate(dict(closure['target'],extra=e)) for e in (set(row['requested_extras'])|{''}))
   if applies:
    name=canonicalize_name(req.name);assert name in selected and req.specifier.contains(selected[name]['version']),(row['name'],value)
    dependencies.append(value)
  rows.append(dict(name=row['name'],version=row['version'],wheel_metadata_version=metadata['Version'],url=url,bytes=len(data),sha256=hashlib.sha256(data).hexdigest(),requires_dist=dependencies,elapsed_seconds=time.monotonic()-t))
  (out/'progress.json').write_text(json.dumps({'packages':rows,'metadata_received_bytes':received,'cpu_elapsed_seconds':time.monotonic()-start},indent=2)+'\n')
 except Exception as e:
  (out/'failure.json').write_text(json.dumps({'name':row['name'],'url':url,'error':str(e),'metadata_received_bytes':received,'cpu_elapsed_seconds':time.monotonic()-start},indent=2)+'\n');raise
result=dict(status='wheel-specific-metadata-closure-verified',packages=rows,metadata_received_bytes=received,cpu_elapsed_seconds=time.monotonic()-start,scope='prospective distinct PyPI distribution only; no wheel/install/model/GPU; METADATA hash is independently retained, full wheel hashes remain unverified until actual approved acquisition')
(out/'verification.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'packages':len(rows),'metadata_bytes':received,'elapsed':result['cpu_elapsed_seconds']}))

import time,json,urllib.request,struct,io,zipfile,re,hashlib,os
from pathlib import Path
start=time.monotonic();base=Path(__file__).parent;out=base/'wheel-directory-metadata-001';out.mkdir(exist_ok=False);closure=json.loads((base/'pypi-closure-004/closure.json').read_text());received=0;rows=[];block=os.statvfs(Path.cwd()).f_frsize
for row in closure['packages']:
 name=row['name'];size=row['bytes'];url=row['url'];deadline=120-(time.monotonic()-start);assert deadline>0
 def fetch(first,last,filename):
  global received
  wanted=last-first+1;assert wanted<=2**21 and received+wanted<=8*2**20
  t=time.monotonic()
  with urllib.request.urlopen(urllib.request.Request(url,headers={'Range':f'bytes={first}-{last}'}),timeout=min(20,deadline)) as response:
   headers={k.lower():v for k,v in response.headers.items()};body=response.read(wanted+1)
   assert response.status==206 and len(body)==wanted and headers.get('content-range')==f'bytes {first}-{last}/{size}',('invalid bounded ZIP metadata response',name,response.status,headers.get('content-range'),len(body))
  received+=len(body);(out/filename).write_bytes(body)
  (out/(filename+'.json')).write_text(json.dumps({'url':url,'range':f'bytes={first}-{last}','status':206,'content_range':headers['content-range'],'bytes':len(body),'sha256':hashlib.sha256(body).hexdigest(),'elapsed_seconds':time.monotonic()-t})+'\n');return body
 end=fetch(size-22,size-1,name+'-end.bin');signature,disk,cd_disk,disk_entries,entries,cd_size,cd_offset,comment=struct.unpack('<4s4H2LH',end)
 assert signature==b'PK\x05\x06' and not disk and not cd_disk and not comment and entries<65535 and cd_offset+cd_size==size-22,(name,'unsupported ZIP metadata layout')
 directory=fetch(cd_offset,cd_offset+cd_size-1,name+'-directory.bin')
 with zipfile.ZipFile(io.BytesIO(directory+end)) as archive:
  files=archive.infolist();assert len(files)==entries
  payload=sum(f.file_size for f in files if not f.is_dir());allocated=sum(((f.file_size+block-1)//block)*block for f in files if not f.is_dir())
 rows.append(dict(name=name,version=row['version'],filename=row['filename'],wheel_bytes=size,wheel_sha256=row['sha256'],file_count=len(files),expanded_payload_bytes=payload,expanded_block_rounded_bytes=allocated,central_directory_bytes=cd_size))
 result=dict(status='metadata-only-archive-size-forecast',scope='distinct PyPI distribution pending explicit user choice; archive directory metadata only, no complete wheel, extraction, installation or model',filesystem_block_bytes=block,packages=rows,metadata_received_bytes=received,expanded_payload_bytes=sum(r['expanded_payload_bytes'] for r in rows),expanded_block_rounded_bytes=sum(r['expanded_block_rounded_bytes'] for r in rows),file_count=sum(r['file_count'] for r in rows),cpu_elapsed_seconds=time.monotonic()-start)
 (out/'progress.json').write_text(json.dumps(result,indent=2)+'\n')
(out/'forecast.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:result[k] for k in ('metadata_received_bytes','expanded_payload_bytes','expanded_block_rounded_bytes','file_count','cpu_elapsed_seconds')}))

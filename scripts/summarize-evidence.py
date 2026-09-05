"""Collect completed experiment measurements, sizes, video metadata and model hashes."""
import csv
import hashlib
import json
from pathlib import Path
import subprocess

ROOT=Path(__file__).resolve().parents[1]
WORK=ROOT/'.local'
out=WORK/'runs/evidence-inventory-20260905'
report={'runs':{},'models':{},'videos':{}}
for folder in sorted((WORK/'runs').glob('evidence-*-20260905*')):
    if not folder.is_dir(): continue
    entry={'bytes':sum(p.stat().st_size for p in folder.rglob('*') if p.is_file())}
    if (folder/'measurement.json').is_file():
        entry['measurement']=json.loads((folder/'measurement.json').read_text())
        rows=list(csv.reader((folder/'gpu.csv').open()))[1:]
        mem=[float(r[1]) for r in rows]
        entry['gpu']={'samples':len(mem),'baseline_mib':mem[:10],'peak_mib':max(mem)}
    if (folder/'browser/browser.json').is_file():
        entry['browser']=json.loads((folder/'browser/browser.json').read_text())
    report['runs'][folder.name]=entry
    for video in folder.rglob('*.mp4'):
        result=subprocess.run(['ffprobe','-v','error','-show_entries','stream=width,height,nb_frames,r_frame_rate',
                               '-of','json',str(video)],capture_output=True,text=True,check=True)
        report['videos'][str(video.relative_to(ROOT))]=json.loads(result.stdout)
for name in ['models--bralani01--nopo4d','models--depth-anything--DA3-LARGE-1.1']:
    folder=WORK/'cache/huggingface/hub'/name
    revision=(folder/'refs/main').read_text().strip()
    files={}
    for path in sorted((folder/'snapshots'/revision).iterdir()):
        if not path.is_file(): continue
        h=hashlib.sha256()
        with path.open('rb') as stream:
            for chunk in iter(lambda:stream.read(1024*1024),b''):h.update(chunk)
        files[path.name]={'bytes':path.stat().st_size,'sha256':h.hexdigest()}
    report['models'][name]={'revision':revision,'files':files}
report['final_storage']=subprocess.run(['du','-sb',*[str(WORK/x) for x in ['data','weights','envs','cache','runs','tools']]],
                                     capture_output=True,text=True,check=True).stdout
(out/'results.json').write_text(json.dumps(report,indent=2)+'\n')
print(out/'results.json')

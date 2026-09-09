"""Fixed training-view ground-truth/initializer/checkpoint comparison panels."""
import argparse
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from basketball_dense_training import ARTIFACTS, ARMS
from basketball_study import MANIFEST, PILOT, digest, write_new


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--iteration',type=int,choices=(0,5000,50000),required=True)
    p.add_argument('--seed',type=int,choices=range(3),default=0)
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args()
    manifest=json.loads(MANIFEST.read_text())
    cameras={c['id']:c for c in manifest['cameras']}
    sources={}; files={str(MANIFEST):digest(MANIFEST)}
    expected={(c,f) for c in (1,11,21,31) for f in PILOT}
    for arm in ARMS:
        for step in ((0,) if a.iteration==0 else (0,a.iteration)):
            folder=ARTIFACTS/'diagnostics'/arm/('initial' if step==0 else f'seed{a.seed}/{step:06d}')
            path=folder/'result.json'; result=json.loads(path.read_text())
            if (result['arm']!=arm or result['iteration']!=step or
                    (step and result['seed']!=a.seed) or len(result['records'])!=12 or
                    {(r['camera'],r['frame']) for r in result['records']}!=expected):
                raise ValueError('diagnostic recipe, seed, time, or view coverage mismatch')
            files[str(path)]=digest(path)
            sources[arm,step]=(folder,{(r['camera'],r['frame']):r for r in result['records']})
    def read(path,sha):
        if digest(path)!=sha:raise ValueError('diagnostic image changed')
        image=Image.open(path).convert('RGB')
        if image.size!=(960,540):raise ValueError('diagnostic resolution changed')
        return image
    a.output.mkdir(parents=True,exist_ok=False)
    artifacts=[]
    font=ImageFont.load_default(size=18)
    for camera,frame in sorted(expected):
        gt=cameras[str(camera)]['frames'][frame]
        panels=[read(MANIFEST.parent/gt['path'],gt['sha256'])]
        labels=['Ground truth']
        for arm in ARMS:
            for step in ((0,) if a.iteration==0 else (0,a.iteration)):
                folder,rows=sources[arm,step];row=rows[camera,frame]
                panels.append(read(folder/row['path'],row['sha256']))
                labels.append(f'{arm} / '+('initialization' if step==0 else f'update {step}'))
        canvas=Image.new('RGB',(960*len(panels),592))
        draw=ImageDraw.Draw(canvas)
        draw.text((4,3),f'TRAINING-VIEW DIAGNOSTIC: camera {camera}, frame {frame}, seed {a.seed}; not held-out quality evidence',fill='white',font=font)
        for i,(panel,label) in enumerate(zip(panels,labels)):
            draw.text((960*i+4,28),label,fill='white',font=font)
            canvas.paste(panel,(960*i,52))
        path=a.output/f'camera{camera}-frame{frame}.png'
        canvas.save(path)
        artifacts.append(dict(camera=camera,frame=frame,path=path.name,sha256=digest(path),columns=labels))
    write_new(a.output/'artifacts.json',dict(iteration=a.iteration,seed=a.seed,
        scope='training-view diagnostics; not held-out quality evidence',files=files,artifacts=artifacts))


if __name__=='__main__':main()

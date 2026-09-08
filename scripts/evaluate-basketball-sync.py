"""Bounded fresh-process checkpoint reload, rendering and Basketball metrics."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time


def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def atomic(path,value):
    from training_budget import atomic_json
    atomic_json(path,value)


def load_model(a):
    from functools import lru_cache
    import torch
    from basketball_scene import BasketballScene,FreeTimeBasketballScene
    state=torch.load(a.checkpoint,map_location='cpu',weights_only=True)
    provenance=state['provenance']
    if provenance['files'].get(str(a.manifest.resolve()))!=digest(a.manifest):
        raise ValueError('checkpoint manifest mismatch')
    for path,expected in provenance['files'].items():
        if digest(path)!=expected:raise ValueError('checkpoint provenance changed: '+path)
    if a.method=='stg-full':
        from stg_checkpoint import restore_checkpoint
        root=a.checkout.resolve();sys.path[:0]=[str(root),str(root/'thirdparty/gaussian_splatting')]
        from helper_train import getrenderpip,trbfunction
        from thirdparty.gaussian_splatting.scene.oursfull import GaussianModel
        if state['variant']!='full':raise ValueError('requires STG Full')
        model=GaussianModel(3,'sandwich')
        iteration,_,_=restore_checkpoint(a.checkpoint,model,variant='full',provenance=provenance,device='cuda')
        model.rgbdecoder.eval();render,settings,rasterizer=getrenderpip('train_ours_full')
        background=torch.zeros(9,device='cuda');scene=BasketballScene(a.manifest)
        @lru_cache(maxsize=2)
        def camera(key):return scene.camera(key,device='cuda',full=True)
        def pixels(key):
            view=camera(key)
            return render(view,model,None,background,basicfunction=trbfunction,
                          GRsetting=settings,GRzer=rasterizer)['render']
        return scene,model,iteration,pixels
    from dataclasses import asdict
    from types import MethodType
    from freetimegs_checkpoint import restore_checkpoint
    from freetimegs_model import NativeFreeTimeModel
    from freetimegs_source import load_initializer,load_temporal_methods
    from freetimegs_training import load_training
    from freetimegs_normalization import load_normalization,normalize_camera
    config=json.loads((a.checkpoint.parent/'training-config.json').read_text())
    if digest(a.checkpoint.parent/'training-config.json')!=provenance['configuration_sha256']:
        raise ValueError('native configuration changed')
    cfg,_,training_source=load_training(a.checkout);cfg.start_frame,cfg.end_frame=0,50
    if asdict(cfg)!=config['native']:raise ValueError('native config mismatch')
    methods,render_source=load_temporal_methods(a.checkout,include_render=True)
    _,init_source=load_initializer(a.checkout)
    model=NativeFreeTimeModel.__new__(NativeFreeTimeModel)
    model.cfg=cfg;model.device='cuda'
    model.source_digests=dict(initializer=init_source,render=render_source,**training_source)
    for name,method in methods.items():setattr(model,name,MethodType(method,model))
    iteration,_=restore_checkpoint(a.checkpoint,model,provenance=provenance)
    helper,source=load_normalization(a.checkout)
    if source!=config['normalization']['source']:raise ValueError('normalization source changed')
    transform=config['normalization']['transform']
    import numpy as np
    transform=np.array(transform,dtype=np.float32)
    class Normalized(FreeTimeBasketballScene):
        def camera(self,key,*,device,load_image=False):
            return normalize_camera(super().camera(key,device=device,load_image=load_image),transform,helper['transform_cameras'])
    scene=Normalized(a.manifest);degree=min(max(iteration-1,0)//cfg.sh_degree_interval,cfg.sh_degree)
    @lru_cache(maxsize=2)
    def camera(key):return scene.camera(key,device='cuda')
    def pixels(key):
        view=camera(key)
        return model.render(view,sh_degree=degree)[0][0,...,:3].permute(2,0,1)
    return scene,model,iteration,pixels


def render(a):
    import socket
    def deny(*args,**kwargs):raise RuntimeError('offline evaluation prohibits network access')
    socket.create_connection=deny;socket.socket.connect=deny;socket.socket.connect_ex=deny
    import numpy as np
    import torch
    from PIL import Image
    torch.set_num_threads(2);torch.hub.set_dir(str(a.torch_cache.resolve()/'hub'))
    deadline=float(os.environ['TRAINING_STOP_MONOTONIC'])
    scene,model,iteration,pixels=load_model(a)
    from basketball_scene import BasketballScene
    regions=json.loads(a.regions.read_text())
    if regions['manifest_sha256']!=scene.sha256:raise ValueError('evaluation regions mismatch')
    regions={(r['camera'],r['frame_id']):r for r in regions['frames']}
    keys=sorted(regions,key=lambda k:(int(k[0]),k[1]))
    probes=[(str(c),f) for c in [0,10,20,30] for f in [0,22,49]]+[('1',22)]
    if a.repeat:keys=probes
    a.output.mkdir(parents=True,exist_ok=False)
    records=[];torch.cuda.reset_peak_memory_stats()
    with torch.no_grad():
        for key in keys:
            if time.monotonic()>deadline-40:break
            prediction=pixels(key)
            if prediction.shape!=(3,540,960) or not torch.isfinite(prediction).all():raise ValueError('invalid native image')
            array=prediction.clamp(0,1).permute(1,2,0).cpu().numpy()
            path=a.output/f'{key[0]}-{key[1]:06d}.png'
            quantized=np.round(array*255).astype(np.uint8);Image.fromarray(quantized).save(path)
            row=dict(camera=key[0],frame_id=key[1],normalized_time=scene.frames[key]['normalized_time'],
                     path=path.name,sha256=digest(path),float_sha256=hashlib.sha256(array.tobytes()).hexdigest())
            if not a.repeat:
                row['split']='heldout-camera' if key[0] in ['0','10','20','30'] else 'temporal-interpolation'
                row['bbox']=regions[key]['bbox']
                row['target_sha256']=scene.frames[key]['sha256']
                row['target_path']=str((scene.path.parent/scene.frames[key]['path']).resolve())
            records.append(row)
            if len(records)%25==0:print(json.dumps(dict(images=len(records),iteration=iteration,repeat=a.repeat)),flush=True)
        benchmark=None
        if not a.repeat and time.monotonic()<deadline-45:
            # Warmed camera cache excludes camera/ray construction from throughput.
            for _ in range(5):pixels(('0',25))
            durations=[]
            for _ in range(30):
                torch.cuda.synchronize();start=time.perf_counter();pixels(('0',25));torch.cuda.synchronize()
                durations.append(time.perf_counter()-start)
            benchmark=dict(warmups=5,count=30,seconds=durations,fps=30/sum(durations),camera='0',frame=25,
                           includes='native renderer and warmed camera-cache lookup; excludes camera/ray construction, loading, PNG encoding and metrics')
    result=dict(schema='basketball-checkpoint-evaluation/v1',method=a.method,iteration=iteration,repeat=a.repeat,
        complete=len(records)==len(keys),expected_images=len(keys),frames=records,benchmark=benchmark,
        checkpoint_sha256=digest(a.checkpoint),checkpoint_bytes=a.checkpoint.stat().st_size,
        manifest_sha256=scene.sha256,regions_sha256=digest(a.regions),regions_path=str(a.regions.resolve()),script_sha256=digest(__file__),
        peak_allocated_bytes=torch.cuda.max_memory_allocated(),peak_reserved_bytes=torch.cuda.max_memory_reserved(),
        process_id=os.getpid(),complete_state_restored=True,network='Python sockets disabled',
        metric_policy='metrics deferred to identical pinned container for both native renderer environments')
    atomic(a.output/'render.json',result)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('stage',choices=['evaluate','render']);p.add_argument('--method',choices=['stg-full','freetimegs'],required=True)
    for name in ['checkout','manifest','checkpoint','regions','output']:p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--torch-cache',type=Path,default=Path('.local/cache/torch'));p.add_argument('--repeat',action='store_true')
    a=p.parse_args()
    if 'TRAINING_STOP_MONOTONIC' not in os.environ:p.error('requires campaign supervisor')
    if a.stage=='render':return render(a)
    a.output.mkdir(parents=True,exist_ok=False)
    for label in ['first','repeat']:
        if time.monotonic()>float(os.environ['TRAINING_STOP_MONOTONIC'])-45:break
        command=[sys.executable,__file__,'render','--method',a.method]
        for k in ['checkout','manifest','checkpoint','regions','torch_cache']:
            command+=['--'+k.replace('_','-'),str(getattr(a,k))]
        command+=['--output',str(a.output/label)]
        if label=='repeat':command+=['--repeat']
        with (a.output/(label+'.log')).open('w') as log:
            subprocess.run(command,stdout=log,stderr=subprocess.STDOUT,check=True)
    first=json.loads((a.output/'first/render.json').read_text())
    repeat=a.output/'repeat/render.json';comparison=None
    if repeat.exists():
        second=json.loads(repeat.read_text());original={(r['camera'],r['frame_id']):r for r in first['frames']}
        pairs=[(original[(r['camera'],r['frame_id'])],r) for r in second['frames'] if (r['camera'],r['frame_id']) in original]
        comparison=dict(fresh_process=first['process_id']!=second['process_id'],compared=len(pairs),
            png_identical=all(x['sha256']==y['sha256'] for x,y in pairs),
            float_identical=all(x['float_sha256']==y['float_sha256'] for x,y in pairs),
            complete=second['complete'] and len(pairs)==13)
    atomic(a.output/'evaluation.json',dict(method=a.method,iteration=first['iteration'],complete=first['complete'],
        checkpoint_sha256=first['checkpoint_sha256'],reload=comparison,first='first/render.json',repeat='repeat/render.json'))


if __name__=='__main__':main()

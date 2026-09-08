"""Native STG Full / FreeTimeGS workers for the bounded Plan 024 controls."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import random
import signal
import socket
import time

from training_budget import atomic_json


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def prepare_free(scene, initialization, checkout):
    import numpy as np
    import torch
    from basketball_scene import FreeTimeBasketballScene
    from freetimegs_normalization import load_normalization, normalize_camera
    helper, source=load_normalization(checkout)
    with np.load(initialization/'static-cloud.npz',allow_pickle=False) as a:
        xyz=a['positions'].copy();rgb=a['colors'].copy()
    if xyz.shape!=rgb.shape or xyz.shape[1]!=3 or not np.isfinite(xyz).all():
        raise ValueError('invalid static initialization')
    cameras=np.concatenate([scene.camera(k,device='cpu').camtoworlds.numpy() for k in scene.training_keys(25)])
    T1=helper['similarity_from_cameras'](cameras)
    T2=helper['align_principle_axes'](helper['transform_points'](T1,xyz))
    transform=T2@T1
    xyz=helper['transform_points'](transform,xyz).astype(np.float32)
    centers=helper['transform_cameras'](transform,cameras)[:,:3,3]
    scale=float(np.linalg.norm(centers-centers.mean(0),axis=1).max())*1.1
    valid=np.linalg.norm(xyz,axis=1)<5*scale;xyz,rgb=xyz[valid],rgb[valid]
    times=sorted({scene.frames[k]['normalized_time'] for k in scene.training_keys() if k[1]%5==0})
    data=dict(positions=np.tile(xyz,(len(times),1)),colors=np.tile(rgb,(len(times),1)),
              velocities=np.zeros((len(xyz)*len(times),3),np.float32),
              times=np.repeat(np.array(times,np.float32),len(xyz))[:,None],
              durations=np.full((len(xyz)*len(times),1),.2,np.float32))
    class Normalized(FreeTimeBasketballScene):
        def camera(self,key,*,device,load_image=False):
            return normalize_camera(super().camera(key,device=device,load_image=load_image),transform,helper['transform_cameras'])
    evidence=dict(transform=transform.tolist(),scene_scale=scale,source=source,
        local_center_times=times,duration=.2,points=len(data['positions']),
        policy='same static map/color prior, zero velocity, local copies at retained every-fifth training frame; native normalization')
    return Normalized(scene.path),{k:torch.from_numpy(v.copy()) for k,v in data.items()},evidence


def train_free(a):
    import numpy as np
    import torch
    from dataclasses import asdict
    from basketball_scene import FreeTimeBasketballScene
    from atgs_sampler import ManifestBalancedSampler
    from freetimegs_training import load_training
    from freetimegs_model import NativeFreeTimeModel
    from freetimegs_checkpoint import save_checkpoint
    from torchmetrics.image.lpip import LearnedPerceptualImagePatchSimilarity
    stopping=[False];signal.signal(signal.SIGTERM,lambda *_:stopping.__setitem__(0,True))
    deadline=float(os.environ['TRAINING_STOP_MONOTONIC'])
    torch.hub.set_dir(str(a.torch_cache/'hub'))
    random.seed(a.seed);np.random.seed(a.seed);torch.manual_seed(a.seed);torch.cuda.manual_seed_all(a.seed)
    cfg,_,source=load_training(a.checkout)
    cfg.start_frame,cfg.end_frame=0,50
    scene,data,normalization=prepare_free(FreeTimeBasketballScene(a.manifest),a.initialization,a.checkout)
    configuration=dict(native=asdict(cfg),normalization=normalization,seed=a.seed,source=source,target_steps=5000,
                       alexnet_sha256=digest(a.torch_cache/'hub/checkpoints/alexnet-owt-7be5be79.pth'))
    atomic_json(a.output/'training-config.json',configuration)
    provenance=json.loads((a.output/'provenance.json').read_text())
    provenance['configuration_sha256']=digest(a.output/'training-config.json')
    atomic_json(a.output/'checkpoint-provenance.json',provenance)
    lpips=LearnedPerceptualImagePatchSimilarity(net_type='alex',normalize=True).cuda()
    model=NativeFreeTimeModel(a.checkout,cfg,data,scene_scale=normalization['scene_scale'],device='cuda')
    model.enable_training(a.checkout,scene_scale=normalization['scene_scale'],device='cuda',lpips=lpips)
    del data
    sampler=ManifestBalancedSampler(scene,1,seed=a.seed);iteration=0;saved=[]
    def save():
        path=a.output/f'checkpoint-{iteration:06d}.pt'
        save_checkpoint(path,model,iteration=iteration,loop_state={'sampler':sampler.state_dict()},provenance=provenance)
        saved.append(dict(iteration=iteration,path=str(path),sha256=digest(path)))
        atomic_json(a.output/'checkpoints.json',saved)
    while iteration<5000 and not stopping[0] and time.monotonic()<deadline-120:
        key=next(sampler);camera=scene.training_camera(key,device='cuda')
        metrics=model.training_step(iteration,camera,model.schedulers);torch.cuda.synchronize()
        metrics={k:float(v.detach()) if isinstance(v,torch.Tensor) else v for k,v in metrics.items()}
        if not np.isfinite(metrics['loss']):raise RuntimeError('nonfinite native loss')
        iteration+=1
        with (a.output/'loss.jsonl').open('a') as f:f.write(json.dumps(dict(iteration=iteration,key=key,**metrics))+'\n')
        if iteration<=5 or iteration%100==0:print(json.dumps(dict(iteration=iteration,**metrics)),flush=True)
        if iteration in (1000,2000,5000):save()
    if not saved or saved[-1]['iteration']!=iteration:save()
    atomic_json(a.output/'worker-result.json',dict(iteration=iteration,target_steps=5000,
        budget_limited=iteration<5000,checkpoints=saved,peak_allocated_bytes=torch.cuda.max_memory_allocated(),
        peak_reserved_bytes=torch.cuda.max_memory_reserved()))


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--method',choices=['stg-full','freetimegs'],required=True)
    p.add_argument('--manifest',type=Path,required=True)
    p.add_argument('--initialization',type=Path,required=True)
    p.add_argument('--checkout',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--torch-cache',type=Path,default=Path('.local/cache/torch'))
    p.add_argument('--seed',type=int,choices=range(3),required=True)
    a=p.parse_args()
    if 'TRAINING_STOP_MONOTONIC' not in os.environ:p.error('requires Plan 024 supervisor')
    for k in ('manifest','initialization','checkout','output','torch_cache'):setattr(a,k,getattr(a,k).resolve())
    init=json.loads((a.initialization/'result.json').read_text())
    if (init['schema']!='basketball-static-initialization/v1' or init['manifest_sha256']!=digest(a.manifest)
            or init['archive_sha256']!=digest(a.initialization/'static-cloud.npz')
            or init['ply_sha256']!=digest(a.initialization/'initialization.ply')):
        raise ValueError('initialization provenance mismatch')
    def deny(*args,**kwargs):raise RuntimeError('network disabled in reconstruction worker')
    socket.create_connection=deny;socket.socket.connect=deny;socket.socket.connect_ex=deny
    a.output.mkdir(parents=True,exist_ok=False)
    files=[a.manifest,a.initialization/'result.json',Path(__file__),Path(__file__).with_name('basketball_scene.py')]
    helpers=['stg_scene.py','sync_timing.py','training_rng.py']
    if a.method=='stg-full':
        helpers+=['stg_checkpoint.py','stg_train_source.py','train-stg-manifest.py']
        files += [a.checkout/p for p in ['train.py','helper_train.py',
            'thirdparty/gaussian_splatting/arguments/__init__.py',
            'thirdparty/gaussian_splatting/scene/oursfull.py',
            'thirdparty/gaussian_splatting/renderer/__init__.py']]
    else:
        helpers+=['freetimegs_checkpoint.py','freetimegs_training.py','freetimegs_source.py',
                  'freetimegs_model.py','freetimegs_normalization.py','freetimegs_scene.py','atgs_sampler.py']
        files += [a.checkout/'src/simple_trainer_freetime_4d_pure_relocation.py',
                  a.checkout/'datasets/normalize.py']
    files += [Path(__file__).with_name(p) for p in helpers]
    atomic_json(a.output/'provenance.json',dict(plan=24,method=a.method,seed=a.seed,files={str(f):digest(f) for f in files}))
    if a.method=='freetimegs':return train_free(a)
    spec=importlib.util.spec_from_file_location('stg_worker',Path(__file__).with_name('train-stg-manifest.py'))
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    a.model='full';a.max_steps=5000;a.resume=None
    module.worker(a)


if __name__=='__main__':main()

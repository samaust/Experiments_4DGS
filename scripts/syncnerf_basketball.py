"""Calibrated training-only data adapter for the released Sync-NeRF K-Planes trainer."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import runpy
import signal
import sys
import time

import numpy as np


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def export_offsets(values):
    """Convert native additive normalized-time shifts to reference-1 seconds."""
    values = np.asarray(values)
    if values.shape != (8,) or not np.isfinite(values).all():
        raise ValueError('expected eight finite camera shifts')
    return -(values-values[0])*(99/25)/1.6


def prepare(a):
    import cv2
    from basketball_scene import render_calibration
    root=Path(__file__).resolve().parents[1]
    frozen=json.loads(a.freeze.read_text())
    calibration_path=root/frozen['calibration_path']
    if digest(calibration_path)!=frozen['calibration_sha256']:raise ValueError('calibration changed')
    calibration=json.loads(calibration_path.read_text())
    cameras={e['camera_id']:e for e in calibration['cameras']}
    a.output.mkdir(parents=True,exist_ok=False)
    entries=[]
    for c in frozen['syncnerf_camera_ids']:
        camera,K,d=render_calibration(cameras[c],frozen['scale'])
        source=frozen['sources'][c];path=root/source['path']
        if source['camera_id']!=c or digest(path)!=source['sha256']:raise ValueError('source changed')
        maps=cv2.initUndistortRectifyMap(K,np.array(d),None,K,(960,540),cv2.CV_32FC1)
        cap=cv2.VideoCapture(str(path));frames=[]
        directory=a.output/str(c);directory.mkdir()
        for f in range(150):
            ok,image=cap.read()
            if not ok:raise ValueError('source decode failed')
            if f<50:continue
            image=cv2.resize(image,(960,540),interpolation=cv2.INTER_AREA)
            image=cv2.remap(image,*maps,cv2.INTER_LINEAR,borderMode=cv2.BORDER_CONSTANT)
            out=directory/f'{f:06d}.png'
            if not cv2.imwrite(str(out),image):raise RuntimeError('image write failed')
            frames.append(dict(frame_id=f,path=str(out.relative_to(a.output)),sha256=digest(out)))
        cap.release();entries.append(dict(camera_id=c,calibration=camera,frames=frames))
        print(json.dumps(dict(camera=c,frames=len(frames))),flush=True)
    with np.load(root/'.local/sync-pivot/basketball-static-init/static-cloud.npz',allow_pickle=False) as d:
        xyz=d['positions']
    low,high=xyz.min(0),xyz.max(0);margin=(high-low)*.05
    data=dict(schema='syncnerf-basketball-inputs/v1',cameras=entries,source_fps=25,
        source_frames=[50,149],freeze_sha256=digest(a.freeze),reference_camera=1,
        scene_bbox=[(low-margin).tolist(),(high+margin).tolist()],
        scene_bbox_policy='full accepted static-map extent plus five percent per axis; fixed before training',
        normalization=dict(origin_seconds=2.,duration_seconds=99/25,normalize_scale=.8),
        test_image_optimization=False,script_sha256=digest(__file__))
    (a.output/'inputs.json').write_text(json.dumps(data,indent=2)+'\n')


class Rays:
    """Uniform camera/frame/pixel sampling; no evaluation images in memory."""
    def __init__(self,path,batch_size):
        import cv2
        import torch
        self.torch=torch;self.batch_size=batch_size
        m=json.loads(path.read_text());self.metadata=m
        self.ids=[c['camera_id'] for c in m['cameras']]
        if (len(self.ids)!=8 or len(set(self.ids))!=8 or self.ids[0]!=1
                or set(self.ids)&{0,10,20,30} or m['test_image_optimization']):
            raise ValueError('invalid Sync-NeRF training-camera split')
        self.scene_bbox=torch.tensor(m['scene_bbox'],dtype=torch.float32)
        self.is_ndc=False;self.is_contracted=False;self.cam_nums=8;self.num_images=800
        self.images=[];self.origins=[];self.rotations=[];self.intrinsics=[]
        for c in m['cameras']:
            if [f['frame_id'] for f in c['frames']]!=list(range(50,150)):
                raise ValueError('Sync-NeRF must fit frames 50–149 only')
            frames=[]
            for f in c['frames']:
                file=path.parent/f['path']
                if digest(file)!=f['sha256']:raise ValueError('input changed')
                frames.append(cv2.cvtColor(cv2.imread(str(file)),cv2.COLOR_BGR2RGB))
            self.images.append(np.stack(frames))
            k=c['calibration'];self.origins.append(k['center']);self.rotations.append(k['world_to_camera_R']);self.intrinsics.append(k['K'])
        self.images=np.stack(self.images);self.origins=np.array(self.origins,dtype=np.float32)
        self.rotations=np.array(self.rotations,dtype=np.float32);self.intrinsics=np.array(self.intrinsics,dtype=np.float32)
        corners=np.array(list(__import__('itertools').product(*zip(*m['scene_bbox']))))
        self.far=float(np.linalg.norm(corners[None]-self.origins[:,None],axis=-1).max()*1.1)

    def reset_iter(self):pass
    def __iter__(self):return self
    def __next__(self):
        n=self.batch_size;c=np.random.randint(8,size=n);f=np.random.randint(100,size=n)
        x=np.random.randint(960,size=n);y=np.random.randint(540,size=n)
        K=self.intrinsics[c]
        local=np.stack(((x+.5-K[:,0,2])/K[:,0,0],(y+.5-K[:,1,2])/K[:,1,1],np.ones(n)),axis=-1)
        directions=np.einsum('ni,nij->nj',local,self.rotations[c]);directions/=np.linalg.norm(directions,axis=-1)[:,None]
        t=self.torch
        return dict(rays_o=t.from_numpy(self.origins[c]),rays_d=t.tensor(directions,dtype=t.float32),
                    imgs=t.tensor(self.images[c,f,y,x],dtype=t.float32)/255,
                    timestamps=t.tensor((f/99*2-1)*.8,dtype=t.float32),camids=t.tensor(c,dtype=t.long),
                    near_fars=t.tensor([[.01,self.far]],dtype=t.float32),bg_color=t.zeros(3))


def train(a):
    if 'TRAINING_STOP_MONOTONIC' not in os.environ:raise ValueError('requires campaign supervisor')
    import torch
    sys.path.insert(0,str(a.checkout.resolve()))
    from plenoxels.runners.video_trainer import VideoTrainer
    from sync_timing import SCHEMA,CONVENTION,validate_timing
    stopped=[False];signal.signal(signal.SIGTERM,lambda *_:stopped.__setitem__(0,True))
    deadline=float(os.environ['TRAINING_STOP_MONOTONIC'])
    np.random.seed(a.seed);torch.manual_seed(a.seed);torch.cuda.manual_seed_all(a.seed)
    config_path=a.checkout/'plenoxels/configs/blender/hybrid/box.py'
    config=runpy.run_path(str(config_path))['config']
    data=Rays(a.inputs,config['batch_size'])
    config.update(test_optim=False,num_frames=100,valid_every=-1,save_every=-1,
                  logdir=str(a.output.resolve()),expname='model',
                  scene_bbox=data.metadata['scene_bbox'],data_dirs=[str(a.inputs.resolve())])
    a.output.mkdir(parents=True,exist_ok=False)
    (a.output/'configuration.json').write_text(json.dumps(dict(config=config,author_config_sha256=digest(config_path),
        inputs_sha256=digest(a.inputs),adapter_sha256=digest(__file__),seed=a.seed,
        policy='native Box hybrid optimizer, losses, proposal sampling and 90001-step schedule; camera-specific calibrated rays and four-second training-only window; budget-limited pilot'),indent=2)+'\n')
    class BoundedTrainer(VideoTrainer):
        def post_step(self,progress_bar):
            super().post_step(progress_bar)
            if self.global_step%1000==0:self.save_model()
            if stopped[0] or time.monotonic()>deadline-60:
                raise TimeoutError('plan allocation checkpoint boundary')
    trainer=BoundedTrainer(tr_loader=data,tr_dset=data,ts_dset=data,**config)
    try:trainer.train()
    except TimeoutError:pass
    trainer.save_model();torch.cuda.synchronize()
    values=trainer.model.cam_offset.detach().cpu().numpy()
    # t_norm=(source-2)/3.96*1.6-.8; native additive d implies source-offset.
    offsets=export_offsets(values)
    ids=[str(i) for i in range(34)];covered=list(map(str,data.ids))
    timing=dict(schema=SCHEMA,convention=CONVENTION,units='seconds',kind='estimated',camera_ids=ids,
        reference_camera='1',offset_seconds={c:float(offsets[covered.index(c)]) if c in covered else None for c in ids},
        uncertainty_seconds={c:None for c in ids},coverage={'camera_ids':covered},source_window_seconds=[2.,6.],
        source_support_seconds={c:[0.,10.] for c in ids},normalization={'origin_seconds':0.,'duration_seconds':2.},
        provenance={'method':'official Sync-NeRF K-Planes hybrid with calibrated Basketball ray adapter',
                    'configuration_sha256':digest(a.output/'configuration.json'),'iterations':trainer.global_step,
                    'budget_limited':trainer.global_step<config['num_steps'],'seed':a.seed,'test_optim':False,
                    'not_approved_for_full_rig_reconstruction':True})
    validate_timing(timing)
    (a.output/'timing.json').write_text(json.dumps(timing,indent=2,allow_nan=False)+'\n')
    (a.output/'worker-result.json').write_text(json.dumps(dict(iterations=trainer.global_step,
        peak_allocated_bytes=torch.cuda.max_memory_allocated(),peak_reserved_bytes=torch.cuda.max_memory_reserved(),
        checkpoint_sha256=digest(a.output/'model/model.pth')),indent=2)+'\n')


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('stage',choices=['prepare','train'])
    p.add_argument('--freeze',type=Path);p.add_argument('--inputs',type=Path)
    p.add_argument('--checkout',type=Path,default=Path('.local/sync-pivot/Sync-NeRF/Sync-K-Planes'))
    p.add_argument('--output',type=Path,required=True);p.add_argument('--seed',type=int,choices=range(3),default=0)
    a=p.parse_args();prepare(a) if a.stage=='prepare' else train(a)


if __name__=='__main__':main()

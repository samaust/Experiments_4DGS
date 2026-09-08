"""Identical offline image metrics and seed/temporal-block summaries for Plan 024."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import time
import numpy as np


def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def block_interval(values,*,seed=0,samples=2000):
    """Resample seeds and aligned temporal blocks, never individual pixels."""
    values=np.asarray(values,float)
    if values.ndim!=2 or values.shape[0]!=3 or not np.isfinite(values).all():
        raise ValueError('requires three seeds and finite temporal block means')
    rng=np.random.default_rng(seed);nseeds,nblocks=values.shape
    s=rng.integers(nseeds,size=(samples,nseeds));b=rng.integers(nblocks,size=(samples,nblocks))
    draws=values[s[:,:,None],b[:,None,:]].mean(axis=(1,2))
    return dict(mean=float(values.mean()),lower=float(np.quantile(draws,.025)),upper=float(np.quantile(draws,.975)),
                seeds=nseeds,blocks=nblocks,resamples=samples,
                limitation='three seeds only; one-block temporal holdout cannot estimate between-block temporal variation' if nblocks==1 else 'three seeds only; resampling conditions on this scene and fixed cameras')


def summarize(runs):
    result={};tables={}
    for method in ['stg-full','freetimegs']:
        selected=sorted([r for r in runs if r['method']==method and r['complete']],key=lambda r:r['seed'])
        if [r['seed'] for r in selected]!=[0,1,2] or len({r['iteration'] for r in selected})!=1:
            result[method]=dict(status='incomplete seed cohort or mismatched checkpoints');continue
        summary={};tables[method]={}
        for split in ['heldout-camera','temporal-interpolation']:
            for region,metrics in [('full',['psnr','ssim','lpips_alex']),('dynamic',['psnr','ssim','lpips_alex']),('motion_pixels',['psnr','mae'])]:
                for metric in metrics:
                    per_seed=[];blocks=set()
                    for run in selected:
                        groups={}
                        for row in run['frames']:
                            if row['split']==split and row.get(region) is not None:
                                groups.setdefault(row['frame_id']//5,[]).append(row[region][metric])
                        blocks.update(groups);per_seed.append(groups)
                    common=sorted(set.intersection(*(set(g) for g in per_seed)))
                    if not common:continue
                    values=np.array([[np.mean(g[b]) for b in common] for g in per_seed])
                    name='/'.join([split,region,metric]);summary[name]=block_interval(values)
                    summary[name]['block_ids']=common;tables[method][name]=(common,values)
        result[method]=dict(status='three-seed common-checkpoint summary',iteration=selected[0]['iteration'],metrics=summary)
    paired={}
    if (len(tables)==2 and result['stg-full'].get('iteration')==result['freetimegs'].get('iteration')):
        for key in tables['stg-full'].keys()&tables['freetimegs'].keys():
            b,x=tables['stg-full'][key];c,y=tables['freetimegs'][key]
            if b==c:paired[key]=block_interval(y-x)
    result['paired_methods_at_zero']=dict(direction='FreeTimeGS minus STG Full, matched seed and five-frame block; this is not a correction benefit estimate',metrics=paired)
    result['timing_correction_benefit']=dict(status='unavailable',reason='no eligible frozen full-rig correction; zero controls only')
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--inputs',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);p.add_argument('--torch-cache',type=Path,default=Path('.local/cache/torch'))
    a=p.parse_args()
    if 'TRAINING_STOP_MONOTONIC' not in os.environ:p.error('requires campaign supervisor')
    import socket
    def deny(*args,**kwargs):raise RuntimeError('network prohibited in offline metrics')
    socket.create_connection=deny;socket.socket.connect=deny;socket.socket.connect_ex=deny
    import torch
    from PIL import Image
    from skimage.metrics import structural_similarity
    from torchmetrics.image.lpip import LearnedPerceptualImagePatchSimilarity
    from training_budget import atomic_json
    torch.set_num_threads(2);torch.hub.set_dir(str(a.torch_cache.resolve()/'hub'))
    metric=LearnedPerceptualImagePatchSimilarity(net_type='alex',normalize=True).cuda().eval()
    a.output.mkdir(parents=True,exist_ok=False);inputs=json.loads(a.inputs.read_text());results=[]
    deadline=float(os.environ['TRAINING_STOP_MONOTONIC'])
    def read(path,expected):
        if digest(path)!=expected:raise ValueError('evaluation image changed')
        return np.asarray(Image.open(path).convert('RGB'),dtype=np.float32)/255
    def metrics(pred,target):
        mse=float(np.mean((pred-target)**2))
        x=torch.from_numpy(pred.copy()).permute(2,0,1)[None].cuda();y=torch.from_numpy(target.copy()).permute(2,0,1)[None].cuda()
        perceptual=float(metric(x,y));metric.reset()
        return dict(psnr=-10*float(np.log10(max(mse,1e-12))),
                    ssim=float(structural_similarity(pred,target,channel_axis=-1,data_range=1.,win_size=7,use_sample_covariance=True)),lpips_alex=perceptual)
    with torch.no_grad():
        for entry in inputs['runs']:
            path=Path(entry['render']);report=json.loads(path.read_text());rows=[];previous={}
            region_path=Path(report['regions_path'])
            if digest(region_path)!=report['regions_sha256']:raise ValueError('motion regions changed')
            masks={(r['camera'],r['frame_id']):r for r in json.loads(region_path.read_text())['frames']}
            for r in report['frames']:
                if time.monotonic()>deadline-40:break
                pred=read(path.parent/r['path'],r['sha256']);target=read(Path(r['target_path']),r['target_sha256'])
                if pred.shape!=target.shape or pred.shape!=(540,960,3):raise ValueError('invalid metric image dimensions')
                row={k:r[k] for k in ['camera','frame_id','split','bbox','normalized_time']}
                row['full']=metrics(pred,target);row['dynamic']=None
                region=masks[(r['camera'],r['frame_id'])];mask_path=region_path.parent/region['mask_path']
                if digest(mask_path)!=region['mask_sha256']:raise ValueError('motion mask changed')
                mask=np.asarray(Image.open(mask_path))>0;row['motion_pixels']=None
                if mask.any():
                    error=pred[mask]-target[mask]
                    row['motion_pixels']=dict(psnr=-10*float(np.log10(max(float(np.mean(error**2)),1e-12))),mae=float(np.mean(np.abs(error))))
                if r['bbox']:
                    x0,y0,x1,y1=r['bbox'];row['dynamic']=metrics(pred[y0:y1,x0:x1],target[y0:y1,x0:x1])
                c,f=r['camera'],r['frame_id']
                if c in previous and previous[c][0]==f-1:
                    _,pp,pt=previous[c];row['temporal_difference_mae']=float(np.mean(np.abs((pred-pp)-(target-pt))))
                previous[c]=(f,pred,target);rows.append(row)
                if len(rows)%50==0:print(json.dumps(dict(method=entry['method'],seed=entry['seed'],frames=len(rows))),flush=True)
            result=dict(method=entry['method'],seed=entry['seed'],iteration=report['iteration'],frames=rows,
                        complete=report['complete'] and len(rows)==len(report['frames']),render_sha256=digest(path))
            atomic_json(a.output/f"{entry['method']}-seed{entry['seed']}.json",result);results.append(result)
    summary=summarize(results)
    summary.update(schema='basketball-reconstruction-metrics/v1',inputs_sha256=digest(a.inputs),script_sha256=digest(__file__),
        metrics='uint8 RGB/255; PSNR capped at120dB at zero MSE; skimage SSIM window7 sample covariance; TorchMetrics1.6.0 LPIPS Alex normalize=True; dynamic metrics are crops from frozen motion proxy, not semantic ground truth',
        uncertainty='2000 seed-and-five-source-frame-block bootstrap resamples, seed0; 95% percentile interval; fixed cameras and single scene',
        gpu_peak_allocated_bytes=torch.cuda.max_memory_allocated(),gpu_peak_reserved_bytes=torch.cuda.max_memory_reserved())
    atomic_json(a.output/'summary.json',summary)


if __name__=='__main__':main()

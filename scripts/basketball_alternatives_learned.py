"""Pinned released image-only reconstruction adapters for Plan 006 snapshots.

Masked pixels are neutral gray before the documented upstream preprocessing.
This suppresses dynamic appearance but is not native correspondence masking;
subsequent geometric support must independently exclude these regions.
"""
import argparse
import json
from pathlib import Path
import resource
import shutil
import sys
import time
import numpy as np
from basketball_audit import sha256
from basketball_alternatives_protocol import TRAINING, PROTOCOL, check_inputs
from basketball_geometry import resize_opencv


def cpu(value):
    import torch
    if isinstance(value, torch.Tensor):
        return value.detach().cpu()
    if isinstance(value, dict):
        return {k:cpu(v) for k,v in value.items()}
    if isinstance(value, (list,tuple)):
        return [cpu(v) for v in value]
    return value


def project_rotations(R,t):
    """Correct small accumulated floating-point drift; reject nonrigid poses."""
    drift=float(np.linalg.norm(R@R.transpose(0,2,1)-np.eye(3),axis=(1,2)).max())
    if drift>.01 or np.any(np.linalg.det(R)<=0):
        raise ValueError(f'nonrigid native rotations: orthogonality drift {drift}')
    centers=-np.linalg.solve(R,t[...,None])[...,0]
    U,_,Vt=np.linalg.svd(R)
    R=U@Vt
    return R,-np.einsum('nij,nj->ni',R,centers),drift


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--method',choices=['da3','mast3r','map-anything'],required=True)
    p.add_argument('--source',type=Path,required=True)
    p.add_argument('--weights',type=Path,required=True)
    p.add_argument('--inputs',type=Path,required=True)
    p.add_argument('--frame',type=int)
    p.add_argument('--frames',type=int,nargs='+')
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--seed',type=int,default=0)
    p.add_argument('--cache-from',type=Path,help='Verified failed MASt3R inference cache; no fitted poses are reused')
    a = p.parse_args()
    if (a.frame is None)==(a.frames is None):
        p.error('choose --frame or --frames')
    frames=a.frames if a.frames is not None else [a.frame]
    check_inputs(TRAINING,frames)
    prepared = json.loads((a.inputs/'result.json').read_text())
    if prepared['status'] != 'prepared':
        raise ValueError('requires validated masks')
    a.output.mkdir(parents=True,exist_ok=False)
    (a.output/'images').mkdir()
    report = dict(protocol=PROTOCOL,method=a.method,frame=a.frame,frames=frames,seed=a.seed,status='running',
                  adapter_sha256=sha256(__file__), input_sha256=sha256(a.inputs/'result.json'),
                  weight_sha256=sha256(a.weights/'model.safetensors'),
                  configuration=dict(dynamic_pixels='neutral RGB 127 before preprocessing',
                                     supplied_calibration=False))
    start = time.monotonic()
    import torch
    from PIL import Image
    try:
        assert torch.cuda.is_available(), 'CUDA required'
        torch.manual_seed(a.seed)
        np.random.seed(a.seed)
        torch.cuda.reset_peak_memory_stats()
        paths=[]
        entries = {(e['camera_id'],e['source_frame_id']):e for e in prepared['observations']}
        sample_ids=[(c,f) for c in TRAINING for f in frames]
        report['sample_ids']=sample_ids
        for c,f in sample_ids:
            e=entries[c,f]
            source=a.inputs/(e['stem']+'.png'); mask=a.inputs/(e['stem']+'-static.png')
            if sha256(source)!=e['image_sha256'] or sha256(mask)!=e['mask_sha256']:
                raise ValueError('changed prepared image or mask')
            rgb=np.array(Image.open(source).convert('RGB'))
            rgb[np.array(Image.open(mask))==0]=127
            name=f'camera{c}.png' if len(frames)==1 else f'camera{c}-frame{f}.png'
            path=a.output/'images'/name
            Image.fromarray(rgb).save(path);paths.append(str(path))
        if a.method=='da3':
            from depth_anything_3.api import DepthAnything3
            model=DepthAnything3.from_pretrained(str(a.weights)).to('cuda').eval()
            pred=model.inference(paths,use_ray_pose=True)
            native=dict(extrinsics=pred.extrinsics,intrinsics=pred.intrinsics,
                        depth=pred.depth,conf=pred.conf)
            np.savez_compressed(a.output/'native.npz',**native)
            R=pred.extrinsics[:,:3,:3];t=pred.extrinsics[:,:3,3]
            h,w=pred.depth.shape[-2:]
            K=np.stack([resize_opencv(k,(w,h),(960,540)) for k in pred.intrinsics])
            report['configuration'].update(use_ray_pose=True,process_res=504,
                process_res_method='upper_bound_resize',native_size=[w,h],
                ref_view_strategy='saddle_balanced')
        elif a.method=='mast3r':
            sys.path.insert(0,str(a.source.resolve()))
            from mast3r.model import AsymmetricMASt3R
            from mast3r.cloud_opt.sparse_ga import sparse_global_alignment
            from dust3r.utils.image import load_images
            from dust3r.image_pairs import make_pairs
            model=AsymmetricMASt3R.from_pretrained(str(a.weights)).to('cuda').eval()
            imgs=load_images(paths,size=512)
            pairs=make_pairs(imgs,scene_graph='complete',prefilter=None,symmetrize=True)
            cache=a.output/'cache'
            if a.cache_from:
                previous=json.loads((a.cache_from/'result.json').read_text())
                if any(previous[k]!=report[k] for k in ('method','frame','seed','weight_sha256','input_sha256')):
                    raise ValueError('cache provenance mismatch')
                if previous['status']!='failed' or 'scipy.cluster.hierarchy' not in previous.get('error',''):
                    raise ValueError('only the known pre-optimization SciPy failure is reusable')
                shutil.copytree(a.cache_from/'cache',cache)
                report['cache_from']=str(a.cache_from)
                report['cache_result_sha256']=sha256(a.cache_from/'result.json')
            else:
                cache.mkdir()
            scene=sparse_global_alignment(paths,pairs,str(cache),model,
                lr1=.07,niter1=300,lr2=.01,niter2=300,device='cuda',
                opt_depth=True,shared_intrinsics=False,matching_conf_thr=0.)
            K_native=scene.intrinsics.detach().cpu().numpy()
            poses=scene.cam2w.detach().cpu().numpy()
            torch.save(cpu(dict(intrinsics=scene.intrinsics,cam2w=scene.cam2w,
                                depthmaps=scene.depthmaps,pts3d=scene.pts3d)),a.output/'native.pt')
            R=poses[:,:3,:3].transpose(0,2,1);t=-np.einsum('nij,nj->ni',R,poses[:,:3,3])
            h,w=imgs[0]['img'].shape[-2:]
            if (w,h)!=(512,288):
                raise ValueError('unexpected MASt3R crop; adapter only validated for 960x540 -> 512x288')
            K=np.stack([resize_opencv(k,(w,h),(960,540)) for k in K_native])
            report['configuration'].update(scene_graph='complete',lr1=.07,niter1=300,lr2=.01,
                niter2=300,opt_depth=True,shared_intrinsics=False,native_size=[w,h],
                rope='upstream torch fallback; no CUDA extension')
        else:
            from mapanything.models import MapAnything
            from mapanything.utils.image import load_images
            from mapanything.utils.cropping import crop_resize_if_necessary
            model=MapAnything.from_pretrained(str(a.weights)).to('cuda').eval()
            views=load_images(paths)
            with torch.inference_mode():
                pred=model.infer(views,memory_efficient_inference=True,minibatch_size=1,
                                 use_amp=True,amp_dtype='bf16',apply_mask=True,mask_edges=True,
                                 apply_confidence_mask=False,use_multiview_confidence=False)
            torch.save(cpu(pred),a.output/'native.pt')
            poses=np.stack([v['camera_poses'][0].cpu().numpy() for v in pred])
            K_native=np.stack([v['intrinsics'][0].cpu().numpy() for v in pred])
            R=poses[:,:3,:3].transpose(0,2,1);t=-np.einsum('nij,nj->ni',R,poses[:,:3,3])
            h,w=views[0]['img'].shape[-2:]
            # Recover the exact upstream affine pixel transform using a centered
            # synthetic K; it is never provided to the reconstruction model.
            original_K=np.array([[960.,0,479.5],[0,960.,269.5],[0,0,1.]])
            _, transformed_K=crop_resize_if_necessary(Image.open(paths[0]),(w,h),intrinsics=original_K)
            A=transformed_K@np.linalg.inv(original_K)
            K=np.linalg.inv(A)[None]@K_native
            report['configuration'].update(memory_efficient_inference=True,minibatch_size=1,
                native_size=[w,h],pixel_transform=A.tolist(),amp_dtype='bf16')
        R,t,drift=project_rotations(R,t)
        report['rotation_projection_max_orthogonality_drift']=drift
        if len(frames)>1:
            from scipy.spatial.transform import Rotation
            centers=-np.einsum('nji,nj->ni',R,t)
            native_observations=[dict(camera_id=c,source_frame_id=f,R=R[i].tolist(),
                t=t[i].tolist(),K=K[i].tolist()) for i,(c,f) in enumerate(sample_ids)]
            (a.output/'per-observation-calibration.json').write_text(json.dumps(native_observations,indent=2)+'\n')
            grouped_R=[];grouped_C=[];grouped_K=[]
            for c in TRAINING:
                indices=[i for i,(camera,_) in enumerate(sample_ids) if camera==c]
                grouped_R.append(Rotation.from_matrix(R[indices]).mean().as_matrix())
                grouped_C.append(centers[indices].mean(0))
                grouped_K.append(np.median(K[indices],axis=0))
            R=np.array(grouped_R);K=np.array(grouped_K)
            t=-np.einsum('nij,nj->ni',R,np.array(grouped_C))
            report['configuration']['static_rig_projection']='SO(3) mean rotation, mean center, median K per camera; raw untied native predictions retained'
        cameras=[]
        for i,c in enumerate(TRAINING):
            if not all(np.isfinite(v).all() for v in (R[i],t[i],K[i])):
                raise ValueError(f'nonfinite camera {c}')
            if not np.allclose(R[i]@R[i].T,np.eye(3),atol=1e-4) or not np.isclose(np.linalg.det(R[i]),1,atol=1e-4):
                raise ValueError(f'invalid rotation {c}')
            if min(K[i,0,0],K[i,1,1])<=0:
                raise ValueError(f'invalid focal {c}')
            cameras.append(dict(camera_id=c,R=R[i].tolist(),t=t[i].tolist(),K=K[i].tolist(),
                                center=(-R[i].T@t[i]).tolist()))
        value=dict(schema='basketball-native-calibration/v1',protocol=PROTOCOL,complete=True,
                   pixel_convention='opencv-integer-centers',pose_convention='world-to-camera',
                   image_size=[960,540],cameras=cameras)
        (a.output/'calibration-0.json').write_text(json.dumps(value,indent=2,allow_nan=False)+'\n')
        report.update(status='complete',model_id=0,cameras=list(TRAINING))
    except BaseException as error:
        report.update(status='failed',error=f'{type(error).__name__}: {error}')
        raise
    finally:
        report.update(wall_seconds=time.monotonic()-start,
                      peak_host_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
                      peak_allocated_bytes=torch.cuda.max_memory_allocated(),
                      peak_reserved_bytes=torch.cuda.max_memory_reserved())
        (a.output/'result.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')


if __name__=='__main__':
    main()

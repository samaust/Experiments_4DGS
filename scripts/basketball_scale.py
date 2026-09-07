"""Frozen training-view ViPE scale gate for the immutable full-rig calibration."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import time

import numpy as np
from basketball_audit import PIN, sha256
from basketball_continuation_audit import CALIBRATION, CALIBRATION_SHA, TRAINING, WORKSPACE, verify_hashes


def read(path):
    return json.loads(Path(path).read_text())


def write(path, value):
    with Path(path).open('x') as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write('\n')


def protocol(path):
    p = read(path)
    if p['calibration_sha256'] != CALIBRATION_SHA or p['training_camera_ids'] != list(TRAINING):
        raise ValueError('scale protocol camera/calibration mismatch')
    if p['fit_frames'] != [100] or p['selection_frames'] != [175]:
        raise ValueError('scale frame roles changed')
    return p


def undistortion(entry):
    """Destination matches the unmodified ViPE wrapper's exact K construction."""
    import cv2
    K = np.array(entry['K'], dtype=np.float64)
    f, cx, cy, k = entry['parameters_colmap']
    if entry['camera_model'] != 'SIMPLE_RADIAL' or not np.allclose(K, [[f,0,cx-.5],[0,f,cy-.5],[0,0,1]]):
        raise ValueError('inconsistent distortion or pixel conventions')
    target = np.array([[f,0,480.],[0,f,270.],[0,0,1.]])
    maps = cv2.initUndistortRectifyMap(K, np.array([k,0.,0.,0.]), None, target, (960,540), cv2.CV_32FC1)
    return target, maps


def prepare(a):
    import cv2
    import pycolmap as cm
    p = protocol(a.protocol)
    audit = read(a.audit)
    if audit['status'] != 'passed':
        raise ValueError('provenance gate has not passed')
    verify_hashes(audit['sha256'])
    verify_hashes({str(CALIBRATION): CALIBRATION_SHA})
    a.output.mkdir(parents=True, exist_ok=False)
    cfg = dict(p, protocol_file_sha256=sha256(a.protocol), role=a.role,
               audit_sha256=sha256(a.audit), adapter_sha256=sha256(__file__))
    write(a.output/'protocol.json', cfg)
    frames = p[a.role+'_frames']
    source = WORKSPACE/('inputs' if a.role == 'fit' else 'selection-inputs')
    inputs = read(source/'result.json')
    if inputs['input_audit_sha256'] != sha256('.local/calibration/basketball-v1/input-audit.json'):
        raise ValueError('source image audit mismatch')
    observations = {(e['camera_id'],e['source_frame_id']):e for e in inputs['observations']}
    model = cm.Reconstruction(p['map'])
    cameras = {e['camera_id']:e for e in read(CALIBRATION)['cameras']}
    # Only points originally observed by this physical training camera are eligible.
    visible = {c:[] for c in TRAINING}
    for pid, point in model.points3D.items():
        image_ids = {e.image_id for e in point.track.elements}
        ids = {int(Path(model.images[i].name).stem.removeprefix('camera')) for i in image_ids}
        if not ids <= set(TRAINING):
            raise ValueError('held-out map observation')
        if len(ids) < p['minimum_map_track_cameras']:
            continue
        centers = np.array([cameras[c]['center'] for c in sorted(ids)])
        rays = point.xyz-centers
        rays /= np.linalg.norm(rays, axis=1)[:,None]
        angle = np.degrees(np.arccos(np.clip(rays@rays.T,-1,1))).max()
        if angle < p['minimum_map_parallax_degrees']:
            continue
        for c in ids:
            visible[c].append((pid, point.xyz.copy()))
    entries = []
    for c in TRAINING:
        entry = cameras[c]
        K, maps = undistortion(entry)
        for frame in frames:
            item = observations[c,frame]
            image_path = source/(item['stem']+'.png')
            mask_path = source/(item['stem']+'-static.png')
            verify_hashes({str(image_path):item['image_sha256'], str(mask_path):item['mask_sha256']})
            image = cv2.imread(str(image_path))
            mask = cv2.imread(str(mask_path),0)
            undistorted = cv2.remap(image,*maps,cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT)
            clear = cv2.distanceTransform((mask>0).astype(np.uint8),cv2.DIST_L2,cv2.DIST_MASK_PRECISE)
            clear = cv2.remap(clear,*maps,cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT)
            valid = cv2.remap(np.ones(mask.shape,np.uint8),*maps,cv2.INTER_NEAREST, borderMode=cv2.BORDER_CONSTANT)
            ids = np.array([i for i,x in visible[c]],dtype=np.int64)
            xyz = np.array([x for i,x in visible[c]])
            camera_xyz = xyz@np.array(entry['R']).T+entry['t']
            projected = camera_xyz@K.T
            uv = projected[:,:2]/projected[:,2:]
            rounded = np.rint(uv).astype(int)
            good = (camera_xyz[:,2]>0)&(rounded[:,0]>=1)&(rounded[:,0]<959)&(rounded[:,1]>=1)&(rounded[:,1]<539)
            indices = np.flatnonzero(good)
            indices = [i for i in indices if valid[rounded[i,1],rounded[i,0]] and clear[rounded[i,1],rounded[i,0]]>=p['minimum_static_mask_clearance_pixels']]
            # Stable spatial deduplication, independent of predicted depth.
            keep=[];occupied=set()
            for i in sorted(indices,key=lambda i:int(ids[i])):
                cell=tuple(np.floor(uv[i]/p['spatial_deduplication_pixels']).astype(int))
                if cell not in occupied:
                    keep.append(i);occupied.add(cell)
            stem=f'camera{c}-frame{frame}'
            path=a.output/(stem+'.png')
            if not cv2.imwrite(str(path),undistorted):
                raise ValueError('image write failed')
            samples=a.output/(stem+'-samples.npz')
            np.savez_compressed(samples, point_ids=ids[keep], xyz=xyz[keep], uv=uv[keep],
                                camera_z=camera_xyz[keep,2], K=K, valid=valid)
            entries.append(dict(camera_id=c,source_frame_id=frame,stem=stem,K=K.tolist(),
                image_sha256=sha256(path),samples_sha256=sha256(samples),
                source_image_sha256=item['image_sha256'],source_mask_sha256=item['mask_sha256'],
                independent_points=len(keep), transform='SIMPLE_RADIAL OpenCV undistortion; no crop; target principal point (480,270)'))
    write(a.output/'inputs.json',dict(status='prepared',role=a.role,entries=entries,
        protocol_sha256=sha256(a.output/'protocol.json'),calibration_sha256=CALIBRATION_SHA))
    print('prepared',len(entries),'training depth inputs')


def infer(a):
    p=read(a.inputs/'protocol.json');data=read(a.inputs/'inputs.json')
    if p['adapter_sha256'] != sha256(__file__):
        raise ValueError('scale adapter changed after preparation')
    verify_hashes({str(a.inputs/'protocol.json'):data['protocol_sha256']})
    if {(e['camera_id'],e['source_frame_id']) for e in data['entries']} != {(c,f) for c in TRAINING for f in p[p['role']+'_frames']}:
        raise ValueError('depth inference leakage/missing frames')
    git=lambda *args:subprocess.check_output(['git','-C',str(a.vipe),*args],text=True).strip()
    if git('rev-parse','HEAD') != PIN or git('status','--porcelain') or git('branch','--show-current')!='tridi':
        raise ValueError('ViPE pin changed')
    # Reuse only the exact already audited sources, extensions and weights.
    prior=read('.local/calibration/basketball-v1/no-camera5-priors/result.json')
    verify_hashes({str(a.vipe/k):v for k,v in prior['source_sha256'].items()})
    verify_hashes(prior['weight_sha256'])
    os.environ['HF_HUB_OFFLINE']='1'
    os.environ['TRANSFORMERS_OFFLINE']='1'
    sys.path.insert(0,str(a.vipe.resolve()))
    import cv2
    import torch
    import torchvision
    from vipe.utils.device import configure_device
    from vipe.priors.depth.unidepth import UniDepth2Model
    from vipe.priors.depth.base import DepthEstimationInput
    import vipe_ext
    if sys.version_info[:2]!=(3,14) or torch.__version__!='2.13.0+cu130' or torchvision.__version__!='0.28.0+cu130':
        raise ValueError('runtime differs from required stack')
    device=configure_device('cuda')
    if not torch.cuda.is_available():
        raise RuntimeError('CUDA required; CPU fallback prohibited')
    torch.cuda.init()
    a.output.mkdir(parents=True,exist_ok=False)
    start=time.monotonic()
    record=dict(status='running',entries=[],inputs_sha256=sha256(a.inputs/'inputs.json'),
        protocol_sha256=sha256(a.inputs/'protocol.json'),adapter_sha256=sha256(__file__),
        prior_provenance_sha256=sha256('.local/calibration/basketball-v1/no-camera5-priors/result.json'),
        source_sha256=prior['source_sha256'],weight_sha256=prior['weight_sha256'],
        runtime=dict(python=sys.version,torch=torch.__version__,torchvision=torchvision.__version__,
                     cuda=torch.version.cuda,gpu=torch.cuda.get_device_name(),extension=vipe_ext.__file__))
    torch.manual_seed(0);np.random.seed(0);torch.cuda.reset_peak_memory_stats()
    try:
        model=UniDepth2Model()
        for e in data['entries']:
            stem=e['stem'];image=a.inputs/(stem+'.png')
            verify_hashes({str(image):e['image_sha256'],str(a.inputs/(stem+'-samples.npz')):e['samples_sha256']})
            rgb=cv2.cvtColor(cv2.imread(str(image)),cv2.COLOR_BGR2RGB)
            rgb=torch.from_numpy(rgb).to(device).float()/255
            K=e['K']
            with torch.inference_mode():
                output=model.estimate(DepthEstimationInput(rgb=rgb,
                    intrinsics=torch.tensor([K[0][0],K[1][1],K[0][2],K[1][2]],device=device)))
            path=a.output/(stem+'-depth.npz')
            np.savez_compressed(path,depth=output.metric_depth.cpu().numpy(),confidence=output.confidence.cpu().numpy())
            record['entries'].append(dict(camera_id=e['camera_id'],source_frame_id=e['source_frame_id'],
                                          stem=stem,sha256=sha256(path)))
            print('depth',stem,flush=True)
        record['status']='complete'
    except BaseException as error:
        record['status']='failed';record['error']=f'{type(error).__name__}: {error}'
        raise
    finally:
        torch.cuda.synchronize()
        record.update(wall_seconds=time.monotonic()-start,peak_allocated_bytes=torch.cuda.max_memory_allocated(),
                      peak_reserved_bytes=torch.cuda.max_memory_reserved())
        write(a.output/'result.json',record)


def scale_statistics(samples, p, frozen_scale=None):
    """Equal-camera robust estimate and camera-cluster bootstrap; no affine shift."""
    if len(samples)!=len(TRAINING) or {s['camera_id'] for s in samples}!=set(TRAINING):
        raise ValueError('scale needs every training camera exactly once')
    rows=[];blockers=[]
    for s in samples:
        ratios=np.asarray(s['ratios'],float)
        if not len(ratios) or not np.isfinite(ratios).all() or (ratios<=0).any():
            raise ValueError('invalid scale ratios')
        logs=np.log(ratios);median=float(np.median(logs));mad=float(np.median(np.abs(logs-median)))
        row=dict(camera_id=s['camera_id'],points=len(ratios),occupied_grid_cells=s['cells'],
                 scale=float(np.exp(median)),log_mad=mad,positive_depth_fraction=s['positive_depth_fraction'])
        rows.append(row)
        if len(ratios)<p['minimum_points_per_camera'] or s['cells']<p['minimum_grid_cells_per_camera']:
            blockers.append(f"camera {s['camera_id']}: insufficient scale support")
        if mad>p['maximum_within_camera_log_mad'] or s['positive_depth_fraction']<p['minimum_positive_depth_fraction']:
            blockers.append(f"camera {s['camera_id']}: inconsistent/invalid depth")
    medians=np.log([r['scale'] for r in rows]);estimate=float(np.exp(np.median(medians)))
    scale=estimate if frozen_scale is None else float(frozen_scale)
    if not np.isfinite(scale) or scale<=0:
        raise ValueError('invalid frozen scale')
    for r in rows:
        r['relative_deviation']=abs(r['scale']/scale-1)
        if r['relative_deviation']>p['maximum_camera_scale_relative_deviation']:
            blockers.append(f"camera {r['camera_id']}: scale disagreement {r['relative_deviation']:.6f}")
    rng=np.random.default_rng(p['bootstrap_seed'])
    boot=np.exp(np.median(rng.choice(medians,(p['bootstrap_camera_resamples'],len(medians)),replace=True),axis=1))
    interval=np.quantile(boot,[.025,.975]);halfwidth=float((interval[1]-interval[0])/(2*estimate))
    if halfwidth>p['maximum_bootstrap_95_relative_halfwidth']:
        blockers.append('global scale uncertainty exceeds frozen limit')
    if frozen_scale is not None and abs(estimate/scale-1)>p['maximum_selection_scale_relative_disagreement']:
        blockers.append('reserved-frame scale disagreement exceeds frozen limit')
    return dict(status='blocked' if blockers else 'passed',blockers=blockers,scale=scale,
        diagnostic_window_scale=estimate,bootstrap_95_interval=interval.tolist(),relative_halfwidth=halfwidth,
        cameras=rows,uncertainty_limitation=p['uncertainty_limitation'])


def evaluate(a):
    import cv2
    p=read(a.inputs/'protocol.json');data=read(a.inputs/'inputs.json');depths=read(a.depths/'result.json')
    verify_hashes({str(a.inputs/'inputs.json'):depths['inputs_sha256'],
                   str(a.inputs/'protocol.json'):depths['protocol_sha256']})
    if depths['status']!='complete' or depths['adapter_sha256']!=sha256(__file__):
        raise ValueError('depth inference incomplete or adapter changed')
    lookup={(e['camera_id'],e['source_frame_id']):e for e in depths['entries']}
    samples=[]
    for e in data['entries']:
        c=e['camera_id'];f=e['source_frame_id'];stem=e['stem']
        path=a.inputs/(stem+'-samples.npz');dp=a.depths/(stem+'-depth.npz')
        verify_hashes({str(path):e['samples_sha256'],str(dp):lookup[c,f]['sha256']})
        geom=np.load(path);depth=np.load(dp)['depth'];uv=geom['uv'];valid=geom['valid']>0
        values=cv2.remap(depth,uv[:,0].astype(np.float32).reshape(-1,1),uv[:,1].astype(np.float32).reshape(-1,1),cv2.INTER_LINEAR).ravel()
        good=np.isfinite(values)&(values>0)&(geom['camera_z']>0)
        cells=np.floor(uv[good]/[240,135]).astype(int)
        samples.append(dict(camera_id=c,ratios=values[good]/geom['camera_z'][good],
            cells=len(set(map(tuple,cells))),positive_depth_fraction=float(np.mean(np.isfinite(depth[valid])&(depth[valid]>0)))))
    frozen=None
    if p['role']=='selection':
        if a.frozen_fit is None:
            raise ValueError('selection requires frozen fitting scale')
        fit=read(a.frozen_fit)
        if fit['status']!='passed' or fit['role']!='fit' or fit['protocol_file_sha256']!=p['protocol_file_sha256']:
            raise ValueError('invalid frozen fitting scale')
        frozen=fit['scale']
    result=scale_statistics(samples,p,frozen)
    result.update(role=p['role'],protocol_file_sha256=p['protocol_file_sha256'],
        inputs_sha256=sha256(a.inputs/'inputs.json'),depths_sha256=sha256(a.depths/'result.json'),
        calibration_sha256=CALIBRATION_SHA,adapter_sha256=sha256(__file__),
        frozen_fit_sha256=sha256(a.frozen_fit) if a.frozen_fit else None)
    write(a.output,result)
    print(json.dumps({k:v for k,v in result.items() if k!='cameras'},indent=2))
    return result['status']!='passed'


def main():
    parser=argparse.ArgumentParser(description=__doc__);sub=parser.add_subparsers(dest='command',required=True)
    p=sub.add_parser('prepare');p.add_argument('--protocol',type=Path,required=True);p.add_argument('--audit',type=Path,required=True)
    p.add_argument('--role',choices=['fit','selection'],required=True);p.add_argument('--output',type=Path,required=True)
    p=sub.add_parser('infer');p.add_argument('--inputs',type=Path,required=True);p.add_argument('--vipe',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p=sub.add_parser('evaluate');p.add_argument('--inputs',type=Path,required=True);p.add_argument('--depths',type=Path,required=True)
    p.add_argument('--frozen-fit',type=Path);p.add_argument('--output',type=Path,required=True)
    a=parser.parse_args();return dict(prepare=prepare,infer=infer,evaluate=evaluate)[a.command](a)


if __name__=='__main__':
    raise SystemExit(main())

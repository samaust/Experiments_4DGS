"""One bounded pinned-RoMa pass on static, verified-overlap training pairs."""
import argparse
import json
from pathlib import Path
import time
from basketball_audit import sha256
from basketball_protocol import TRAINING, PROTOCOL


def select_pairs(edges, maximum=64):
    if maximum < len(TRAINING)-1:
        raise ValueError('pair budget cannot span the retained cameras')
    edges=sorted(edges,key=lambda e:(-e['inliers'],e['cameras']))
    if any(c not in TRAINING for e in edges for c in e['cameras']):
        raise ValueError('dense overlap includes excluded or held-out camera')
    parent={c:c for c in TRAINING}
    def find(c):
        while parent[c]!=c: c=parent[c]
        return c
    tree=set()
    for e in edges:
        a,b=e['cameras'];ra,rb=find(a),find(b)
        if ra!=rb: parent[ra]=rb;tree.add(tuple(sorted([a,b])))
    if len(tree)!=len(TRAINING)-1: raise ValueError('verified-overlap graph is disconnected')
    selected=set(tree)
    for c in TRAINING:
        local=[e for e in edges if c in e['cameras']][:3]
        selected.update(tuple(sorted(e['cameras'])) for e in local)
    ranked=[tuple(sorted(e['cameras'])) for e in edges if tuple(sorted(e['cameras'])) in selected-tree]
    selected=tree|set(ranked[:maximum-len(tree)])
    return sorted(selected)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--priors',type=Path,required=True)
    p.add_argument('--sift-result',type=Path,required=True)
    p.add_argument('--roma',type=Path,required=True)
    p.add_argument('--weights',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args()
    import numpy as np
    import cv2
    import torch
    from PIL import Image
    from edgs_source import load_roma,ROMA_PIN,ROMA_WEIGHTS
    a.output.mkdir(exist_ok=False)
    sift=json.loads(a.sift_result.read_text())
    pairs=select_pairs(sift['verified_edges'])
    config=dict(schema='basketball-dense-pass/v1',protocol=PROTOCOL,pairs=pairs,frames=[50,149],
                max_pairs=64,max_inferences=128,min_confidence=.95,max_matches_per_pair=1500,
                source_coverage_cell_pixels=16,mask_clearance_pixels=8,seed=0,
                roma_pin=ROMA_PIN,weights=ROMA_WEIGHTS,priors_result_sha256=sha256(a.priors/'result.json'),
                sift_result_sha256=sha256(a.sift_result),adapter_sha256=sha256(__file__))
    (a.output/'config.json').write_text(json.dumps(config,indent=2)+'\n')
    artifacts=json.loads((a.priors/'artifacts.json').read_text())
    report=dict(schema='basketball-dense-pass-result/v1',status='blocked',blockers=[],pairs=[],
                config_sha256=sha256(a.output/'config.json'))
    started=time.monotonic()
    try:
        torch.manual_seed(0)
        model=load_roma(a.roma,a.weights)
        torch.cuda.reset_peak_memory_stats()
        for frame in config['frames']:
            images={};masks={}
            for camera in TRAINING:
                stem=f'camera{camera}-frame{frame}'
                for name in [stem+'.png',stem+'-static.png']:
                    if sha256(a.priors/name)!=artifacts[name]: raise ValueError(f'changed prior artifact: {name}')
                images[camera]=Image.open(a.priors/(stem+'.png')).convert('RGB')
                mask=cv2.imread(str(a.priors/(stem+'-static.png')),cv2.IMREAD_GRAYSCALE)
                masks[camera]=cv2.distanceTransform((mask>0).astype(np.uint8),cv2.DIST_L2,5)>=8
            for left,right in pairs:
                with torch.inference_mode():
                    warp,confidence=model.match(images[left],images[right],device='cuda')
                    uv_a,uv_b=model.to_pixel_coordinates(warp.reshape(-1,4),540,960,540,960)
                uv_a,uv_b=uv_a.cpu().numpy(),uv_b.cpu().numpy()
                scores=confidence.flatten().cpu().numpy()
                good=np.isfinite(uv_a).all(1)&np.isfinite(uv_b).all(1)&np.isfinite(scores)&(scores>=.95)
                good&=(uv_a[:,0]>=0)&(uv_a[:,0]<960)&(uv_a[:,1]>=0)&(uv_a[:,1]<540)
                good&=(uv_b[:,0]>=0)&(uv_b[:,0]<960)&(uv_b[:,1]>=0)&(uv_b[:,1]<540)
                indices=np.flatnonzero(good)
                xy_a=np.floor(uv_a[indices]).astype(int);xy_b=np.floor(uv_b[indices]).astype(int)
                indices=indices[masks[left][xy_a[:,1],xy_a[:,0]]&masks[right][xy_b[:,1],xy_b[:,0]]]
                indices=indices[np.argsort(-scores[indices],kind='stable')]
                chosen=[];occupied=set()
                for index in indices:
                    cell=tuple(np.floor(uv_a[index]/16).astype(int))
                    if cell in occupied: continue
                    occupied.add(cell);chosen.append(index)
                    if len(chosen)==1500: break
                name=f'frame{frame}-camera{left}-camera{right}.npz'
                np.savez_compressed(a.output/name,uv_a=uv_a[chosen],uv_b=uv_b[chosen],confidence=scores[chosen])
                report['pairs'].append(dict(frame=frame,cameras=[left,right],matches=len(chosen),path=name,sha256=sha256(a.output/name)))
                print(frame,left,right,len(chosen),flush=True)
        report['peak_allocated_bytes']=torch.cuda.max_memory_allocated()
        report['peak_reserved_bytes']=torch.cuda.max_memory_reserved()
        report['status']='matches-generated'
    except BaseException as error:
        report['blockers'].append(f'{type(error).__name__}: {error}')
        raise
    finally:
        report['wall_seconds']=time.monotonic()-started
        (a.output/'result.json').write_text(json.dumps(report,indent=2)+'\n')


if __name__=='__main__': main()

"""One frozen dense inference pass reused at the two authorized confidence levels."""
import argparse
import json
from pathlib import Path
import sqlite3
import time
import numpy as np
from basketball_audit import sha256
from basketball_protocol import TRAINING, PROTOCOL
from basketball_dense_matches import select_pairs


def bilateral_sample(uv_a, uv_b, confidence, threshold):
    selected = []; left = set(); right = set()
    for index in np.argsort(-confidence, kind='stable'):
        if confidence[index] < threshold:
            continue
        a = tuple(np.floor(uv_a[index] / 16).astype(int))
        b = tuple(np.floor(uv_b[index] / 16).astype(int))
        if a in left or b in right:
            continue
        selected.append(int(index)); left.add(a); right.add(b)
        if len(selected) == 1500:
            break
    return np.array(selected, dtype=np.int64)


def infer(priors, early, late, output, roma, weights):
    import cv2
    import torch
    from PIL import Image
    from edgs_source import load_roma, ROMA_PIN, ROMA_WEIGHTS
    from basketball_focus import sharpness_maps
    reports = [json.loads((p / 'result.json').read_text()) for p in (early, late)]
    edges = [{tuple(e['cameras']): e['inliers'] for e in r['verified_edges']} for r in reports]
    common = [dict(cameras=list(pair), inliers=min(edges[0][pair], edges[1][pair])) for pair in sorted(edges[0].keys() & edges[1].keys())]
    pairs = select_pairs(common)
    output.mkdir(exist_ok=False)
    config = dict(schema='basketball-dense-recovery/v1', protocol=PROTOCOL, pairs=pairs, frames=[50,149],
        max_inferences=128, confidence_variants=[.95,.90], mask_clearance=8, bilateral_grid=16,
        max_matches_per_pair=1500, seed=0, roma_pin=ROMA_PIN, weights=ROMA_WEIGHTS,
        source_results=[sha256(p / 'result.json') for p in (early,late)],
        priors_sha256=sha256(priors / 'result.json'), adapter_sha256=sha256(__file__))
    (output / 'config.json').write_text(json.dumps(config,indent=2)+'\n')
    result = dict(schema='basketball-dense-recovery-result/v1',protocol=PROTOCOL,status='blocked',blockers=[],pairs=[],config_sha256=sha256(output/'config.json'))
    started = time.monotonic()
    try:
        torch.manual_seed(0)
        model = load_roma(roma, weights)
        artifacts = json.loads((priors/'artifacts.json').read_text())
        for frame, report in zip([50,149],reports):
            images={};valid={}
            for c in TRAINING:
                stem=f'camera{c}-frame{frame}'
                for name in [stem+'.png',stem+'-static.png']:
                    if sha256(priors/name)!=artifacts[name]:raise ValueError('changed dense input')
                images[c]=Image.open(priors/(stem+'.png')).convert('RGB')
                gray=cv2.imread(str(priors/(stem+'.png')),cv2.IMREAD_GRAYSCALE)
                mask=cv2.imread(str(priors/(stem+'-static.png')),cv2.IMREAD_GRAYSCALE)
                score,variance=sharpness_maps(gray)
                valid[c]=(cv2.distanceTransform((mask>0).astype(np.uint8),cv2.DIST_L2,5)>=8)&(variance>=1e-4)&(score>=report['features'][str(c)]['sharpness_threshold'])
                valid[c][:11]=False;valid[c][-11:]=False;valid[c][:,:11]=False;valid[c][:,-11:]=False
            for a,b in pairs:
                with torch.inference_mode():
                    warp,confidence=model.match(images[a],images[b],device='cuda')
                    uv_a,uv_b=model.to_pixel_coordinates(warp.reshape(-1,4),540,960,540,960)
                uv_a,uv_b,scores=uv_a.cpu().numpy(),uv_b.cpu().numpy(),confidence.flatten().cpu().numpy()
                good=np.isfinite(uv_a).all(1)&np.isfinite(uv_b).all(1)&np.isfinite(scores)&(scores>=.9)
                for uv in [uv_a,uv_b]:good&=(uv[:,0]>=0)&(uv[:,0]<960)&(uv[:,1]>=0)&(uv[:,1]<540)
                idx=np.flatnonzero(good);xya=np.floor(uv_a[idx]).astype(int);xyb=np.floor(uv_b[idx]).astype(int)
                idx=idx[valid[a][xya[:,1],xya[:,0]]&valid[b][xyb[:,1],xyb[:,0]]]
                name=f'frame{frame}-camera{a}-camera{b}.npz'
                np.savez_compressed(output/name,uv_a=uv_a[idx],uv_b=uv_b[idx],confidence=scores[idx])
                counts={str(t):len(bilateral_sample(uv_a[idx],uv_b[idx],scores[idx],t)) for t in [.95,.9]}
                result['pairs'].append(dict(frame=frame,cameras=[a,b],path=name,sha256=sha256(output/name),eligible=len(idx),selected=counts))
                print(frame,a,b,counts,flush=True)
        result['status']='matches-generated'
    except BaseException as error:
        result['blockers'].append(f'{type(error).__name__}: {error}');raise
    finally:
        result['wall_seconds']=time.monotonic()-started
        (output/'result.json').write_text(json.dumps(result,indent=2)+'\n')


def augment(source, dense, output, frame, threshold):
    import pycolmap as colmap
    from scipy.spatial import cKDTree
    report=json.loads((dense/'result.json').read_text())
    if report['status']!='matches-generated' or report['blockers']:raise ValueError('requires complete dense pass')
    output.mkdir(exist_ok=False)
    dbpath=output/'merged.db'
    with sqlite3.connect(f'file:{(source/"merged.db").resolve()}?mode=ro',uri=True) as old,sqlite3.connect(dbpath) as new:old.backup(new)
    (output/'merged-images').symlink_to((source/'merged-images').resolve(),target_is_directory=True)
    jobs=[e for e in report['pairs'] if e['frame']==frame]
    counts=[]
    with colmap.Database.open(dbpath) as db:
        if sorted(i.camera_id-1 for i in db.read_all_images())!=list(TRAINING):raise ValueError('invalid source membership')
        keys={c:db.read_keypoints(c+1) for c in TRAINING}
        for job in jobs:
            path=dense/job['path']
            if sha256(path)!=job['sha256']:raise ValueError('changed dense correspondences')
            data=np.load(path);chosen=bilateral_sample(data['uv_a'],data['uv_b'],data['confidence'],threshold)
            a,b=job['cameras'];indices=[]
            for c,uv in [(a,data['uv_a'][chosen]),(b,data['uv_b'][chosen])]:
                distances,nearest=cKDTree(keys[c][:,:2]).query(uv)
                added=[];mapping={};ids=[]
                for i,point in enumerate(uv):
                    if distances[i]<=1.:ids.append(int(nearest[i]));continue
                    cell=tuple(np.rint(point*2).astype(int))
                    if cell not in mapping:
                        mapping[cell]=len(keys[c])+len(added)
                        row=np.zeros(keys[c].shape[1],np.float32);row[:2]=point;row[2]=1.
                        added.append(row)
                    ids.append(mapping[cell])
                if added:keys[c]=np.concatenate([keys[c],np.array(added)])
                indices.append(ids)
            extra=np.asarray(indices,np.uint32).T.reshape(-1,2)
            old=db.read_matches(a+1,b+1) if db.exists_matches(a+1,b+1) else np.empty((0,2),np.uint32)
            if db.exists_matches(a+1,b+1):db.delete_matches(a+1,b+1)
            if db.exists_two_view_geometry(a+1,b+1):db.delete_two_view_geometry(a+1,b+1)
            db.write_matches(a+1,b+1,np.unique(np.concatenate([old,extra]),axis=0))
            counts.append(dict(cameras=[a,b],matches=len(extra)))
        for c,k in keys.items():db.update_keypoints(c+1,k)
    with sqlite3.connect(dbpath) as db:db.execute('DELETE FROM descriptors')
    pairpath=output/'pairs.txt';pairpath.write_text(''.join(f'camera{e["cameras"][0]}.png camera{e["cameras"][1]}.png\n' for e in jobs))
    options=colmap.TwoViewGeometryOptions();options.ransac.random_seed=0
    colmap.verify_matches(dbpath,pairpath,options=options)
    result=dict(schema='basketball-dense-augmentation/v1',protocol=PROTOCOL,status='features-generated',source=str(source),
                source_sha256=sha256(source/'merged.db'),dense_sha256=sha256(dense/'result.json'),frame=frame,threshold=threshold,pairs=counts,adapter_sha256=sha256(__file__))
    (output/'result.json').write_text(json.dumps(result,indent=2)+'\n')


def main():
    p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='mode',required=True)
    inference=sub.add_parser('infer')
    for name in ['priors','early','late','output','roma','weights']:inference.add_argument('--'+name,type=Path,required=True)
    augmentation=sub.add_parser('augment')
    for name in ['source','dense','output']:augmentation.add_argument('--'+name,type=Path,required=True)
    augmentation.add_argument('--frame',type=int,choices=[50,149],required=True)
    augmentation.add_argument('--threshold',type=float,choices=[.95,.9],required=True)
    a=vars(p.parse_args());mode=a.pop('mode')
    (infer if mode=='infer' else augment)(**a)


if __name__=='__main__':main()

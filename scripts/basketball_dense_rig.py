"""Augment a fitting-window SIFT database with the single bounded RoMa pass."""
import argparse
import json
from pathlib import Path
import shutil
import sqlite3
import time
import numpy as np
from scipy.spatial import cKDTree
from basketball_audit import sha256
from basketball_protocol import TRAINING, PROTOCOL
from basketball_geometry import connected_components


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--sift',required=True,type=Path)
    p.add_argument('--dense',required=True,type=Path)
    p.add_argument('--frame',required=True,type=int,choices=[50,149])
    p.add_argument('--output',required=True,type=Path)
    a=p.parse_args()
    import pycolmap as colmap
    if colmap.__version__!='4.2.0': raise ValueError('requires pinned PyCOLMAP')
    dense=json.loads((a.dense/'result.json').read_text())
    if dense['status']!='matches-generated' or dense['blockers']: raise ValueError('dense pass incomplete')
    jobs=[e for e in dense['pairs'] if e['frame']==a.frame]
    if len(jobs)>64 or any(c not in TRAINING for e in jobs for c in e['cameras']): raise ValueError('invalid dense membership')
    a.output.mkdir(exist_ok=False)
    dbpath=a.output/'merged.db'
    with sqlite3.connect(a.sift/'merged.db') as source,sqlite3.connect(dbpath) as target: source.backup(target)
    images=a.output/'merged-images';images.symlink_to((a.sift/'merged-images').resolve(),target_is_directory=True)
    config=dict(schema='basketball-dense-rig/v1',protocol=PROTOCOL,frame=a.frame,model='PINHOLE',
                source_database_sha256=sha256(a.sift/'merged.db'),dense_result_sha256=sha256(a.dense/'result.json'),
                adapter_sha256=sha256(__file__),merge_radius_pixels=1.,seed=0)
    (a.output/'config.json').write_text(json.dumps(config,indent=2)+'\n')
    result=dict(schema='basketball-static-rig-result/v1',status='blocked',blockers=[],models=[],
                config_sha256=sha256(a.output/'config.json'),dense_pairs=[],protocol=PROTOCOL)
    started=time.monotonic()
    try:
        with colmap.Database.open(dbpath) as db:
            source_ids=sorted(image.camera_id-1 for image in db.read_all_images())
            if source_ids!=list(TRAINING):
                raise ValueError('source database contains missing, duplicate, held-out or excluded cameras')
            keypoints={c:db.read_keypoints(c+1) for c in TRAINING}
            # Geometric verification/mapper use coordinates and matches only.
            # Descriptor rows are removed below, so appended RoMa locations can
            # never be mistaken for valid SIFT descriptors by a later consumer.
            for job in jobs:
                path=a.dense/job['path']
                if sha256(path)!=job['sha256']: raise ValueError('changed dense match artifact')
                data=np.load(path);left,right=job['cameras'];pair_indices=[]
                for c,uv in [(left,data['uv_a']),(right,data['uv_b'])]:
                    existing=keypoints[c]
                    distances,nearest=cKDTree(existing[:,:2]).query(uv)
                    added=[];mapping={};indices=[]
                    for i,point in enumerate(uv):
                        if distances[i]<=1.:
                            indices.append(int(nearest[i]));continue
                        cell=tuple(np.rint(point*2).astype(int))
                        if cell not in mapping:
                            mapping[cell]=len(existing)+len(added)
                            row=np.zeros(existing.shape[1],dtype=np.float32);row[:2]=point
                            if len(row)>2: row[2]=1.
                            added.append(row)
                        indices.append(mapping[cell])
                    if added: keypoints[c]=np.concatenate([existing,np.array(added)])
                    pair_indices.append(indices)
                extra=np.array(pair_indices,dtype=np.uint32).T
                previous=db.read_matches(left+1,right+1) if db.exists_matches(left+1,right+1) else np.empty((0,2),dtype=np.uint32)
                matches=np.unique(np.concatenate([previous,extra]),axis=0)
                if db.exists_matches(left+1,right+1):db.delete_matches(left+1,right+1)
                if db.exists_two_view_geometry(left+1,right+1):db.delete_two_view_geometry(left+1,right+1)
                db.write_matches(left+1,right+1,matches)
                result['dense_pairs'].append(dict(cameras=[left,right],added=len(extra),total=len(matches)))
            for c,keys in keypoints.items(): db.update_keypoints(c+1,keys)
        with sqlite3.connect(dbpath) as db: db.execute('DELETE FROM descriptors')
        pairpath=a.output/'pairs.txt'
        pairpath.write_text(''.join(f'camera{e["cameras"][0]}.png camera{e["cameras"][1]}.png\n' for e in jobs))
        geometry_options=colmap.TwoViewGeometryOptions()
        geometry_options.ransac.random_seed=0
        colmap.verify_matches(dbpath,pairpath,options=geometry_options)
        edges=[]
        with colmap.Database.open(dbpath) as db:
            for i,c in enumerate(TRAINING):
                for other in TRAINING[i+1:]:
                    if db.exists_two_view_geometry(c+1,other+1):
                        geom=db.read_two_view_geometry(c+1,other+1)
                        if len(geom.inlier_matches)>=30:edges.append([c,other])
        result['components']=connected_components(TRAINING,edges)
        options=colmap.IncrementalPipelineOptions(num_threads=8,random_seed=0,min_model_size=3,max_num_models=3,
                    ba_refine_focal_length=True,ba_refine_principal_point=False,ba_refine_extra_params=False,
                    max_runtime_seconds=600,extract_colors=False)
        models=colmap.incremental_mapping(dbpath,images,a.output/'sparse',options=options)
        for index,model in models.items():
            ba=colmap.BundleAdjustmentOptions(refine_focal_length=True,refine_principal_point=True,refine_extra_params=False)
            ba.ceres.loss_function_type=colmap.LossFunctionType.SOFT_L1
            ba.ceres.solver_options.num_threads=8
            ba.ceres.solver_options.max_solver_time_in_seconds=120
            colmap.bundle_adjustment(model,options=ba)
            model.write(a.output/'sparse'/str(index))
            cameras=sorted(image.camera_id-1 for image in model.images.values() if image.has_pose)
            result['models'].append(dict(model_id=index,cameras=cameras,points=model.num_points3D(),mean_reprojection_error=model.compute_mean_reprojection_error()))
        complete=[m for m in result['models'] if m['cameras']==list(TRAINING)]
        if len(complete)!=1 or len(result['components'])!=1: result['blockers'].append('dense fallback did not recover one complete connected training candidate')
        else:result.update(status='candidate-rig',model_id=complete[0]['model_id'])
    except BaseException as error:
        result['blockers'].append(f'{type(error).__name__}: {error}');raise
    finally:
        result['wall_seconds']=time.monotonic()-started
        (a.output/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    return bool(result['blockers'])


if __name__=='__main__':raise SystemExit(main())

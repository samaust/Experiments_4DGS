"""Audit three-seed full-rig repeatability with training-only alignments."""
import argparse
import json
from pathlib import Path
import numpy as np
from basketball_alternatives_compare import compare, frozen_errors, load_export
from basketball_alternatives_protocol import CAMERAS, HELD_OUT, PROTOCOL
from basketball_alternatives_finalist_report import locate
from basketball_alternatives_colmap import dump
from basketball_audit import sha256


def full_compare(training, held_out):
    result=compare(*training)
    a=result['alignment']
    transform=(a['scale'],np.array(a['rotation']),np.array(a['translation']))
    angles,centers=frozen_errors(*held_out,transform,a['diameter'])
    result['per_camera'].extend(dict(camera_id=c,rotation_degrees=float(r),center_fraction=float(t))
                               for c,r,t in zip(HELD_OUT,angles,centers))
    result['per_camera'].sort(key=lambda r:r['camera_id'])
    result['max_rotation_degrees']=max(r['rotation_degrees'] for r in result['per_camera'])
    result['max_center_fraction']=max(r['center_fraction'] for r in result['per_camera'])
    result['passed']=result['max_rotation_degrees']<=.5 and result['max_center_fraction']<=.01
    result['held_out_alignment_refitted']=False
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--workspace',type=Path,required=True)
    p.add_argument('--method',required=True)
    p.add_argument('--policy',choices=['fixed','focal','radial'],required=True)
    p.add_argument('--sharp',action='store_true')
    p.add_argument('--held-out-prefix',default='held-out')
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();training={};held={};hashes={};paired=[]
    for seed in (0,1,2):
        for side in ('early','late'):
            folder=locate(a.workspace,a.method,a.policy,a.sharp,side,seed)
            tp=folder/'calibration-0.json'
            hp=a.workspace/f'{a.held_out_prefix}-{side}-seed{seed}-verified'/'calibration.json'
            hr=json.loads(hp.with_name('result.json').read_text())
            if hr['status']!='localized' or not all(r['support_passed'] for r in hr['cameras']):
                raise ValueError('held-out support failed')
            training[seed,side]=load_export(tp);held[seed,side]=load_export(hp,expected=HELD_OUT)
            hashes.update({str(tp):sha256(tp),str(hp):sha256(hp)})
        paired.append(dict(seed=seed,**full_compare([training[seed,s] for s in ('early','late')],
                                                  [held[seed,s] for s in ('early','late')])))
    cross=[dict(seed=seed,side=side,**full_compare([training[0,side],training[seed,side]],
                                                [held[0,side],held[seed,side]]))
           for seed in (1,2) for side in ('early','late')]
    a.output.mkdir(parents=True,exist_ok=False)
    report=dict(protocol=PROTOCOL,method=a.method,policy=a.policy,sharp=a.sharp,
                paired=paired,cross_seed=cross,source_sha256=hashes,
                passed=all(r['passed'] for r in paired+cross),
                max_rotation_degrees=max(r['max_rotation_degrees'] for r in paired),
                max_center_fraction=max(r['max_center_fraction'] for r in paired),
                cross_seed_max_rotation_degrees=max(r['max_rotation_degrees'] for r in cross),
                cross_seed_max_center_fraction=max(r['max_center_fraction'] for r in cross))
    dump(a.output/'result.json',report)
    base=locate(a.workspace,a.method,a.policy,a.sharp,'early',0)
    value=json.loads((base/'calibration-0.json').read_text())
    hp=a.workspace/f'{a.held_out_prefix}-early-seed0-verified'/'calibration.json'
    value['cameras']+=json.loads(hp.read_text())['cameras']
    value['cameras'].sort(key=lambda r:r['camera_id'])
    value.update(estimated=True,metric_scale_verified=False,synchronization_verified=False,
                 selection_used_for_fitting=False,source_sha256=hashes)
    dump(a.output/'calibration.json',value)
    load_export(a.output/'calibration.json',expected=CAMERAS)
    print(json.dumps({k:v for k,v in report.items() if k not in ('paired','cross_seed','source_sha256')},indent=2))


if __name__=='__main__':main()

"""Select at most two nonplanar, distributed initial pairs eligible in both windows."""
import argparse
from contextlib import contextmanager
import json
from pathlib import Path
import sqlite3
import tempfile
import numpy as np
from basketball_audit import sha256
from basketball_protocol import TRAINING, PROTOCOL


@contextmanager
def frozen_database(path):
    import pycolmap
    with tempfile.TemporaryDirectory() as folder:
        snapshot=Path(folder)/'read.db'
        with sqlite3.connect(f'file:{path.resolve()}?mode=ro',uri=True) as source, sqlite3.connect(snapshot) as target:source.backup(target)
        with pycolmap.Database.open(snapshot) as db:yield db


def eligible(record):
    return (record['inliers']>=100 and record['triangulation_degrees']>=16.
            and min(record['coverage_cells'])>=6 and record['homography_fraction']<.8)


def rank_common(early,late):
    a={tuple(e['cameras']):e for e in early if eligible(e)}
    b={tuple(e['cameras']):e for e in late if eligible(e)}
    return [list(pair) for pair in sorted(a.keys()&b.keys(),key=lambda p:(-min(a[p]['inliers'],b[p]['inliers']),p))[:2]]


def inspect_pairs(path):
    import pycolmap as p
    records=[]
    options=p.TwoViewGeometryOptions();options.compute_relative_pose=True;options.ransac.random_seed=0
    homography_options=p.RANSACOptions();homography_options.random_seed=0;homography_options.max_error=4.
    with frozen_database(path) as db:
        keys={c:db.read_keypoints(c+1)[:,:2].astype(float) for c in TRAINING}
        for i,a in enumerate(TRAINING):
            for b in TRAINING[i+1:]:
                if not db.exists_two_view_geometry(a+1,b+1):continue
                old=db.read_two_view_geometry(a+1,b+1)
                if len(old.inlier_matches)<100:continue
                geometry=p.estimate_calibrated_two_view_geometry(db.read_camera(a+1),keys[a],db.read_camera(b+1),keys[b],old.inlier_matches,options)
                pairs=geometry.inlier_matches
                if len(pairs)<100:continue
                left,right=keys[a][pairs[:,0]],keys[b][pairs[:,1]]
                H=p.estimate_homography_matrix(left,right,homography_options)
                cells=[len(set(map(tuple,np.floor(uv/[240,135]).astype(int)))) for uv in [left,right]]
                records.append(dict(cameras=[a,b],inliers=len(pairs),triangulation_degrees=float(np.rad2deg(geometry.tri_angle)),
                                    coverage_cells=cells,homography_fraction=float(H['num_inliers']/len(pairs)) if H else 0.))
    return records


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ['early','late','output']:parser.add_argument('--'+name,type=Path,required=True)
    args=parser.parse_args()
    early=inspect_pairs(args.early/'merged.db');late=inspect_pairs(args.late/'merged.db')
    result=dict(schema='basketball-initial-pairs/v1',protocol=PROTOCOL,early=early,late=late,pairs=rank_common(early,late),
                database_sha256=[sha256(p/'merged.db') for p in [args.early,args.late]],adapter_sha256=sha256(__file__))
    with args.output.open('x') as out:json.dump(result,out,indent=2,allow_nan=False)


if __name__=='__main__':main()

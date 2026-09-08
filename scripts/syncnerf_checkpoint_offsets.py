"""CPU-only matched-checkpoint repeatability from retained native Sync-NeRF state."""
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np
from syncnerf_basketball import export_offsets


def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--runs',type=Path,default=Path('.local/sync-pivot/runs'))
    p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    import torch
    directories=[a.runs/f'syncnerf-seed{s}/worker/model' for s in range(3)]
    available=[{int(p.name.split('-')[0]) for p in d.glob('*-model.pth') if p.name.split('-')[0].isdigit()} for d in directories]
    common=sorted(set.intersection(*available))
    if not common:raise ValueError('no common retained checkpoint across three seeds')
    step=common[-1];records=[];ids=[1,2,4,5,6,7,9,11]
    for seed,d in enumerate(directories):
        path=d/f'{step}-model.pth';state=torch.load(path,map_location='cpu',weights_only=True)
        if state['global_step']!=step or set(state)!={'model','optimizer','lr_scheduler','global_step'}:
            raise ValueError('unexpected native checkpoint schema or iteration')
        offsets=export_offsets(state['model']['cam_offset'].numpy())
        records.append(dict(seed=seed,iteration=step,checkpoint=str(path),checkpoint_sha256=digest(path),
                            offset_seconds={str(c):float(v) for c,v in zip(ids,offsets)}))
        del state
    matrix=np.array([[r['offset_seconds'][str(c)] for c in ids] for r in records])
    report=dict(schema='syncnerf-matched-checkpoint-offsets/v1',iteration=step,runs=records,
        camera_ids=ids,mean_seconds=matrix.mean(0).tolist(),range_seconds=np.ptp(matrix,axis=0).tolist(),
        sample_standard_deviation_seconds=matrix.std(0,ddof=1).tolist(),script_sha256=digest(__file__),
        policy='largest saved native checkpoint shared by all three seeds; CPU deserialize only; no additional optimizer or renderer invocation',
        caveat='repeatability is not ground-truth accuracy; native checkpoint omits RNG and AMP scaler state, so exact training continuation is not established; full model/optimizer/scheduler and offsets are retained')
    a.output.write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
    print(json.dumps(dict(iteration=step,mean_milliseconds=(matrix.mean(0)*1000).tolist(),range_milliseconds=(np.ptp(matrix,axis=0)*1000).tolist())))


if __name__=='__main__':main()

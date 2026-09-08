"""Retain pilot offsets and seed disagreement without inventing timing truth."""
import argparse
import hashlib
import json
from pathlib import Path
import statistics


def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--runs',type=Path,default=Path('.local/sync-pivot/runs'))
    p.add_argument('--output',type=Path,default=Path('docs/research/basketball-sync-pivot/syncnerf-results.json'))
    a=p.parse_args();root=Path(__file__).resolve().parents[1]
    ledger=json.loads((root/'docs/research/basketball-sync-pivot/gpu-budget.json').read_text())
    saved=json.loads((root/'docs/research/basketball-sync-pivot/sift-common-graph.json').read_text())['global_fit']['offset_seconds']
    records=[];offsets={}
    for seed in range(3):
        path=a.runs/f'syncnerf-seed{seed}'
        attempts=[x for x in ledger['attempts'] if x['role']==f'syncnerf-basketball-seed{seed}']
        if not attempts:records.append(dict(seed=seed,status='unrun'));continue
        attempt=attempts[0];row=dict(seed=seed,status=attempt['status'],charged_seconds=attempt['charged_seconds'],
                                   supervisor_path=str(path/'supervisor-result.json'))
        timing=path/'worker/timing.json';worker=path/'worker/worker-result.json'
        if timing.exists() and worker.exists():
            data=json.loads(timing.read_text());result=json.loads(worker.read_text())
            row.update(timing=data,timing_sha256=digest(timing),worker_result=result,worker_result_sha256=digest(worker))
            for c,offset in data['offset_seconds'].items():
                if offset is not None:offsets.setdefault(c,[]).append((seed,offset))
        records.append(row)
    cameras=[]
    for c,values in sorted(offsets.items(),key=lambda x:int(x[0])):
        if [v[0] for v in values]!=[0,1,2]:continue
        numbers=[v[1] for v in values]
        cameras.append(dict(camera_id=c,offsets_milliseconds=[1000*v for v in numbers],
            mean_milliseconds=1000*statistics.mean(numbers),range_milliseconds=1000*(max(numbers)-min(numbers)),
            sample_standard_deviation_milliseconds=1000*statistics.stdev(numbers),
            saved_sift_milliseconds=None if saved[c] is None else saved[c]*1000,
            mean_minus_saved_sift_milliseconds=None if saved[c] is None else 1000*(statistics.mean(numbers)-saved[c])))
    report=dict(schema='syncnerf-basketball-pilots/v1',runs=records,camera_seed_disagreement=cameras,
        three_seed_export_complete=len(cameras)==8,ground_truth_accuracy=None,full_rig_correction=None,
        interpretation='Seed spread describes optimizer repeatability, not timing uncertainty or ground-truth error. Saved SIFT disagreement uses the same reference and sign but cannot adjudicate accuracy. Eight-camera coverage cannot authorize full-rig correction.',
        author_target_steps=90001,maximum_seconds_per_seed=2400,test_image_optimization=False,
        source_frames=[50,149],final_window_images_opened=False,script_sha256=digest(__file__))
    a.output.write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
    print(json.dumps(dict(three_seed_export_complete=report['three_seed_export_complete'],cameras=cameras),indent=2))


if __name__=='__main__':main()

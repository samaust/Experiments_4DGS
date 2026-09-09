"""Plan 027 complete trajectory coverage, native resource curves, and job audit."""
import argparse
import json
from pathlib import Path

import numpy as np

from basketball_dense_training import ARTIFACTS, ARMS, ORDER
from basketball_study import CURVE, ROOT, digest, verify_files, write_new


def ledger_audit(events):
    active, finished, charged = None, [], {}
    for event in events:
        if event['event'] == 'start':
            if active is not None:
                raise ValueError('overlapping GPU jobs')
            active = event['output']
        elif event['event'] in ('finish', 'failure'):
            if event['output'] != active:
                raise ValueError('unpaired GPU job accounting')
            active = None
            finished.append(event)
            charged[event['stage']] = charged.get(event['stage'],0.)+event['charged_seconds']
        elif event['event'] == 'cleanup-failed':
            raise ValueError('GPU process cleanup not confirmed')
    if active is not None:
        raise ValueError('unclosed GPU job')
    return dict(closed_jobs=len(finished), peak_concurrency=1 if finished else 0,
        failures=[e for e in finished if e['event']=='failure' or e.get('exit_code') or e.get('interrupted')],
        charged_gpu_job_wall_seconds=charged)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args()
    verify_files(json.loads((ARTIFACTS/'historical-links.json').read_text())['files'])
    events=[json.loads(line) for line in (ARTIFACTS/'ledger.jsonl').read_text().splitlines()]
    accounting=ledger_audit(events)
    records,series=[],{}
    for arm,seed in ORDER:
        folder=ARTIFACTS/f'training/{arm}-seed{seed}'
        all_rows=[]; results=[]; checkpoints=[]; elapsed=0.
        for endpoint,start in ((5000,0),(50000,5000)):
            segment=folder/f'{endpoint:06d}'
            result=json.loads((segment/'worker-result.json').read_text())
            if not result['completed'] or result['iteration']!=endpoint:
                raise ValueError('incomplete dense endpoint')
            rows=[json.loads(line) for line in (segment/'loss.jsonl').read_text().splitlines()]
            if [r['iteration'] for r in rows]!=list(range(start+1,endpoint+1)):
                raise ValueError('missing, repeated, or excess training updates')
            if any(not all(np.isfinite(r[k]) for k in ('loss','points','elapsed_seconds')) for r in rows):
                raise ValueError('nonfinite trajectory')
            if any(b['elapsed_seconds']<c['elapsed_seconds'] for c,b in zip(rows,rows[1:])):
                raise ValueError('nonmonotonic segment timing')
            for r in rows:r['elapsed_seconds']+=elapsed
            elapsed=rows[-1]['elapsed_seconds']
            all_rows.extend(rows); results.append(result)
            for step in CURVE:
                if start<step<=endpoint:
                    path=segment/f'checkpoint-{step:06d}.pt'
                    saved=next(c for c in result['checkpoints'] if c['iteration']==step)
                    if digest(path)!=saved['sha256']:
                        raise ValueError('retained checkpoint changed')
                    checkpoints.append(dict(iteration=step,path=str(path),sha256=saved['sha256'],bytes=path.stat().st_size))
        frozen=json.loads((ARTIFACTS/'initializers'/arm/'result.json').read_text())
        if {r['points'] for r in all_rows}!={frozen['total_gaussians']}:
            raise ValueError('unexpected point-count change')
        series[arm,seed]=all_rows
        records.append(dict(arm=arm,seed=seed,updates=len(all_rows),points=frozen['total_gaussians'],
            optimizer_loop_seconds=elapsed,final_loss=all_rows[-1]['loss'],checkpoints=checkpoints,
            peak_allocated_bytes=max(r['peak_allocated_bytes'] for r in results),
            peak_reserved_bytes=max(r['peak_reserved_bytes'] for r in results)))
    a.output.mkdir(parents=True,exist_ok=False)
    write_new(a.output/'trajectories.json',dict(records=records,production_updates=sum(r['updates'] for r in records),
        accounting=accounting,scope='six new dense trajectories; historical resource evidence preserved separately'))
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,axes=plt.subplots(2,2,figsize=(12,8),constrained_layout=True)
    for column,arm in enumerate(ARMS):
        for seed in range(3):
            rows=series[arm,seed]
            blocks=[rows[i:i+100] for i in range(0,len(rows),100)]
            x=[b[-1]['iteration'] for b in blocks]
            axes[0,column].plot(x,[np.mean([r['loss'] for r in b]) for b in blocks],label=f'seed {seed}')
            axes[1,column].plot(x,[b[-1]['points'] for b in blocks],label=f'seed {seed}')
        axes[0,column].set_title(arm)
        axes[0,column].set_ylabel('Native loss (100-update mean)')
        axes[1,column].set_ylabel('Point count')
        for panel in axes[:,column]:
            panel.set_xlabel('Absolute optimizer update');panel.legend();panel.grid(alpha=.2)
    fig.savefig(a.output/'training-trajectories.png',dpi=150)
    plt.close(fig)


if __name__=='__main__':main()

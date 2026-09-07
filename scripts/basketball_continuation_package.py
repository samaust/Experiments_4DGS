"""Package rev2 scale/timing evidence without opening reserved timing images."""
import argparse
from collections import Counter
import json
import os
from pathlib import Path

from basketball_audit import sha256
from basketball_continuation_audit import verify_hashes


def read(path):return json.loads(Path(path).read_text())


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--workspace',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();w=a.workspace;out=a.output;out.mkdir(parents=True,exist_ok=True)
    audit=read(w/'provenance/result.json');verify_hashes(audit['sha256'])
    artifacts={}
    for name in ['scale-fit.json','scale-selection.json','timing-fit.json','timing-fit-precise.json']:
        source=w/name;value=read(source)
        if name.startswith('timing-'):
            # One complete edge per line retains every curve without thousands
            # of single-number lines; original byte hashes remain inventoried.
            edges=value.pop('edges')
            text=json.dumps(value,indent=2)[:-2]+',\n  "edges": [\n'
            text+=',\n'.join('    '+json.dumps(e,separators=(',',':'),allow_nan=False) for e in edges)+'\n  ]\n}\n'
            (out/name).write_text(text)
            assert read(out/name)==read(source)
        else:
            (out/name).write_bytes(source.read_bytes())
        artifacts[str(source)]=sha256(source)
    timing=read(w/'timing-fit-precise.json');tracks=read(w/'timing-fit-tracks-precise/result.json')
    verify_hashes({str(w/'timing-fit-tracks-precise/result.json'):timing['tracks_sha256'],
                   str(w/'timing-fit-tracks-precise/protocol.json'):timing['protocol_sha256'],
                   'scripts/basketball_timing.py':timing['adapter_sha256']})
    for c in tracks['cameras']:
        verify_hashes({str(w/f"timing-fit-tracks-precise/camera{c['camera_id']}-tracks.json"):c['sha256']})
    for name in ['timing-fit-tracks.log','timing-fit.log','timing-fit-tracks-verified.log',
                 'timing-fit-tracks-precise.log','timing-fit-precise.log','timing-fit-precise-resources.txt',
                 'basketball-tests-final.log','budget-tests.log','selfcap-tests.log','basketball_timing-initial.py']:
        artifacts[str(w/name)]=sha256(w/name)
    reasons=Counter(reason for e in timing['edges'] for reason in e.get('refined',e['integer'])['blockers'])
    summary=dict(status=timing['status'],blockers=timing['blockers'],accepted_edges=timing['accepted_edges'],
        candidate_edges=len(timing['edges']),rejection_counts=dict(reasons),unreachable_cameras=timing.get('unreachable_cameras',[]),
        total_tracks=sum(c['tracks'] for c in tracks['cameras']),camera_tracks=tracks['cameras'],
        corrected_tracking_wall_seconds=tracks['wall_seconds'],
        initial_tracking_wall_seconds=read(w/'timing-fit-tracks/result.json')['wall_seconds'],
        corrected_fitting_resources=(w/'timing-fit-precise-resources.txt').read_text(),
        numerical_repairs=['default inverse distortion max roundtrip 0.0102196px; explicit 50-iteration convergence now <1e-6px',
                           'test actual signed fundamental cycle closure before least-squares residuals'],
        failed_cpu_attempt=dict(path=str(w/'timing-fit-tracks-verified'),error='OpenCV 5 exposes criteria on undistortPoints, not undistortPointsIter',
                                wall_seconds=None,gpu_seconds=0),
        timing_selection_consumed=False,timing_final_validation_consumed=False,
        initialization_started=False,training_started=False,evaluation_started=False,
        artifact_sha256=artifacts)
    (out/'timing-summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    os.environ.setdefault('MPLCONFIGDIR',str(w/'matplotlib-cache'))
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    plt.rcParams['svg.hashsalt']='basketball-rev2'
    fit=read(w/'scale-fit.json');selection=read(w/'scale-selection.json')
    fig,axes=plt.subplots(2,1,figsize=(12,8),layout='constrained')
    for value,label,marker in [(fit,'Fitting frame 100','o'),(selection,'Reserved frame 175','x')]:
        rows=value['cameras'];axes[0].plot([r['camera_id'] for r in rows],[r['scale'] for r in rows],marker+'-',label=label)
    scale=fit['scale'];axes[0].axhline(scale,color='black',label='Frozen global scale')
    axes[0].axhspan(*fit['bootstrap_95_interval'],color='gray',alpha=.2,label='Fit camera-bootstrap 95% interval')
    axes[0].set(xlabel='Physical training camera ID',ylabel='Estimated metres / calibration unit',title='Scale passes fitting and reserved-frame checks')
    axes[0].legend(fontsize=8,ncol=2)
    labels=[];values=[];colors=[]
    for e in timing['edges']:
        labels.append(f"{e['a']}–{e['b']}")
        r=e.get('refined',e['integer']);interval=r.get('bootstrap_95_frames')
        values.append((interval[1]-interval[0])/2 if interval else float('nan'))
        colors.append('#2c7a45' if e['passed'] else '#bd4435')
    axes[1].bar(range(len(values)),values,color=colors)
    axes[1].axhline(.25,color='black',linestyle='--',label='0.25-frame gate')
    axes[1].set_xticks(range(len(labels)),labels,rotation=90,fontsize=6)
    axes[1].set(ylabel='Timing bootstrap 95% halfwidth (frames)',xlabel='Candidate camera pair (gaps lack track support)',
                title='Timing blocked: 24 / 71 edges pass; accepted graph is disconnected')
    axes[1].legend()
    fig.savefig(out/'scale-timing.svg',metadata={'Date':None})
    svg=out/'scale-timing.svg'
    svg.write_text('\n'.join(line.rstrip() for line in svg.read_text().splitlines())+'\n')
    fig.savefig(w/'scale-timing-preview.png',dpi=120)
    plt.close(fig)
    print('Packaged',len(artifacts),'artifact hashes; timing',timing['status'])


if __name__=='__main__':main()

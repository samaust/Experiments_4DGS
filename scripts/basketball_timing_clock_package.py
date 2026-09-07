"""Package clock evidence, retaining and explicitly rejecting the logo locator run."""
import argparse
import json
from pathlib import Path
import shutil

from basketball_audit import sha256
from basketball_continuation_audit import verify_hashes
from basketball_scale import read


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspace',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--refresh',action='store_true',help='Refresh this task-owned publication from preserved local evidence')
    a=parser.parse_args();current=a.workspace/'display-verified';old=a.workspace/'run'
    result=read(current/'result.json');verify_hashes(result['sha256']);verify_hashes(result['artifacts_sha256'])
    rejected=read(old/'result.json');verify_hashes(rejected['artifacts_sha256'])
    archived=a.workspace/'source-initial.py'
    original_sources={k:v for k,v in rejected['sha256'].items() if not k.endswith('/basketball_timing_clock.py')}
    original_code=next(v for k,v in rejected['sha256'].items() if k.endswith('/basketball_timing_clock.py'))
    verify_hashes(original_sources);verify_hashes({str(archived):original_code})
    initial_display=read(a.workspace/'display-run/result.json')
    display_archive=a.workspace/'source-display-initial.py'
    display_code=next(v for k,v in initial_display['sha256'].items() if k.endswith('/basketball_timing_clock.py'))
    verify_hashes({str(display_archive):display_code});verify_hashes(initial_display['artifacts_sha256'])
    assert initial_display['edges']==result['edges'] and initial_display['cameras']==result['cameras']
    a.output.mkdir(parents=True,exist_ok=a.refresh)
    def write(path,value):
        # Only the task-owned publication is refreshable; local runs stay immutable.
        path.write_text(json.dumps(value,indent=2)+'\n')
    # One camera/edge per line retains all raw signals and search curves.
    summary={k:v for k,v in result.items() if k not in ['cameras','edges']}
    text=json.dumps(summary,indent=2)[:-2]
    for key in ['cameras','edges']:
        text+=',\n  "'+key+'": [\n'+',\n'.join('    '+json.dumps(e) for e in result[key])+'\n  ]'
    (a.output/'result.json').write_text(text+'\n}\n')
    assert read(a.output/'result.json')==result
    write(a.output/'rejected-locator.json',dict(status='rejected',reason='preview identifies court logo, not clock',
        result_sha256=sha256(old/'result.json'),archived_source=str(archived),archived_source_sha256=original_code,
        initial_protocol=read(old/'frozen.json'),wall_seconds=rejected['wall_seconds'],gpu_seconds=0,
        interpretation='All initial lag outputs are invalid clock evidence and excluded'))
    for name in ['regions.jpg','camera25-clock.jpg','camera33-clock.jpg','frozen.json']:
        shutil.copyfile(current/name,a.output/name)
    shutil.copyfile(old/'regions.jpg',a.output/'rejected-regions.jpg')
    prior=read('docs/experiments/basketball-advertising-recovery/result.json')
    directed={}
    for e in prior['edges']:
        directed[e['a'],e['b']]=e['lag'];directed[e['b'],e['a']]=-e['lag']
    write(a.output/'comparison.json',dict(status='diagnostic_only',prior_sha256=sha256('docs/experiments/basketball-advertising-recovery/result.json'),
        edges=[dict(a=e['a'],b=e['b'],motion_lag_frames=directed[e['a'],e['b']],
                    clock_integer_lag_frames=e.get('lag_frames'),clock_integer_bootstrap_95=e.get('bootstrap_95_integer_frames')) for e in result['edges']],
        conclusion='No whole-frame discrepancy flagged; quantized clock evidence cannot attribute subframe cycle failures to a camera or edge'))
    write(a.output/'evidence.json',dict(source_sha256={str(Path(__file__)):sha256(__file__)},
        result_sha256=sha256(current/'result.json'),logs_sha256={str(p):sha256(p) for p in a.workspace.glob('*.log')},
        ledger_sha256=sha256('.local/calibration/basketball-v1/gpu-ledger.json'),
        artifacts_sha256={str(p):sha256(p) for p in sorted(a.output.iterdir()) if p.name!='evidence.json'},
        guarded_rerun=dict(reason='Explicit detection-frame role guard added; numerical signals and curves match the earlier corrected run exactly',
                          prior_result_sha256=sha256(a.workspace/'display-run/result.json'),archived_source_sha256=display_code,
                          prior_worker_seconds=initial_display['wall_seconds']),
        measured_worker_seconds=result['wall_seconds']+rejected['wall_seconds']+initial_display['wall_seconds'],gpu_seconds=0))


if __name__=='__main__':main()

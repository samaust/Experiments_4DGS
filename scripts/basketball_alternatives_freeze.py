"""Freeze the unique eligible full-rig candidate before final-frame preparation."""
import argparse
import json
from pathlib import Path
from basketball_audit import sha256
from basketball_alternatives_compare import load_export
from basketball_alternatives_protocol import CAMERAS


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--workspace',type=Path,required=True)
    p.add_argument('--full-rig',type=Path,required=True)
    p.add_argument('--selection',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args()
    full=json.loads((a.full_rig/'result.json').read_text())
    selection=json.loads((a.selection/'result.json').read_text())
    finalists=json.loads((a.workspace/'finalists.json').read_text())
    screened=json.loads((a.workspace/'screening.json').read_text())
    methods={r['method'] for r in screened['ranking'][:3]}
    eligible=[r for r in finalists['configurations'] if r.get('passes_training_gates')]
    identity=lambda r:(r['method'],r['policy'],r['sharp'])
    # This campaign has one eligible configuration. A future multiple-winner
    # campaign must evaluate every eligible candidate on selection before ranking.
    if len(eligible)!=1 or identity(eligible[0])!=identity(full):
        raise ValueError('requires selection comparison of all eligible candidates')
    if {r['method'] for r in finalists['configurations']}!=methods:
        raise ValueError('finalists differ from screening top three')
    exclusions=[]
    for config in finalists['configurations']:
        if identity(config)==identity(full):continue
        failures=[r for r in finalists['pairs'] if identity(r)==identity(config) and r['complete'] and
                  not (r['passed'] and r['support_passed'] and r['converged'])]
        if not failures:raise ValueError('another configuration could still qualify')
        exclusions.append(dict(configuration=list(identity(config)),failed_seed=failures[0]['seed']))
    if not full['passed'] or selection['status']!='passed' or selection['role']!='selection':
        raise ValueError('full-rig or selection gate failed')
    if len(selection['cameras'])!=34 or {r['camera_id'] for r in selection['cameras']}!=set(CAMERAS):
        raise ValueError('selection coverage incomplete')
    calibration=a.full_rig/'calibration.json';load_export(calibration,expected=CAMERAS)
    if selection['frozen_artifact_sha256'].get(str(calibration))!=sha256(calibration):
        raise ValueError('calibration changed after selection')
    for path,digest in selection['frozen_artifact_sha256'].items():
        if sha256(path)!=digest:raise ValueError(f'changed artifact: {path}')
    evaluator=Path(__file__).with_name('basketball_alternatives_evaluate.py')
    if selection['adapter_sha256']!=sha256(evaluator):raise ValueError('selection evaluator changed')
    record=dict(status='frozen',selection_passed=True,configuration=list(identity(full)),
                calibration_path=str(calibration),calibration_sha256=sha256(calibration),
                full_rig_result_sha256=sha256(a.full_rig/'result.json'),
                selection_result_path=str(a.selection/'result.json'),
                selection_result_sha256=sha256(a.selection/'result.json'),
                evaluation_adapter_sha256=sha256(evaluator),
                frozen_artifact_sha256=selection['frozen_artifact_sha256'],
                correspondence_policy=selection['correspondence_policy'],
                exclusions=exclusions,finalists_at_freeze=finalists,
                final_validation_frames=[200,212,225,237,249],
                metric_scale_verified=False,synchronization_verified=False)
    with a.output.open('x') as stream:json.dump(record,stream,indent=2,allow_nan=False);stream.write('\n')
    print(a.output)


if __name__=='__main__':main()

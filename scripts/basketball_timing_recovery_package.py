"""Publish saved timing recovery diagnostics without reading reserved frames."""
import argparse
from collections import Counter
import json
from pathlib import Path
from basketball_audit import sha256
from basketball_scale import read
from basketball_continuation_audit import verify_hashes


def compact_edges(path,value):
    value=dict(value);edges=value.pop('edges',None)
    if edges is None:
        path.write_text(json.dumps(value,indent=2,allow_nan=False)+'\n');return
    text=json.dumps(value,indent=2,allow_nan=False)[:-2]+',\n  "edges": [\n'
    text+=',\n'.join('    '+json.dumps(e,separators=(',',':'),allow_nan=False) for e in edges)+'\n  ]\n}\n'
    path.write_text(text)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--workspace',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();w=a.workspace;o=a.output;o.mkdir(parents=True,exist_ok=True)
    audit=read('.local/calibration/basketball-rev2/provenance/result.json');verify_hashes(audit['sha256'])
    frozen=read(w/'frozen/protocol.json');verify_hashes(frozen['source_sha256'])
    files=['sift-fit.json','roma-fit.json','complementary.json','component-cycles.json',
           'frozen/protocol.json','roma-seeds/config.json','roma-seeds/result.json','roma-tracks/result.json',
           'sift-fit.log','roma-infer.log','roma-tracks.log','roma-fit.log',
           'basketball-tests.log','budget-tests.log','selfcap-tests.log']
    hashes={str(w/name):sha256(w/name) for name in files}
    for name in ['sift-fit.json','roma-fit.json','complementary.json','component-cycles.json']:
        compact_edges(o/name,read(w/name))
        assert read(o/name)==read(w/name)
    seeds=read(w/'roma-seeds/result.json');tracks=read(w/'roma-tracks/result.json')
    for row in seeds['pairs']:verify_hashes({str(w/'roma-seeds'/row['path']):row['sha256']})
    for row in tracks['cameras']:verify_hashes({str(w/f"roma-tracks/camera{row['camera_id']}-tracks.json"):row['sha256']})
    verify_hashes(seeds['image_sha256']);verify_hashes(seeds['mask_sha256'])
    summary={}
    for name in ['sift-fit.json','roma-fit.json']:
        r=read(w/name)
        summary[name]=dict(status=r['status'],accepted_edges=r['accepted_edges'],candidate_edges=len(r['edges']),
            blockers=r['blockers'],unreachable_cameras=r.get('unreachable_cameras'),wall_seconds=r['wall_seconds'],
            rejection_counts=dict(Counter(reason for e in r['edges'] for reason in e.get('refined',e['integer'])['blockers'])))
    ledger_path=Path('.local/calibration/basketball-v1/gpu-ledger.json');ledger=read(ledger_path)
    attempts=[x for x in ledger['attempts'] if 'scripts/basketball_timing_roma.py' in x.get('command',[])]
    record=dict(schema='basketball-timing-recovery-evidence/v1',status='blocked',fits=summary,
        source_sha256={str(Path(__file__)):sha256(__file__),**frozen['source_sha256'],
                       'scripts/basketball_timing_roma.py':sha256('scripts/basketball_timing_roma.py'),
                       'scripts/basketball_timing_complementary.py':sha256('scripts/basketball_timing_complementary.py')},
        artifacts_sha256=hashes,dense_seed_count=sum(x['seeds'] for x in seeds['pairs']),
        dense_surviving_camera_endpoints=sum(x['tracks'] for x in tracks['cameras']),dense_pair_seed_records=seeds['pairs'],
        dense_track_records=tracks['cameras'],dense_inference_wall_seconds=seeds['wall_seconds'],
        dense_tracking_wall_seconds=tracks['wall_seconds'],runtime=seeds['runtime'],
        peak_allocated_bytes=seeds['peak_allocated_bytes'],peak_reserved_bytes=seeds['peak_reserved_bytes'],
        ledger_sha256=sha256(ledger_path),gpu_attempts=attempts,recovery_gpu_charge_seconds=sum(x['charged_seconds'] for x in attempts),
        original_ledger_total_seconds=sum(x['charged_seconds'] for x in ledger['attempts']),
        remaining_original_allowance_seconds=ledger['limit_seconds']-sum(x['charged_seconds'] for x in ledger['attempts']),
        downstream_extension_used=False,basketball_training_seconds=0,
        reserved_timing_selection_consumed=False,reserved_timing_validation_consumed=False,
        calibration_scale_unchanged=True,tests=dict(basketball=64,budget=7,selfcap=3))
    compact_edges(o/'evidence.json',record)
    print('Packaged recovery blocker; GPU seconds',record['recovery_gpu_charge_seconds'])


if __name__=='__main__':main()

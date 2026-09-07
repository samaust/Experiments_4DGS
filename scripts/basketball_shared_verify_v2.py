"""Independent reconstruction and publication verification for Plan008 blocker."""
import os
os.environ['OPENBLAS_NUM_THREADS']='1'
import argparse
from collections import Counter
import json
from pathlib import Path
import re
import subprocess
import time
from urllib.parse import unquote
from basketball_audit import sha256
from basketball_scale import read,write
from basketball_continuation_audit import verify_hashes

DOCS=['docs/experiments/basketball-shared-timing-v2.md','docs/experiments/basketball-rev2.md',
    'docs/experiments/contender-summary.md',*[f'docs/experiments/{name}.md' for name in ['006-stg-full','007-freetimegs','008-moe-gs','009-atgs','010-freetimegs-plus-plus']]]


def verify(a):
    evidence=read(a.evidence/'evidence.json')
    for key in ['source_sha256','immutable_sha256','artifact_sha256','test_logs_sha256']: verify_hashes(evidence[key])
    p=read('configs/basketball-rev2/timing-shared-v2.json')
    if time.time()>p['investigation_started_unix']+14400: raise TimeoutError('four-hour reporting deadline exceeded')
    groups=read(a.evidence/'groups.json')['groups']; matrix=read(a.evidence/'membership.json')
    partition=read(a.evidence/'partition.json'); support=read(a.evidence/'support.json')
    assignment=partition['assignment']; source_seen=set(); family_seen=set(); tracks={}
    verify_hashes(read(a.associate/'tracks/result.json')['source_sha256'])
    raw_count=0; checkpoint_count=0; duplicate_rejections=0
    for camera in range(34):
        raw=read(a.associate/'tracks'/f'camera{camera}-tracks.json')
        assert raw['role']=='fit' and raw['camera_id']==camera
        ids=set()
        for t in raw['tracks']:
            assert len(t['frames'])>=60 and min(t['frames'])>=50 and max(t['frames'])<=149
            assert all(b-a==1 for a,b in zip(t['frames'],t['frames'][1:]))
            assert t['source_track_id'] not in ids; ids.add(t['source_track_id'])
            assert t['seed_frame'] in p['seed_frames'] and t['seed_frame'] in t['frames']
            for d in t['descriptor_checkpoints']:
                assert d['frame'] in t['frames'] and (d['frame']-t['seed_frame'])%10==0
                assert d['source_track_id']==t['source_track_id'] and len(d['descriptor'])==128
            assert sum(d['kind']=='seed' for d in t['descriptor_checkpoints'])==1
            checkpoint_count+=len(t['descriptor_checkpoints'])
        raw_count+=len(raw['tracks'])
        families=read(a.associate/f'duplicate-camera{camera}.json')['families']
        family_ids=[i for f in families for i in f['source_track_ids']]
        assert len(family_ids)==len(set(family_ids)) and set(family_ids)==ids
        duplicate_rejections+=sum(f['status']=='rejected' for f in families)
        merged=read(a.associate/f'merged-camera{camera}.json')['tracks']; tracks[camera]=merged
        for f in families:
            if f['status']=='merged':
                t=merged[f['merged_track_id']]
                assert t['source_track_ids']==f['source_track_ids'] and t['duplicate_family_id']==f['duplicate_family_id']
    assert [g['group_id'] for g in groups]==list(range(len(groups)))==matrix['group_order']
    for g in groups:
        cameras=[m['camera_id'] for m in g['members']]
        assert len(cameras)==len(set(cameras)) and len(set(cameras)-{0,10,20,30})>=3
        for member in g['members']:
            c=member['camera_id']; t=tracks[c][member['track_id']]
            family=(c,t['duplicate_family_id']); assert family not in family_seen; family_seen.add(family)
            for identity in t['source_track_ids']:
                key=(c,identity); assert key not in source_seen; source_seen.add(key)
        if assignment is not None: assert g['split']==('assessment' if assignment[g['group_id']] else 'optimization')
        else: assert 'split' not in g
    assert len(support['edges'])==len(matrix['edge_order'])==72
    for i,(edge,row) in enumerate(zip(matrix['edge_order'],support['edges'])):
        assert (edge['a'],edge['b'])==(row['a'],row['b'])
        membership=[int({edge['a'],edge['b']}<={m['camera_id'] for m in g['members']}) for g in groups]
        assert membership==matrix['matrix'][i]
        ids=[j for j,present in enumerate(membership) if present]
        assert ids==row['group_ids'] and len(ids)==row['eligible_groups']==partition['edge_totals'][i]
        if assignment is not None:
            for value,role in [(0,'optimization'),(1,'assessment')]:
                selected=[j for j in ids if assignment[j]==value]
                assert selected==row['half_group_ids'][role] and len(selected)==row[role] and len(selected)>=12
        else: assert row['optimization'] is None and row['assessment'] is None
    if assignment is not None: assert abs(2*sum(assignment)-len(groups))<=1
    elif partition['status']=='insufficient_edge_support': assert any(e['eligible_groups']<24 for e in support['edges'])
    terminal=read(a.evidence/'result.json');synthetic=read(a.evidence/'synthetic-summary.json')
    assert terminal['status']=='blocked' and terminal['terminal_kind']=='numerical_failure'
    assert terminal['candidate_offsets'] is None and terminal['accepted_timing'] is None
    assert terminal['model_configurations_fitted_to_real_data']==0
    assert synthetic['optimizer_controls_attempted']==1890 and synthetic['optimizer_matrix_complete']
    assert synthetic['independent_controls_attempted']==3 and not synthetic['independent_matrix_complete']
    assert len(synthetic['targeted_identifiability_controls'])==3
    assert all(not r['data_only_identified'] and not r['estimator_qualified'] and r['safeguard_passed'] for r in synthetic['targeted_identifiability_controls'])
    failed=synthetic['failed_independent_controls'];assert len(failed)==1
    case=read(failed[0]['group_profiles_and_optimizer_traces_path'])
    assert (case['motion'],case['length'],case['noise'],case['delta'])==('direction_changes',100,0.,-.1)
    profiles=case['result']['profiles']
    assert profiles['regularized']['passed'] and profiles['regularized']['lag']==-.1
    assert profiles['data_only']['support']==0 and profiles['data_only']['lag'] is None
    traces=[t for row in case['result']['optimizer_traces'] if row['weight']==0 for t in row['optimizer_traces']]
    failures=[t for t in traces if not t['converged']]
    assert len(traces)==612 and len(failures)==71 and all(t['nfev']==200 for t in failures)
    assert not any(t['boundary_cameras'] for t in traces)
    broken=[]; link_count=0
    for name in DOCS:
        file=Path(name)
        for link in re.findall(r'\]\(([^)]+)\)',file.read_text()):
            link=link.split('#')[0]
            if not link or '://' in link or link.startswith('mailto:'): continue
            target=(file.parent/unquote(link.strip('<>'))).resolve(); link_count+=1
            if target!=a.output.resolve() and not target.exists(): broken.append(dict(source=name,target=str(target)))
    if broken: raise ValueError('broken documentation links: '+json.dumps(broken))
    subprocess.run(['git','diff','--check'],check=True)
    subprocess.run(['git','diff','--cached','--check'],check=True)
    tests={}
    for name in ['basketball','budget','selfcap']:
        log=(a.evidence/f'{name}-tests.log').read_text()
        assert re.search(r'\nOK\s*$',log) and 'FAILED (' not in log
        tests[name]=int(re.search(r'Ran (\d+) tests?',log).group(1))
    markers=sorted(str(f) for f in Path('.local/calibration/basketball-rev2').rglob('*consumed*.json'))
    expected=['.local/calibration/basketball-rev2/timing-selection/run/selection-consumed.json']
    assert markers==expected,markers
    elapsed=time.time()-p['investigation_started_unix']
    if elapsed>14400:raise TimeoutError('four-hour reporting deadline exceeded')
    write(a.output,dict(status='passed',evidence_sha256=sha256(a.evidence/'evidence.json'),
        verification_script_sha256=sha256(__file__),source_and_artifact_hashes='passed',immutable_hashes='passed',
        raw_fitting_tracks=raw_count,descriptor_checkpoints=checkpoint_count,incompatible_duplicate_families=duplicate_rejections,
        reconstructed_edges=72,eligible_groups=len(groups),partition_status=partition['status'],partition_assignment_present=assignment is not None,
        no_source_trajectory_or_duplicate_family_leakage=True,optimizer_controls=1890,targeted_controls=3,independent_controls=3,data_only_fits=612,data_only_nonconverged_fits=71,data_only_complete_groups=0,terminal_kind=terminal['terminal_kind'],tests=tests,local_documentation_links=link_count,
        broken_links=broken,diff_check='passed',timing_consumption_markers=markers,
        elapsed_including_final_verification_seconds=elapsed,within_four_hour_deadline=elapsed<=14400,
        documentation_sha256={name:sha256(name) for name in DOCS}))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--evidence',type=Path,required=True)
    parser.add_argument('--associate',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    verify(parser.parse_args())

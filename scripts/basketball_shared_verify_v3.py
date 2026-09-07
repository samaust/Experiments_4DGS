"""Independent artifact/partition reconstruction for the Plan009 terminal blocker."""
import argparse
from collections import Counter
from pathlib import Path
import re
import subprocess
import time
from urllib.parse import unquote
from basketball_audit import sha256
from basketball_scale import read,write
from basketball_continuation_audit import verify_hashes

DOCS=['docs/experiments/basketball-shared-timing-v3.md','docs/experiments/basketball-rev2.md',
      'docs/experiments/contender-summary.md',*[f'docs/experiments/{n}.md' for n in
      ['006-stg-full','007-freetimegs','008-moe-gs','009-atgs','010-freetimegs-plus-plus']]]


def verify(a):
    if a.output.exists():raise FileExistsError('fresh verification output required')
    p=read(a.config);evidence=read(a.evidence/'evidence.json')
    assert time.time()<p['investigation_started_unix']+14400
    verify_hashes(evidence['source_sha256']);verify_hashes(evidence['artifacts_sha256'])
    prior=read(p['prior_evidence'])
    assert sha256(p['prior_evidence'])==evidence['historical_evidence_sha256']
    for k in ['source_sha256','immutable_sha256','artifact_sha256','test_logs_sha256']:verify_hashes(prior[k])
    manifest=read(a.evidence/'cross-version-manifest.json');verify_hashes(manifest['source_sha256'])
    assert manifest['old_config_hashes_rewritten'] is False
    assert manifest['predecessor_config_sha256']==sha256(p['prior_config'])
    assert manifest['new_config_sha256']==sha256(a.config)
    admission=Path(p['admission']);groups=read(admission/'groups.json')['groups']
    matrix=read(admission/'membership.json');partition=read(admission/'partition.json');support=read(admission/'support.json')
    assignment=partition['assignment'];tracks={c:read(admission/f'merged-camera{c}.json')['tracks'] for c in range(34)}
    seen_sources=set();seen_families=set()
    assert len(groups)==1334 and Counter(g['split'] for g in groups)==dict(optimization=667,assessment=667)
    assert [g['group_id'] for g in groups]==matrix['group_order']==list(range(1334))
    for g in groups:
        cameras=[m['camera_id'] for m in g['members']]
        assert len(cameras)==len(set(cameras)) and len(set(cameras)-{0,10,20,30})>=3
        assert g['split']==('assessment' if assignment[g['group_id']] else 'optimization')
        for m in g['members']:
            c=m['camera_id'];t=tracks[c][m['track_id']]
            assert min(t['frames'])>=50 and max(t['frames'])<=149
            family=(c,t['duplicate_family_id']);assert family not in seen_families;seen_families.add(family)
            for source in t['source_track_ids']:
                key=(c,source);assert key not in seen_sources;seen_sources.add(key)
    assert len(matrix['edge_order'])==len(support['edges'])==72
    half_min=1334
    for i,(edge,row) in enumerate(zip(matrix['edge_order'],support['edges'])):
        assert (edge['a'],edge['b'])==(row['a'],row['b'])
        membership=[int({edge['a'],edge['b']}<={m['camera_id'] for m in g['members']}) for g in groups]
        assert membership==matrix['matrix'][i]
        ids=[j for j,v in enumerate(membership) if v];assert ids==row['group_ids']
        for value,role in [(0,'optimization'),(1,'assessment')]:
            chosen=[j for j in ids if assignment[j]==value]
            assert chosen==row['half_group_ids'][role] and len(chosen)==row[role]
            half_min=min(half_min,len(chosen))
    assert half_min==19
    reuse=read(a.evidence/'controls-reuse.json')['controls'];assert len(reuse)==1890
    verify_hashes({r['path']:r['sha256'] for r in reuse})
    for r in reuse:
        old=read(r['path'])
        assert all(old[k]==r[k] for k in ['configuration','motion','length','noise_pixels','known_offset_frames'])
        assert r['independent_qualification']=='requires v3 reassessment'
    exact=read(a.evidence/'exact-retest.json');profiles=exact['profiles']
    raw=read(exact['raw_profiles_and_initializations'])['result']
    assert not exact['safeguard_passed'] and exact['terminal_kind']=='numerical_failure'
    assert profiles['regularized']['passed'] and profiles['regularized']['lag']==-.1
    assert profiles['data_only']['support']==12 and profiles['data_only']['lag']==-.1
    assert not profiles['data_only']['passed']
    assert {k:v['support'] for k,v in profiles['data_only']['sweeps'].items()}==dict(ascending=11,descending=10)
    failures=[]
    for trace in raw['optimizer_traces']:
        for state in trace['states']:
            all_lags=sorted(map(float,state['attempts']))
            assert set(range(-25,26))<=set(all_lags)
            assert min(all_lags)==-25 and max(all_lags)==25
            assert len(all_lags)==97
            for lag,attempts in state['attempts'].items():
                assert len(attempts)==3 and [r['start'] for r in attempts]==['cold','ascending','descending']
                for r in attempts:
                    assert r['problem_key']==state['problem_key']
                    assert r['seed_problem_key'] in [None,state['problem_key']]
                    assert r['nfev']<=200
                    assert r['offsets']['1']==0. and r['offsets']['2']==float(lag)
                    if r['start']=='cold':
                        assert r['seed_lag'] is None and r['seed_start'] is None
                    else:
                        seeds=state['attempts'][str(r['seed_lag'])]
                        seed=next(v for v in seeds if v['start']==r['seed_start'])
                        assert seed['valid'] and r['initial_x']==seed['x']
                        if float(lag) not in range(-25,26):
                            assert (r['seed_lag']<float(lag) if r['start']=='ascending' else r['seed_lag']>float(lag))
                    if not r['valid']:failures.append(dict(group_id=state['group_id'],weight=trace['weight'],lag=float(lag),start=r['start'],nfev=r['nfev'],positive_depth=r['positive_depth'],converged=r['converged']))
            # Reconstruct best-of-three costs independently.
            profile=profiles['data_only' if trace['weight']==0 else 'regularized']
            gi=profile['group_ids'].index(state['group_id'])
            for lag,reported in zip(profile['grid'],profile['group_profile_costs'][gi]):
                candidates=state['attempts'][str(lag)]
                valid=[r['objective'] for r in candidates if r['valid']]
                assert reported==(min(valid) if valid else None)
    assert len(failures)==12 and all(r['converged'] and not r['positive_depth'] and r['weight']==0 for r in failures)
    diagnostics=read(a.evidence/'solver-comparisons.json')['problems'];assert len(diagnostics)==48
    for row in diagnostics:
        xs=[read(Path(v['raw_residuals_and_coefficients']))['solvers'][name]['initial_x'] for name,v in row['solvers'].items()]
        assert xs[0]==xs[1]==xs[2]
        for pair in row['comparisons']:
            a1=row['solvers'][pair['a']]['objective'];b1=row['solvers'][pair['b']]['objective']
            assert pair['agrees']==(abs(a1-b1)<=1e-6+1e-4*max(abs(a1),abs(b1)))
    terminal=read(a.evidence/'result.json')
    assert terminal['status']=='blocked' and terminal['terminal_kind']=='numerical_failure'
    assert terminal['candidate_offsets'] is None and terminal['accepted_timing'] is None
    markers=sorted(str(f) for f in Path('.local/calibration/basketball-rev2').rglob('*consumed*.json'))
    assert markers==['.local/calibration/basketball-rev2/timing-selection/run/selection-consumed.json']
    broken=[];links=0
    for name in DOCS:
        file=Path(name)
        for link in re.findall(r'\]\(([^)]+)\)',file.read_text()):
            link=link.split('#')[0]
            if not link or '://' in link or link.startswith('mailto:'):continue
            target=(file.parent/unquote(link.strip('<>'))).resolve();links+=1
            if target!=a.output.resolve() and not target.exists():broken.append(dict(source=name,target=str(target)))
    assert not broken,broken
    tests={};logs={}
    for name in ['basketball','budget','selfcap']:
        file=a.logs/f'{name}-tests.log';text=file.read_text()
        assert re.search(r'\nOK\s*$',text) and 'FAILED (' not in text
        tests[name]=int(re.search(r'Ran (\d+) tests?',text).group(1));logs[str(file)]=sha256(file)
    subprocess.run(['git','diff','--check'],check=True)
    subprocess.run(['git','diff','--cached','--check'],check=True)
    elapsed=time.time()-p['investigation_started_unix'];assert elapsed<14400
    write(a.output,dict(status='passed',evidence_sha256=sha256(a.evidence/'evidence.json'),
        verification_script_sha256=sha256(__file__),tests=tests,test_logs_sha256=logs,
        all_artifact_and_historical_hashes_verified=True,production_controls_verified=1890,
        groups=1334,groups_per_half=667,edges_reconstructed=72,minimum_groups_per_edge_per_half=half_min,
        no_source_track_or_duplicate_family_leakage=True,failed_attempts=failures,
        initialization_and_cache_provenance_verified=True,identical_diagnostic_initial_states=True,
        timing_consumption_markers=markers,documentation_links=links,broken_links=broken,
        documentation_sha256={n:sha256(n) for n in DOCS},working_tree_diff_check='passed',staged_diff_check='passed',
        elapsed_including_verification_seconds=elapsed,within_four_hours=True,
        accepted_timing=None,selection_consumed_this_attempt=False,final_validation_consumed=False))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for key in ['config','evidence','logs','output']:parser.add_argument('--'+key,type=Path,required=True)
    verify(parser.parse_args())

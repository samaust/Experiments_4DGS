"""Terminal packaging preserves failures, unknown counts and unassessed gates."""
from pathlib import Path
import json
from basketball_scale import read,write
from basketball_shared_diagnose_v5 import compressed_read
from basketball_audit import sha256

def ledger(scheduled,executed=0,qualified=0):
    return dict(scheduled=scheduled,executed=executed,missing=None if executed is None or scheduled is None else scheduled-executed,qualified=qualified)

def package(output,prior,predecessor,p):
    roots={predecessor}
    roots.update(Path(f).parent for f in prior['source_sha256'] if f.endswith('/result.json') and '/basketball-shared-timing-v8/' in f)
    decisions={name:dict(status='unassessed',passed=None,reason='required preceding gate did not pass') for name in ['conditioning','scalar_basins','combined']}
    counts=dict(conditioning=ledger(144),scalar_initial=ledger(7344),scalar_refinement=ledger(None),joint_releases=ledger(None),complete_outer=ledger(144),historical_replays=ledger(0))
    sources={}
    for root in sorted(roots):
        recovery=root/'recovery-decision.json'
        if recovery.exists():counts['historical_replays']=read(recovery)['replay_ledger']
        for name,file in [('conditioning','conditioning-decision.json'),('scalar_basins','basin-decision.json'),('combined','combined-decision.json')]:
            if (root/file).exists():
                r=read(root/file);decisions[name]=dict(status='passed' if r['passed'] else 'rejected',**r);sources[str(root/file)]=sha256(root/file)
                if name=='conditioning':counts[name]=ledger(144,r['executed'],r['qualified'])
                elif name=='combined':counts['complete_outer']=ledger(144,r['outer_searches'],r['qualified'])
        if (root/'worker-ledger.json').exists() and root.name=='condition' and not (root/'conditioning-decision.json').exists():
            artifacts=list(root.glob('weight*-group*.json.gz'))
            rows=[r for f in artifacts for rs in compressed_read(f)['attempts'].values() for r in rs]
            counts['conditioning']=ledger(144,None,None)
            counts['conditioning']['known_completed_attempts']=len(rows)
        if root.name=='basins':
            # Start events without finish events imply unknown actual execution, not zero.
            initial=refined=initial_valid=refined_valid=0;started=finished=0;scheduled=0
            for f in root.glob('*.events.jsonl'):
                for line in f.read_text().splitlines():
                    try:e=json.loads(line)
                    except json.JSONDecodeError:continue
                    if e['event']=='scheduled':scheduled+=3*len(e['points'])
                    elif e['event']=='started':started+=1
                    elif e['event']=='finished':
                        finished+=1;is_initial=float(e['offset']).is_integer()
                        if is_initial:initial+=int(e['executed']);initial_valid+=int(e['qualified'])
                        else:refined+=int(e['executed']);refined_valid+=int(e['qualified'])
            unknown=started!=finished
            counts['scalar_initial']=ledger(7344,None if unknown else initial,initial_valid)
            counts['scalar_refinement']=ledger(max(0,scheduled-7344) if scheduled>=7344 else None,None if unknown else refined,refined_valid)
            counts['scalar_initial']['known_executed']=initial;counts['scalar_refinement']['known_executed']=refined
            counts['scalar_initial']['unclosed_started_events']=started-finished
    if prior['stage']=='recover' and not (predecessor/'recovery-decision.json').exists():counts['historical_replays']=ledger(None,None,None)
    write(output/'development-decisions.json',decisions);write(output/'search-ledgers.json',counts)
    write(output/'resources.json',dict(elapsed_predecessor_seconds=prior['elapsed_seconds'],stage_wall_seconds={root.name:read(root/'result.json')['wall_seconds'] for root in roots if (root/'result.json').exists()},gpu_seconds=0))
    return dict(status=prior['status'],terminal_kind=prior['terminal_kind'],blockers=prior['blockers'],blocked_stage=None if prior['status']=='passed' else prior['stage'],conditioning_decision=decisions['conditioning']['status'],basin_decision=decisions['scalar_basins']['status'],combined_decision=decisions['combined']['status'],decision_sources_sha256=sources)

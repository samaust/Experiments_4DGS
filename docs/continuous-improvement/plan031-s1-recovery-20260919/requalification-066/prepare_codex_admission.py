import json,hashlib,sys
from pathlib import Path
ROOT=Path.cwd();sys.path.insert(0,str(ROOT/'scripts'))
from vipe_benchmark.files import file_record as record
from vipe_benchmark.s1_validation_contract import source_paths,STDIN,ARGV,THREADS,session_proof
from vipe_benchmark.budgets import budget_snapshot
RUN=ROOT/'docs/resolve-blocker/plan031-progress-20260922'
kind=sys.argv[2] if len(sys.argv)>2 else 'aggregate';index=int(sys.argv[1]);suffix=f'{kind}-{index:03d}';reason='Plan066 sampler source requalification under Codex'
identity_path=RUN/f'launch-identity-049-{suffix}.json';identity=json.loads(identity_path.read_text());identity_record=record(identity_path)
source_records=[record(p) for p in source_paths()]
event_paths=[RUN/f'main-session-049-{suffix}-event-{i:03d}.json' for i in range(4)]
events=[json.loads(p.read_text()) for p in event_paths]
handle=events[0]['result']['session_id'];readiness=events[1]['result']['output'].splitlines()[-1]
proof=dict(schema='plan049-session-proof/v2',proof_mode='session-bound/v2',kind=kind,index=index,session_id=handle,
 driver=record(RUN/'launch-049-exec.py'),identity_request=identity_record,admission_path=str(RUN/f'launch-admission-049-{suffix}.json'),
 tool_events=[record(p) for p in event_paths],readiness_event=1,readiness_line=readiness,readiness_line_sha256=hashlib.sha256(readiness.encode()).hexdigest(),admission_handoff=dict(session_id=handle,chars='ADMIT\n'),
 user_authorization=record(RUN/'authorization-049-session-proof-001.md'),correction=record(RUN/'plan049-correction-008.md'),plan054=record(ROOT/'plans/plan_054.md'),evidence_amendment=record(ROOT/'docs/resolve-blocker/plan031-session-proof-wrapper-20260923/correction-008-trust-amendment-001-proposal.md'),cross_namespace_kernel_verified=False)
proof_path=RUN/f'main-session-proof-049-{suffix}.json'
with proof_path.open('x') as f:json.dump(proof,f,indent=2);f.write('\n')
proof_record=record(proof_path)
session_proof(proof_record,kind,index,proof['driver'],identity_record,proof['admission_path'],reason)
dispatch_path=RUN/'implementation-dispatch-049.json';dispatch=json.loads(dispatch_path.read_text())
addenda=[record(RUN/f'plan049-correction-{i:03d}.md') for i in range(1,16)]
addenda += [record(RUN/f'plan049-correction-015-source-scope-addendum-{i:03d}.md') for i in (1,2,3,6)]
addenda.append(record(RUN.parent/'plan031-lost-exec-handle-20260925/candidate011-correction-adoption-001.md'))
directory=str(RUN/f'{kind}-049-{index:03d}');command=[str(ROOT/ARGV[0]),'-B','-m','vipe_benchmark.s1_validation_capture',directory,'--no-timeout']
if kind=='diagnostic':command.append('--diagnostic')
settings={k:'1' for k in (*THREADS,'OPENCV_FOR_THREADS_NUM','VIPE_CPU_VALIDATION')};settings['PYTHONPATH']=str(ROOT/'scripts')
identity_binding={k:identity[k] for k in ('ownership_root','preexisting_ancestors','ancestry_terminal','retained_wrappers','output_paths')}
bootstrap=json.loads(events[0]['result']['output'])
bindings=dict(session_proof=proof_record,plan054=proof['plan054'],evidence_amendment=proof['evidence_amendment'],plan=record(ROOT/'plans/plan_049.md'),dispatch=record(dispatch_path),status=dispatch['implementation_status_snapshot'],authorization=dispatch['authorization_note'],ancestor_authorization=record(RUN/'authorization-049-ancestor-process-001.md'),driver=proof['driver'],command=command,environment=settings,stdin=dict(bytes=len(STDIN.encode()),sha256=hashlib.sha256(STDIN.encode()).hexdigest()),run_directory=directory,identity_request=identity_record,addenda=addenda,job_ledger=bootstrap['awaiting_main_start_proof'],**identity_binding)
counts={k:len(list(RUN.glob('driver-049-'+k+'-*-exec-start.json'))) for k in ('diagnostic','aggregate')}
capacity=budget_snapshot(ROOT/'.local/vipe-alternatives/plan031-20260913T032700Z')
admission=dict(kind=kind,index=index,reason=reason,counts_before=counts,execution_mode='no-timeout',timeout_seconds=None,cpu_bound='B+max(1,H)≤8',approved=True,cleanup_resolved=True,resource_capacity=dict(B=0,H=1,charge=1,artifact_bytes=capacity['artifact_bytes']),source_paths=[r['path'] for r in source_records],sources=source_records,bindings=bindings)
with Path(proof['admission_path']).open('x') as f:json.dump(admission,f,indent=2);f.write('\n')
print('Validated actual same-session proof and wrote admission',proof['admission_path'])

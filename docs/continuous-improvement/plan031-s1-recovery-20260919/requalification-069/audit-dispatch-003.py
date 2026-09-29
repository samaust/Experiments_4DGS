"""Audit and freeze the single consumed S1 recovery 003 outcome."""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / 'scripts'))
from vipe_benchmark.config import load
from vipe_benchmark.files import file_record
from vipe_benchmark.ledger import Ledger
from vipe_benchmark.s1_recovery import validate_binding

HERE = Path(__file__).resolve().parent
LOCAL = ROOT / '.local/vipe-alternatives/plan031-20260913T032700Z'
LEDGER = LOCAL / 'ledger.jsonl'
JOB = 'S1-calibration-recovery-003'
AUTH = ROOT / 'docs/research/vipe-alternatives/plan031-20260913T032700Z/s1-calibration-recovery-authorization-003.json'
PRIOR = HERE.parent / 'requalification-067/post-dispatch-ledger-002.jsonl'

raw = LEDGER.read_bytes()
prior = PRIOR.read_bytes()
assert len(prior) == 351609 and hashlib.sha256(prior).hexdigest() == '97e55b9ab1d1651dfdfda227ead2a697352c1e445ec352902f53685b7e030a3b'
assert raw.startswith(prior)
events = Ledger(LEDGER, load()).events()
assert len(events) == 467
assert [event['event'] for event in events[459:]] == [
    'admission', 'component_recovery_authorized', 'reserve', 'temporary_directory',
    'started', 'monitor_gap_recovered', 'monitor_gap_recovered', 'finish',
]
admission, registration, reserve, temporary, started, gap1, gap2, finish = events[459:]
assert all(event.get('job_id') == JOB for event in (registration, reserve, temporary, started, gap1, gap2, finish))
assert registration['authorization'] == file_record(AUTH)
assert reserve['evidence']['authorization'] == file_record(AUTH)
assert reserve['evidence']['repair_validation']['sha256'] == '77b35580cb6dd283a75491d70123d80fbee36d1f0f86be96b76c12a7c55b7935'
assert reserve['evidence']['request']['bytes'] == 353132
assert finish['reservation'] == {'sequence': reserve['sequence'], 'event_sha256': reserve['event_sha256']}
assert finish['status'] == 'failed' and finish['failure_kind'] == 'worker_failure'
assert finish['error'] == 'RuntimeError: worker exited 1'
assert finish['cleanup_confirmed'] is True and finish['cleanup_uncertain'] is False
assert finish['surviving_pids'] == finish['helper_ownership'] == finish['helper_cleanup_errors'] == []
assert finish['result'] is finish['acceptance'] is None
assert finish['terminal_receipt'] is not None
assert started['pid'] == started['pgid']
assert all(event['expired_samples'] == 2 and 0 < event['gap_seconds'] < 15 for event in (gap1, gap2))
validate_binding(LOCAL, load(), file_record(AUTH), consumed=True)
try:
    validate_binding(LOCAL, load(), file_record(AUTH))
except ValueError as exc:
    refusal = str(exc)
    assert 'consumed S1 identity' in refusal
else:
    raise AssertionError('003 remained dispatchable')

totals = Ledger(LEDGER, load()).totals(events)
assert totals['gpu']['attempts'] == 33 and totals['gpu']['reserved_seconds'] == 0
worker = LOCAL / 'jobs' / JOB
worker_log = worker.with_suffix('.log')
failure = json.loads((worker / 'failure.json').read_text())
assert failure['reason'] == 'ValueError: progress byte capacity'
assert failure['first_result']['path'] == str((worker / 'first-result-qualification.json').resolve())
assert failure['failure_evidence']['path'].endswith('/calibration/camera0/frame50-failure-evidence.json')
assert file_record(failure['failure_evidence']['path']) == failure['failure_evidence']
assert file_record(worker_log)['bytes'] > 0

pid_query = subprocess.run(['ps', '-p', str(started['pid']), '-o', 'pid,ppid,pgid,stat,comm,args'],
                           capture_output=True, text=True, timeout=30)
assert pid_query.returncode == 1 and len(pid_query.stdout.splitlines()) == 1
apps_query = subprocess.run(['nvidia-smi', '--query-compute-apps=pid,process_name,used_memory',
                             '--format=csv,noheader'], capture_output=True, text=True, timeout=60)
assert apps_query.returncode == 0 and not apps_query.stdout.strip()

snapshot = HERE / 'post-dispatch-ledger-003.jsonl'
with snapshot.open('xb') as stream:
    stream.write(raw)
assert file_record(snapshot)['sha256'] == file_record(LEDGER)['sha256']
result = {
    'status': 'failed_after_worker_launch',
    'attempt_consumed': True,
    'redispatch_authorized': False,
    'prior_459_event_prefix_unchanged': True,
    'ledger': file_record(snapshot),
    'live_ledger': file_record(LEDGER),
    'events': len(events),
    'admission': admission,
    'authorization': registration,
    'reservation': reserve,
    'temporary_directory': temporary,
    'started': started,
    'monitor_gaps': [gap1, gap2],
    'finish': finish,
    'totals': totals,
    'validate_binding_consumed_passed': True,
    'unconsumed_binding_refusal': refusal,
    'worker_log': file_record(worker_log),
    'worker_failure': file_record(worker / 'failure.json'),
    'first_result_qualification': file_record(worker / 'first-result-qualification.json'),
    'first_frame_failure_evidence': file_record(failure['failure_evidence']['path']),
    'initial_runtime': file_record(worker / 'initial-runtime.json'),
    'worker_config': file_record(worker / 'config.json'),
    'terminal_receipt': file_record(finish['terminal_receipt']['path']),
    'host_observations': {
        'worker_pid_query': {'command': f'ps -p {started["pid"]} -o pid,ppid,pgid,stat,comm,args',
                             'exit_code': pid_query.returncode, 'rows': pid_query.stdout.splitlines()[1:]},
        'gpu_compute_query': {'command': 'nvidia-smi --query-compute-apps=pid,process_name,used_memory --format=csv,noheader',
                              'exit_code': apps_query.returncode, 'rows': apps_query.stdout.splitlines()},
    },
}
assert LEDGER.read_bytes() == raw
with (HERE / 'dispatch-outcome-003.json').open('x') as stream:
    json.dump(result, stream, indent=2)
    stream.write('\n')
print(json.dumps({key: result[key] for key in ('status', 'attempt_consumed', 'events', 'totals', 'unconsumed_binding_refusal')}, indent=2))

#!/usr/bin/env python3
"""Read-only host launch gate for the proposed fourth S1 recovery identity.

Usage (host, repository root):
    python docs/continuous-improvement/plan031-s1-recovery-20260919/requalification-070/s1-live-launch-gate-070.py

Prints GO or NO-GO with evidence. This script is strictly read-only: it
never appends to the ledger, never writes run artifacts, and never
admits a job. It exists so the operator can verify every precondition of
the proposed fourth dispatch without consuming an admission.
"""
from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / 'scripts'))
LOCAL = (ROOT / '.local/vipe-alternatives/plan031-20260913T032700Z').resolve()
AUTH = (ROOT / 'docs/research/vipe-alternatives/plan031-20260913T032700Z'
        / 's1-calibration-recovery-authorization-004.json').resolve()

LEDGER_SHA = 'd958d128e3b8c7a7263e0e07ba6d91e3c7ec5ae7ba855935895673fc69418f96'
LEDGER_BYTES = 363162
E1_PY = LOCAL / 'jobs/E1-setup-recovery-002/environment/bin/python'

failures: list[str] = []


def check(name: str, ok: bool, detail: str = '') -> None:
    print(f"  [{'ok' if ok else 'NO'}] {name}" + (f' — {detail}' if detail else ''))
    if not ok:
        failures.append(name)


print('== S1 fourth-identity host launch gate (read-only) ==')

import _thread
check('controller native joinable thread API', hasattr(_thread, 'start_joinable_thread'),
      f'Python {sys.version.split()[0]} — use .local/envs/stg-colmap/bin/python')

# 1. ledger byte check
b = (LOCAL / 'ledger.jsonl').read_bytes()
check('consumed 467-event ledger prefix byte-identical',
      hashlib.sha256(b[:LEDGER_BYTES]).hexdigest() == LEDGER_SHA and len(b) == LEDGER_BYTES,
      f'sha256={hashlib.sha256(b).hexdigest()[:12]}… bytes={len(b)}')

# 2. authorization document exists
check('authorization document present', AUTH.is_file(), str(AUTH))

# 3. E1 interpreter + import chain
ok = E1_PY.is_file()
check('E1 interpreter present', ok, str(E1_PY))
if ok:
    r = subprocess.run([str(E1_PY), '-c',
                        'import sys, torch, numpy; print(sys.version.split()[0], torch.__version__, numpy.__version__)'],
                       capture_output=True, text=True, timeout=120)
    check('E1 import chain (python/torch/numpy)', r.returncode == 0, r.stdout.strip() or r.stderr.strip()[:120])

# 4. S1 asset presence
sys.path.insert(0, str(ROOT))
from vipe_benchmark.config import load  # noqa: E402
from vipe_benchmark.files import file_record  # noqa: E402
from vipe_benchmark.s1_recovery import validate_binding  # noqa: E402
from vipe_benchmark.s1_progress import read_request_record, REQUEST_BYTES  # noqa: E402
from vipe_benchmark.s1_recovery import JOB, JOB_4  # noqa: E402
from vipe_benchmark.s1_validation_contract import validate_wrapper  # noqa: E402
from vipe_benchmark.ledger import Ledger  # noqa: E402
from vipe_benchmark.backends import AssetBundle  # noqa: E402

config = load()
e1res = json.loads((LOCAL / 'jobs/E1-setup-recovery-002/result.json').read_text())
asset_records = json.loads(Path(e1res['assets']['path']).read_text())
proposed = {}
try:
    AssetBundle('S1', asset_records)
    check('AssetBundle(S1) passes', True, f'{len(asset_records)} asset records')
except Exception as e:
    check('AssetBundle(S1) passes', False, f'{type(e).__name__}: {e}')

# 5. Qualification is checked even while approval is pending.
try:
    proposed = json.loads(AUTH.read_text())
    if file_record(proposed['repair_validation']['path']) != proposed['repair_validation']:
        raise ValueError('qualification record changed')
    validate_wrapper(json.loads(Path(proposed['repair_validation']['path']).read_text()),
                     proposed['semantic_amendment'], proposed['configuration'])
    check('current source qualification', True)
except Exception as e:
    check('current source qualification', False, f'{type(e).__name__}: {e}')
check('explicit one-attempt approval recorded',
      proposed.get('additional_attempt_approved') is True
      and proposed.get('authorization_context', {}).get('stage') == 'DO',
      proposed.get('authorization_context', {}).get('stage', 'missing'))

# Full binding validation also checks every event after the baseline and
# rejects any consumed attempt. An existing matching, unconsumed registration
# is safe: execute_s1_recovery reuses it without another admission.
try:
    if proposed.get('additional_attempt_approved') is True:
        document, request = validate_binding(LOCAL, config, file_record(AUTH))
        check('validate_binding (fail-closed contract)', True)
    else:
        check('validate_binding (fail-closed contract)', False, 'approval pending')
except Exception as e:
    check('validate_binding (fail-closed contract)', False, f'{type(e).__name__}: {e}')

# The exact frozen dispatch request must pass the same bounded read used in
# prelaunch and by the publisher. This check never reserves or writes a job.
try:
    reservations = [event for event in Ledger(LOCAL / 'ledger.jsonl', config).events()
                    if event['event'] == 'reserve' and event['job_id'] == JOB]
    if len(reservations) != 1:
        raise ValueError('unique frozen S1 reservation required')
    request_record = reservations[0]['evidence']['request']
    old_request = read_request_record(request_record)
    check('consumed frozen S1 request fits progress read bound', True,
          f'{request_record["bytes"]} <= {REQUEST_BYTES} bytes')
except Exception as e:
    check('consumed frozen S1 request fits progress read bound', False, f'{type(e).__name__}: {e}')

try:
    planned = dict(old_request, job_id=JOB_4, recovery_authorization=file_record(AUTH))
    planned_bytes = len((json.dumps(planned, indent=2, allow_nan=False) + '\n').encode())
    check('planned fourth request fits progress read bound', planned_bytes <= REQUEST_BYTES,
          f'{planned_bytes} <= {REQUEST_BYTES} bytes')
except Exception as e:
    check('planned fourth request fits progress read bound', False, f'{type(e).__name__}: {e}')

# Necessary latency check: the live helper allows at most one second for the
# entire resource request. Storage alone exceeding it guarantees failure.
# This does not certify helper startup/IPC latency or relax the live deadline.
from vipe_benchmark.budgets import budget_snapshot  # noqa: E402
try:
    started = time.monotonic()
    storage = budget_snapshot(LOCAL)
    elapsed = time.monotonic() - started
    check('storage sample below live 1 s resource deadline', elapsed < 1.,
          f'{elapsed:.3f} s; artifact_bytes={storage["artifact_bytes"]}')
except Exception as e:
    check('storage sample below live 1 s resource deadline', False, f'{type(e).__name__}: {e}')

# 6. GPU exclusivity evidence
# NOTE: the process table is not visible inside a bwrap sandbox, so the
# compute-apps query there is meaningless. Refuse to certify GO unless the
# process table is actually visible (i.e. run on the host).
sandboxed = not Path('/proc/1/comm').exists() or Path('/proc/1/comm').read_text().strip() != 'systemd'
nvidia = shutil.which('nvidia-smi')
if not nvidia:
    check('GPU compute-app report', False, 'nvidia-smi not found on host')
else:
    r = subprocess.run([nvidia, '--query-compute-apps=pid,process_name,used_memory',
                        '--format=csv,noheader'], capture_output=True, text=True, timeout=60)
    apps = [ln for ln in r.stdout.splitlines() if ln.strip()]
    if sandboxed:
        check('GPU exclusively free (no compute PIDs)', False,
              'process table invisible in this sandbox — run the gate on the host')
    else:
        check('GPU exclusively free (no compute PIDs)', r.returncode == 0 and not apps,
              'no compute apps' if not apps else f'{len(apps)} compute PID(s): ' + '; '.join(apps))
    r2 = subprocess.run([nvidia, '--query-gpu=name,memory.total,memory.used,utilization.gpu',
                         '--format=csv,noheader'], capture_output=True, text=True, timeout=60)
    print(f"       gpu: {r2.stdout.strip()}")

print()
if failures:
    print(f'NO-GO: {len(failures)} precondition(s) failed: {", ".join(failures)}')
    sys.exit(1)
print('GO: all preconditions hold. The single host dispatch may now run:')
print()
print('  bash scripts/run_s1_calibration_recovery_004.sh --run')

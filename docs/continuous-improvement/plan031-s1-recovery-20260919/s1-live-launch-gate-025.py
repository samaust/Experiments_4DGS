#!/usr/bin/env python3
"""S1-3 live S1 calibration recovery — read-only host launch gate.

Usage (host, repository root):
    python docs/continuous-improvement/plan031-s1-recovery-20260919/s1-live-launch-gate-025.py

Prints GO or NO-GO with evidence. This script is strictly read-only: it
never appends to the ledger, never writes run artifacts, and never
admits a job. It exists so the operator can verify every precondition of
the single host dispatch defined in plans/plan_064.md without consuming
the one tolerated 'admitted' admission.
"""
from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'scripts'))
LOCAL = (ROOT / '.local/vipe-alternatives/plan031-20260913T032700Z').resolve()
AUTH = (ROOT / 'docs/research/vipe-alternatives/plan031-20260913T032700Z'
        / 's1-calibration-recovery-authorization-001.json').resolve()

LEDGER_SHA = '2a0f66e38911b0ed029eb9dd0cf4bbd5da4a3b67abb577fbfe9ad67e6a888990'
LEDGER_BYTES = 332437
E1_PY = LOCAL / 'jobs/E1-setup-recovery-002/environment/bin/python'

failures: list[str] = []


def check(name: str, ok: bool, detail: str = '') -> None:
    print(f"  [{'ok' if ok else 'NO'}] {name}" + (f' — {detail}' if detail else ''))
    if not ok:
        failures.append(name)


print('== S1-3 host launch gate (read-only) ==')

# 1. ledger byte check
b = (LOCAL / 'ledger.jsonl').read_bytes()
check('ledger byte-identical (447-event baseline)',
      hashlib.sha256(b).hexdigest() == LEDGER_SHA and len(b) == LEDGER_BYTES,
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
from vipe_benchmark.backends import AssetBundle  # noqa: E402

config = load()
e1res = json.loads((LOCAL / 'jobs/E1-setup-recovery-002/result.json').read_text())
asset_records = json.loads(Path(e1res['assets']['path']).read_text())
try:
    AssetBundle('S1', asset_records)
    check('AssetBundle(S1) passes', True, f'{len(asset_records)} asset records')
except Exception as e:
    check('AssetBundle(S1) passes', False, f'{type(e).__name__}: {e}')

# 5. full binding validation (read-only part of host admission)
try:
    document, request = validate_binding(LOCAL, config, file_record(AUTH))
    check('validate_binding (fail-closed contract)', True)
except Exception as e:
    check('validate_binding (fail-closed contract)', False, f'{type(e).__name__}: {e}')

# 6. GPU exclusivity evidence
# NOTE: the process table is not visible inside a bwrap sandbox, so the
# compute-apps query there is meaningless. Refuse to certify GO unless the
# process table is actually visible (i.e. run on the host).
sandboxed = Path('/proc/1/comm').read_text().strip() in ('bwrap', 'unshare') if Path('/proc/1/comm').exists() else False
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
print('  PYTHONPATH=scripts python -B -m basketball_vipe_benchmark \\')
print('    --run-id plan031-20260913T032700Z component-recovery \\')
print('    --job S1-calibration-recovery-001 \\')
print('    --authorization docs/research/vipe-alternatives/plan031-20260913T032700Z/s1-calibration-recovery-authorization-001.json')

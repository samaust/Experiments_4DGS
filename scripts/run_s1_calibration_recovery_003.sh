#!/usr/bin/env bash
# Third S1 recovery identity. --check is read-only; --run needs new approval.
set -euo pipefail

if [[ $# != 1 || ( $1 != --check && $1 != --run ) ]]; then
    echo "Usage: bash scripts/run_s1_calibration_recovery_003.sh --check|--run" >&2
    exit 2
fi
mode=$1
cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.."

if [[ $(cat /proc/1/comm) != systemd ]]; then
    echo "NO-GO: host PID visibility required; in Codex use require_escalated." >&2
    exit 1
fi

recovery_python=.local/envs/stg-colmap/bin/python
"$recovery_python" -B -c 'import _thread; assert hasattr(_thread, "start_joinable_thread"), "S1 controller requires native joinable ownership thread"'
"$recovery_python" -B docs/continuous-improvement/plan031-s1-recovery-20260919/requalification-069/s1-live-launch-gate-069.py
if [[ $mode == --check ]]; then
    exit 0
fi

export PYTHONPATH="$PWD/scripts"
exec "$recovery_python" -B -m basketball_vipe_benchmark \
    --run-id plan031-20260913T032700Z component-recovery \
    --job S1-calibration-recovery-003 \
    --authorization docs/research/vipe-alternatives/plan031-20260913T032700Z/s1-calibration-recovery-authorization-003.json

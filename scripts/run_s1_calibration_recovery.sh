#!/usr/bin/env bash
# Fixed Plan064 recovery entry point. Run through Codex require_escalated.
set -euo pipefail

if [[ $# != 1 || ( $1 != --check && $1 != --run ) ]]; then
    echo "Usage: bash scripts/run_s1_calibration_recovery.sh --check|--run" >&2
    exit 2
fi
mode=$1
cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.."

# Match dispatch's host requirement BEFORE any admission can be written.
if [[ $(cat /proc/1/comm) != systemd ]]; then
    echo "NO-GO: host PID visibility required; in Codex use require_escalated." >&2
    exit 1
fi

recovery_python=.local/vipe-alternatives/plan031-20260913T032700Z/jobs/E1-setup-recovery-002/environment/bin/python
"$recovery_python" -B docs/continuous-improvement/plan031-s1-recovery-20260919/s1-live-launch-gate-025.py
if [[ $mode == --check ]]; then
    exit 0
fi

# Exactly one controller invocation. Never retry an admission or dispatch here.
export PYTHONPATH="$PWD/scripts"
exec "$recovery_python" -B -m basketball_vipe_benchmark \
    --run-id plan031-20260913T032700Z component-recovery \
    --job S1-calibration-recovery-001 \
    --authorization docs/research/vipe-alternatives/plan031-20260913T032700Z/s1-calibration-recovery-authorization-001.json

#!/usr/bin/env bash
# Run from any directory; never activate or clear an existing environment.
set -euo pipefail
GS_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
GS_WORK="$GS_ROOT/.local"
GS_ENV="${1:?Usage: bash scripts/setup-environment.sh METHOD}"
case "$GS_ENV" in
  stg-render|stg-colmap|hust|mango-render|nopo4d|atgs|freetimegs|roma|downloads) ;;
  *) printf 'Unknown environment: %s\n' "$GS_ENV" >&2; exit 2 ;;
esac
if [ "$#" -ne 1 ]; then
  printf '%s\n' 'Expected exactly one environment name.' >&2
  exit 2
fi
export UV_CACHE_DIR="$GS_WORK/cache/uv"
export UV_PYTHON_INSTALL_DIR="$GS_WORK/tools/python"
export UV_PYTHON_DOWNLOADS=never
export HF_HOME="$GS_WORK/cache/huggingface"
export TORCH_HOME="$GS_WORK/cache/torch"
export XDG_CACHE_HOME="$GS_WORK/cache/xdg"
mkdir -p "$GS_WORK/envs" "$GS_WORK/runs" "$UV_CACHE_DIR" "$HF_HOME" "$TORCH_HOME" "$XDG_CACHE_HOME"
GS_LOG="$(mktemp -d "$GS_WORK/runs/environment-$GS_ENV-XXXXXXXX")"
exec > >(tee "$GS_LOG/setup.log") 2>&1
trap 'printf "Setup failed at line %s; logs: %s\n" "$LINENO" "$GS_LOG" >&2' ERR
printf 'Environment: %s\nLogs: %s\n' "$GS_ENV" "$GS_LOG"
uv --version
GS_PY="$GS_WORK/envs/$GS_ENV/bin/python"
if [ ! -e "$GS_WORK/envs/$GS_ENV" ]; then
  uv venv --python /usr/bin/python3.14 "$GS_WORK/envs/$GS_ENV"
fi
"$GS_PY" -c 'import sys,sysconfig; print(sys.executable,sys.version); assert sys.version_info[:2] == (3,14); assert not sysconfig.get_config_var("Py_GIL_DISABLED")'
GS_OPTIONS=()
GS_INPUTS=("$GS_ROOT/environments/$GS_ENV.in")
if [ "$GS_ENV" != downloads ]; then
  GS_OPTIONS=(--torch-backend cu130 --constraint "$GS_ROOT/environments/constraints-cu130.txt")
  GS_INPUTS+=("$GS_ROOT/environments/build.in")
  uv pip install --python "$GS_PY" "${GS_OPTIONS[@]}" -r "$GS_ROOT/environments/base-cu130.in"
fi
# Resolve build tools together with the candidate dependencies before installing.
uv pip compile --quiet --python "$GS_PY" "${GS_OPTIONS[@]}" "${GS_INPUTS[@]}" \
  --output-file "$GS_LOG/candidate.txt"
uv pip install --python "$GS_PY" "${GS_OPTIONS[@]}" -r "$GS_LOG/candidate.txt"
uv pip check --python "$GS_PY"
uv pip freeze --python "$GS_PY" > "$GS_LOG/installed.txt"
if [ "$GS_ENV" = downloads ]; then
  "$GS_WORK/envs/downloads/bin/hf" --help
else
  "$GS_PY" "$GS_ROOT/scripts/verify-environment.py" --method "$GS_ENV"
fi
printf 'Candidate dependencies installed and checked. Logs: %s\n' "$GS_LOG"
printf '%s\n' 'Method source builds, GPU kernels and checkpoint rendering are separate checks.'

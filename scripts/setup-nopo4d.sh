#!/usr/bin/env bash
# Install the pinned NoPo4D inference sources on the shared Python 3.14 stack.
set -euo pipefail
GS_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
GS_WORK="$GS_ROOT/.local"
export UV_CACHE_DIR="$GS_WORK/cache/uv"
export HF_HOME="$GS_WORK/cache/huggingface"
export TORCH_HOME="$GS_WORK/cache/torch"
export XDG_CACHE_HOME="$GS_WORK/cache/xdg"
export MPLCONFIGDIR="$GS_WORK/cache/matplotlib"
mkdir -p "$UV_CACHE_DIR" "$HF_HOME" "$TORCH_HOME" "$XDG_CACHE_HOME" "$GS_WORK/runs"
mkdir -p "$MPLCONFIGDIR"
GS_LOG="$(mktemp -d "$GS_WORK/runs/nopo4d-install-XXXXXXXX")"
exec > >(tee "$GS_LOG/setup.log") 2>&1
echo "Installation log: $GS_LOG/setup.log"
trap 'echo "NoPo4D setup failed at line $LINENO; see $GS_LOG/setup.log" >&2' ERR

GS_SOURCE="$GS_WORK/NoPo4D"
GS_REV=cb54c9349792d474aa541274842e0fadf1d807c7
if [ ! -e "$GS_SOURCE" ]; then
  git clone https://github.com/bralani/NoPo4D.git "$GS_SOURCE"
fi
if [ "$(git -C "$GS_SOURCE" rev-parse HEAD)" != "$GS_REV" ]; then
  if [ -n "$(git -C "$GS_SOURCE" status --porcelain)" ]; then
    echo "Existing NoPo4D revision differs and has local changes; inspect it before switching revisions." >&2
    exit 1
  fi
  git -C "$GS_SOURCE" checkout --detach "$GS_REV"
fi
git -C "$GS_SOURCE" submodule update --init --recursive
git -C "$GS_SOURCE" rev-parse HEAD
git -C "$GS_SOURCE" submodule status --recursive
GS_BACKBONE="$GS_SOURCE/src/model/encoder/backbone/Depth-Anything-3"
test "$(git -C "$GS_BACKBONE" rev-parse HEAD)" = 41736238f5bced4debf3f2a12375d2466874866d

apply_once() {
  local checkout="$1" patch="$2"
  if git -C "$checkout" apply --reverse --check "$patch" 2>/dev/null; then
    echo "Already applied: $patch"
  else
    git -C "$checkout" apply --check "$patch"
    git -C "$checkout" apply "$patch"
  fi
}
apply_once "$GS_SOURCE" "$GS_ROOT/patches/nopo4d-python314.patch"
apply_once "$GS_BACKBONE" "$GS_ROOT/patches/da3-python314.patch"

GS_PY="$GS_WORK/envs/nopo4d/bin/python"
if [ ! -x "$GS_PY" ]; then
  bash "$GS_ROOT/scripts/setup-environment.sh" nopo4d
fi
"$GS_PY" -c 'import sys; assert sys.version_info[:2] == (3, 14), sys.version'
uv pip install --python "$GS_PY" --torch-backend cu130 \
  --constraint "$GS_ROOT/environments/constraints-cu130.txt" \
  -e "$GS_SOURCE" -e "$GS_BACKBONE"
uv pip check --python "$GS_PY"
"$GS_PY" -c 'import torch, xformers, gsplat; print(torch.__version__, xformers.__version__, gsplat.__version__)'
"$GS_PY" "$GS_SOURCE/src/inference.py" --help
"$GS_PY" "$GS_ROOT/scripts/verify-nopo4d.py"
uv pip freeze --python "$GS_PY" > "$GS_LOG/installed.txt"

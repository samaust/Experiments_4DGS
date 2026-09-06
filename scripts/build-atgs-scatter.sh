#!/usr/bin/env bash
# Offline torch-scatter 2.1.2 build, including CUDA even without device access.
set -euo pipefail
ATGS_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
ATGS_SCATTER="$ATGS_ROOT/.local/pytorch-scatter-atgs"
ATGS_PY="$ATGS_ROOT/.local/envs/atgs/bin/python"
test "$(git -C "$ATGS_SCATTER" rev-parse HEAD)" = 140d3ad677aae615767412873b90982cbf97d35d
export UV_CACHE_DIR="$ATGS_ROOT/.local/cache/uv"
export CUDA_HOME=/usr/local/cuda-13.0
export PATH="$CUDA_HOME/bin:$PATH"
export TORCH_CUDA_ARCH_LIST=8.9
export FORCE_CUDA=1
export CC=/usr/bin/gcc
export CXX=/usr/bin/g++
ATGS_LOG="$(mktemp -d "$ATGS_ROOT/.local/runs/atgs-scatter-build-XXXXXXXX")"
exec > >(tee "$ATGS_LOG/build.log") 2>&1
trap 'printf "Build failed at line %s; log directory: %s\n" "$LINENO" "$ATGS_LOG" >&2' ERR
printf 'Build log: %s\n' "$ATGS_LOG"
"$CUDA_HOME/bin/nvcc" --version
uv pip install --offline --no-deps --no-build-isolation --python "$ATGS_PY" "$ATGS_SCATTER"
uv pip check --python "$ATGS_PY"
printf '%s\n' 'Build completed; CUDA and full ATGS import validation remain separate gates.'

#!/usr/bin/env bash
# Build only the pinned tiny-cuda-nn dependency; no downloads or GPU execution.
set -euo pipefail
ATGS_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
ATGS_SRC="$ATGS_ROOT/.local/tiny-cuda-nn-atgs"
ATGS_PY="$ATGS_ROOT/.local/envs/atgs/bin/python"
test "$(git -C "$ATGS_SRC" rev-parse HEAD)" = 32507f059d7abc8c13f5df81ea9597b70923ee44
test "$(git -C "$ATGS_SRC/dependencies/cutlass" rev-parse HEAD)" = 1eb6355182a5124639ce9d3ff165732a94ed9a70
test "$(git -C "$ATGS_SRC/dependencies/fmt" rev-parse HEAD)" = b0c8263cb26ea178d3a5df1b984e1a61ef578950
git -C "$ATGS_SRC" apply --reverse --check "$ATGS_ROOT/patches/tcnn17-python314-cu130.patch"
export UV_CACHE_DIR="$ATGS_ROOT/.local/cache/uv"
export CUDA_HOME=/usr/local/cuda-13.0
export PATH="$CUDA_HOME/bin:$PATH"
export TCNN_CUDA_ARCHITECTURES=89
export TORCH_CUDA_ARCH_LIST=8.9
export MAX_JOBS=2
export CC=/usr/bin/gcc
export CXX=/usr/bin/g++
ATGS_LOG="$(mktemp -d "$ATGS_ROOT/.local/runs/atgs-tcnn-build-XXXXXXXX")"
exec > >(tee "$ATGS_LOG/build.log") 2>&1
trap 'printf "Build failed at line %s; log directory: %s\n" "$LINENO" "$ATGS_LOG" >&2' ERR
printf 'Build log: %s\n' "$ATGS_LOG"
"$CUDA_HOME/bin/nvcc" --version
uv pip install --offline --no-deps --no-build-isolation --python "$ATGS_PY" "$ATGS_SRC/bindings/torch"
uv pip check --python "$ATGS_PY"
printf '%s\n' 'Build completed; GPU forward/backward validation remains a separate gate.'

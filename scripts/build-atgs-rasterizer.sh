#!/usr/bin/env bash
# Build recovered native dependencies offline; no GPU execution or downloads.
set -euo pipefail
ATGS_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
ATGS_NATIVE="$ATGS_ROOT/.local/LocalDyGS"
ATGS_PY="$ATGS_ROOT/.local/envs/atgs/bin/python"
test "$(git -C "$ATGS_NATIVE" rev-parse HEAD)" = 39dacdcd8ef6d2b93824df79041713b4a29fb828
git -C "$ATGS_NATIVE" apply --reverse --check "$ATGS_ROOT/patches/localdygs-cstdint.patch"
export UV_CACHE_DIR="$ATGS_ROOT/.local/cache/uv"
export CUDA_HOME=/usr/local/cuda-13.0
export PATH="$CUDA_HOME/bin:$PATH"
export TORCH_CUDA_ARCH_LIST=8.9
export MAX_JOBS=2
export CC=/usr/bin/gcc
export CXX=/usr/bin/g++
ATGS_LOG="$(mktemp -d "$ATGS_ROOT/.local/runs/atgs-rasterizer-build-XXXXXXXX")"
exec > >(tee "$ATGS_LOG/build.log") 2>&1
trap 'printf "Build failed at line %s; log directory: %s\n" "$LINENO" "$ATGS_LOG" >&2' ERR
printf 'Build log: %s\n' "$ATGS_LOG"
"$CUDA_HOME/bin/nvcc" --version
uv pip install --offline --no-deps --no-build-isolation --python "$ATGS_PY" \
    "$ATGS_NATIVE/submodules/diff-gaussian-rasterization" \
    "$ATGS_NATIVE/submodules/simple-knn"
uv pip check --python "$ATGS_PY"
printf '%s\n' 'Build completed; CUDA validation remains a separate gate.'

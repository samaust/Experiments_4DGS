#!/usr/bin/env bash
# Build locked reproduction dependencies offline; GPU execution is a later gate.
set -euo pipefail
FTGS_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
FTGS_SPLAT="$FTGS_ROOT/.local/gsplat-freetimegs"
FTGS_SSIM="$FTGS_ROOT/.local/fused-ssim-freetimegs"
FTGS_PY="$FTGS_ROOT/.local/envs/freetimegs/bin/python"
test "$(git -C "$FTGS_SPLAT" rev-parse HEAD)" = b60e917c95afc449c5be33a634f1f457e116ff5e
test "$(git -C "$FTGS_SPLAT/gsplat/cuda/csrc/third_party/glm" rev-parse HEAD)" = 33b4a621a697a305bc3a7610d290677b96beb181
test "$(git -C "$FTGS_SSIM" rev-parse HEAD)" = 1272e21a282342e89537159e4bad508b19b34157
export UV_CACHE_DIR="$FTGS_ROOT/.local/cache/uv"
export CUDA_HOME=/usr/local/cuda-13.0
export PATH="$CUDA_HOME/bin:$PATH"
export TORCH_CUDA_ARCH_LIST=8.9
export MAX_JOBS=2
export CC=/usr/bin/gcc
export CXX=/usr/bin/g++
FTGS_LOG="$(mktemp -d "$FTGS_ROOT/.local/runs/freetimegs-native-build-XXXXXXXX")"
exec > >(tee "$FTGS_LOG/build.log") 2>&1
trap 'printf "Build failed at line %s; log directory: %s\n" "$LINENO" "$FTGS_LOG" >&2' ERR
printf 'Build log: %s\n' "$FTGS_LOG"
"$CUDA_HOME/bin/nvcc" --version
uv pip install --offline --no-deps --no-build-isolation --python "$FTGS_PY" "$FTGS_SPLAT" "$FTGS_SSIM"
uv pip check --python "$FTGS_PY"
printf '%s\n' 'Build completed; native imports, GPU kernels and training remain separate gates.'

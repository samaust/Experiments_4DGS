#!/usr/bin/env bash
# Build the isolated joint FreeTimeGS/RoMa runtime offline (#34, research-use).
# Pins: FreeTimeGS env freeze minus GUI OpenCV, plus RoMa matcher closure with
# headless OpenCV only; gsplat/fused-ssim rebuilt from their pinned checkouts.
set -euo pipefail
REPO=/home/auss/git_repos/samaust/Experiments_4DGS
HERE="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
ENV="$REPO/.local/envs/plan069-joint-native-001"
test ! -e "$ENV"
test "$(git -C "$REPO/.local/gsplat-freetimegs" rev-parse HEAD)" = b60e917c95afc449c5be33a634f1f457e116ff5e
test "$(git -C "$REPO/.local/fused-ssim-freetimegs" rev-parse HEAD)" = 1272e21a282342e89537159e4bad508b19b34157
export UV_CACHE_DIR="$REPO/.local/cache/uv"
export CUDA_HOME=/usr/local/cuda-13.0 PATH="/usr/local/cuda-13.0/bin:$PATH"
export TORCH_CUDA_ARCH_LIST=8.9 MAX_JOBS=6 CC=/usr/bin/gcc CXX=/usr/bin/g++
start=$(date +%s.%N)
uv venv --python /usr/bin/python3.14 "$ENV"
# Attempt 001 found triton 3.7.1 absent from the cache; fetch only cache misses.
cache_before=$(du -sb "$UV_CACHE_DIR" | cut -f1)
uv pip install --python "$ENV/bin/python" --no-deps \
  --index-url https://download.pytorch.org/whl/cu130 --extra-index-url https://pypi.org/simple \
  --index-strategy unsafe-best-match -r "$HERE/joint-pins.txt"
uv pip install --python "$ENV/bin/python" --offline --no-deps --no-build-isolation \
  "$REPO/.local/gsplat-freetimegs" "$REPO/.local/fused-ssim-freetimegs"
uv pip check --python "$ENV/bin/python"
cache_after=$(du -sb "$UV_CACHE_DIR" | cut -f1)
echo "uv cache growth bytes: $((cache_after-cache_before))"
end=$(date +%s.%N)
python3 -c "import json,sys;json.dump(dict(schema='plan069-joint-runtime-setup/v1',status='complete',environment='$ENV',elapsed_seconds=float(sys.argv[2])-float(sys.argv[1]),cache_growth_bytes=int(sys.argv[3])),open('$HERE/setup-receipt.json','w'),indent=2)" "$start" "$end" "$((cache_after-cache_before))"

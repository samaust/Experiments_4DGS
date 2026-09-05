  # Update the repository for Python 3.14 and PyTorch cu130

  ## 1. Establish the environment policy

  Make the documented target:

  - Standard CPython 3.14, using the installed /usr/bin/python3.14.
  - uv for virtual environments and package installation.
  - PyTorch 2.13.0 with torchvision 0.28.0 from the official cu130 index.
  - System CUDA toolkit at /usr/local/cuda-13.0.
  - Separate environments per research implementation beneath .local/envs/.

  Treat cu130 as the selected prebuilt PyTorch distribution. Building PyTorch itself from source is outside
  this update.

  Do not introduce automatic fallbacks to Conda, older Python, or another CUDA build. Record incompatible
  methods as requiring adaptation.

  ## 2. Replace environment instructions throughout the guides

  Add a shared environment guide and link to it from the README, pretrained experiments, training, and
  rendering guides.

  Replace:

  - Miniforge installation and Conda activation commands.
  - Conda package caches and environment inventories.
  - CUDA 11.6/12.1 toolkit installations and Conda compiler paths.
  - Legacy Torch and xFormers installation pins.
  - The CUDA 11.6 8.6+PTX extension setting.

  Use commands following this pattern:

  export GS_WORK="$(git rev-parse --show-toplevel)/.local"
  export UV_CACHE_DIR="$GS_WORK/cache/uv"

  uv venv --python /usr/bin/python3.14 \
    "$GS_WORK/envs/stg-render"

  uv pip install \
    --python "$GS_WORK/envs/stg-render/bin/python" \
    --torch-backend cu130 \
    torch==2.13.0 torchvision==0.28.0

  export CUDA_HOME=/usr/local/cuda-13.0
  export PATH="$CUDA_HOME/bin:$PATH"
  export TORCH_CUDA_ARCH_LIST=8.9

  Use explicit environment interpreter paths in execution commands. Give each method a separate extension-
  build cache.

  Document COLMAP as a system executable with a recorded version and verified CLI compatibility. A Python
  virtual environment does not replace Conda’s installation of native tools.

  Retain upstream historical stacks as research facts, clearly separated from current installation
  instructions. Preserve previous plans as historical records.

  ## 3. Document compatibility work by method

  Preserve the rendering-first experiment sequence, but distinguish available previews from native pipelines
  awaiting validation.

   Component                      Required update
  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   splaTV and metadata helpers    Use Python 3.14 for serving/testing; browser playback remains independent
                                  of Torch
  ─────────────────────────────  ─────────────────────────────────────────────────────────────────────────────
   STG and HUST                   Audit MMCV configuration usage, old scientific-library APIs, checkpoint
                                  loading, and custom CUDA extensions
  ─────────────────────────────  ─────────────────────────────────────────────────────────────────────────────
   Mango-GS                       Verify PyTorch3D and rasterizer builds against Python 3.14, Torch 2.13, and
                                  CUDA 13
  ─────────────────────────────  ─────────────────────────────────────────────────────────────────────────────
   NoPo4D and its backbone        Resolve compatible xFormers, gsplat, and other compiled dependencies
                                  without changing the selected Torch stack

  For each method, record dependency resolution, imports, extension compilation, and actual rendering as
  separate validation stages.

  Where adaptation is necessary, document the specific blocker and proposed patch. Updating package-version
  text must not imply that the method has been ported.

  ## 4. Add reproducible dependency specifications

  Introduce tracked base constraints and separate dependency specifications per method.

  - Pin the Torch/torchvision pair and explicitly select cu130.
  - Remove unnecessary dependencies such as torchaudio unless an implementation imports them.
  - Resolve application dependencies under the base constraints so they cannot silently replace Torch.
  - Record source revisions for dependencies installed from Git.
  - Generate resolved dependency files only after successful resolution.
  - Document extension build dependencies and any justified use of disabled build isolation.

  Update the experiment template to record uv version, Python executable/version, dependency specification,
  Torch build, compiler, and extension revisions.

  ## 5. Validate the content update

  For the repository changes:

  - Check links and shell syntax.
  - Confirm active instructions contain no Conda installation, activation, or execution commands.
  - Run existing Python tests with Python 3.14 and retain the JavaScript tests.
  - Check consistent environment names, interpreter paths, and cache locations.

  For subsequent environment execution:

  - Verify Python 3.14 and torch.version.cuda == "13.0".
  - Check GPU access and a synchronized CUDA tensor operation.
  - Resolve and import each method’s dependencies.
  - Compile its extensions and render a real checkpoint.
  - Mark native rendering supported only after that final check.

  The immediate implementation updates documentation and environment specifications. Research-code ports and
  GPU experiment results remain explicitly identified follow-up work where compatibility is not yet
  established.
  </proposed_plan>
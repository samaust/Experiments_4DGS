  # Rendering-first 4DGS experiments

  ## Summary

  Create docs/pretrained-experiments.md: a step-by-step guide for experiencing existing 4DGS models before
  choosing a training method.

  The sequence will be:

  1. Explore a bundled scene in splaTV.
  2. Inspect a downloaded SpacetimeGaussians lite checkpoint.
  3. Compare its browser rendering with the original CUDA renderer.
  4. Render a downloaded Mango-GS checkpoint of the same scene.
  5. Run NoPo4D reconstruction inference on its bundled examples.
  6. Record findings and decide which method merits training.

  The immediate deliverable is the guide, repository layout changes, and a reproducible viewer patch.
  Environment installation, downloads, and GPU experiments are subsequent execution steps.

  ## Repository organization

  Update the README and existing guides to make this repository the experiment workspace and put pretrained
  rendering first. Preserve the distinction between planned procedures and measured results.

  Use this layout:

  .local/                   # Ignored runtime workspace
    splaTV/                 # Upstream checkouts
    SpacetimeGaussians/
    Mango-GS/
    NoPo4D/
    envs/                   # Separate environments
    tools/                  # Local environment manager/toolchains
    cache/                  # Package, model, and extension caches
    downloads/              # Original archives
    data/                   # Original and prepared inputs
    weights/                # Downloaded checkpoints
    runs/                   # Images, videos, logs, measurements
  patches/                  # Tracked upstream modifications
  docs/experiments/         # Tracked findings and reproduction notes

  Add /.local/ to .gitignore, preserving prompts/. Keep our future implementation, environment
  specifications, configurations, and patches tracked.

  Start guide commands from the repository root:

  GS_ROOT="$(git rev-parse --show-toplevel)"
  export GS_WORK="$GS_ROOT/.local"

  mkdir -p "$GS_WORK"/{envs,tools,cache,downloads,data,weights,runs}

  export HF_HOME="$GS_WORK/cache/huggingface"
  export TORCH_HOME="$GS_WORK/cache/torch"
  export TORCH_EXTENSIONS_DIR="$GS_WORK/cache/torch_extensions"
  export PIP_CACHE_DIR="$GS_WORK/cache/pip"
  export CONDA_PKGS_DIRS="$GS_WORK/cache/conda/pkgs"

  git check-ignore .local/weights/example.ply
  df -h "$GS_ROOT"

  Use environments installed by prefix beneath .local/envs. Document a local environment-manager
  installation because conda was not available on the inspected PATH.

  ## Step-by-step experiment guide

  Every experiment will explain its purpose, prerequisites, download sources, commands, expected files,
  viewing procedure, failure checks, and completion criteria. Record full source revisions and model
  revisions; distinguish source-checked commands from locally tested commands.

  ### 1. View the bundled splaTV scene

  This provides the first interactive experience without installing a CUDA research environment.

  git clone https://github.com/antimatter15/splaTV.git "$GS_WORK/splaTV"
  git -C "$GS_WORK/splaTV" checkout --detach 8b313fe
  git -C "$GS_WORK/splaTV" rev-parse HEAD

  test -s "$GS_WORK/splaTV/model.splatv"

  python3 -m http.server 8000 \
    --bind 127.0.0.1 \
    --directory "$GS_WORK/splaTV"

  Open http://127.0.0.1:8000/, explore the camera controls, and confirm browser hardware acceleration. The
  repository includes its default scene. splaTV source

  Supply a tracked patch adding:

  - Play/pause and a normalized-time slider.
  - Constant-speed looping with an editable cycle duration.
  - A numeric time display and restart control.
  - Camera movement while time remains paused.

  Start paused at time zero. Scrubbing pauses playback; resuming continues from the selected time. Label
  cycle duration as a viewing setting unless capture timing is known. Prevent timeline controls from
  triggering camera shortcuts.

  Apply the patch with git apply --check followed by git apply. Preserve upstream rendering and conversion
  behavior.

  ### 2. Inspect a downloaded STG lite model

  Use n3d_sear_steak_lite_allcam.zip, published with the original implementation. It is approximately 16.1
  MB. Published checkpoint

  The guide will provide commands to download that individual archive, record its checksum, inspect its
  contents, and extract it into a dedicated weights directory.

  Load its matching camera JSON before importing the lite PLY into splaTV. Save the converted .splatv
  under .local, retain the original checkpoint, and reload the conversion from an explicit loopback URL.

  Inspect:

  - Fixed-camera animation.
  - Frozen-time camera movement.
  - Beginning, middle, and end states.
  - Fine edges, fast motion, transparency, background stability, and newly exposed surfaces.

  Treat this as a preview of the browser representation. Its rendering differences will be assessed in the
  next experiment.

  ### 3. Render the STG checkpoint with its original renderer

  Install the isolated STG environment and matching compiler using the reference stack documented in the
  repository. Explicitly select that toolchain for extension builds: the installed system compiler is CUDA
  13.0.

  Obtain the matching sear_steak input and prepare the metadata required by STG’s loader. Explain why a
  downloaded checkpoint can still require dataset files for rendering.

  The guide will resolve the archive’s actual model path, saved iteration, configuration, and temporal
  window before supplying the complete command using:

  python test.py
    --source_path <prepared sear_steak colmap directory>
    --model_path <downloaded checkpoint directory>
    --configpath configs/n3d_lite/sear_steak.json
    --eval --skip_train --valloader colmapvalid

  Use the published testing entry point without running training. STG testing instructions

  Compare original-renderer PNGs with browser views at matched camera poses, times, resolution, and
  background. Document any camera-import corrections required for alignment.

  The checkpoint was trained using all cameras. Label comparisons against dataset images as reconstruction
  inspection, not held-out evaluation.

  ### 4. Render Mango-GS on the same scene

  Download only the released sear_steak_mango_node checkpoint bundle. Keep its configuration, Gaussian PLY,
  and deformation weights together. This scene is available in the published model repository. Mango-GS
  checkpoints

  Create a separate Mango-GS environment, using its documented PyTorch 2.4.1/CUDA 12.1 baseline as the
  starting point. Prepare the shared source capture in Mango-GS’s own loader layout.

  Provide complete commands for the upstream single-frame preview and subsequent image/video rendering.
  These entry points support downloaded checkpoints. Mango-GS rendering instructions

  Begin with one frame before rendering a sequence. Compare overlapping physical times and camera views with
  STG, recording differences in resolution, temporal coverage, and training setup. Preserve PNGs for judging
  detail before video compression.

  ### 5. Run pretrained NoPo4D inference

  Create a separate environment with its required backbone and compatible CUDA dependencies. Keep downloaded
  model weights and build caches beneath .local.

  Start with the upstream example:

  cd "$GS_WORK/NoPo4D"

  python src/inference.py \
    --image_dir assets/examples \
    --num_cameras 4 \
    --output_dir "$GS_WORK/runs/nopo4d-example" \
    --render_timestamps 10

  The bundled input contains four cameras and four frames. The command renders ten timestamps per predicted
  camera, producing 40 images in camera-major order. Inference source

  Explain how to inspect and encode each camera’s sequence separately. Include a smaller render-timestamp
  setting for diagnosing rendering-memory failures, while explaining that it does not reduce encoder input
  size.

  Label this experiment as reconstruction followed by input-camera replay. Custom novel-view paths and
  portable Gaussian export remain follow-up integrations; the stock CLI does not provide them.

  ### 6. Choose the first training candidate

  Provide a tracked experiment-note template covering:

  - Model/source revisions and exact commands.
  - Installation effort and failures.
  - Appearance, motion stability, and viewpoint limitations.
  - Downloaded and installed sizes.
  - Peak GPU memory and measurement method.
  - Render timing, resolution, and timing boundaries.
  - Original-versus-browser differences.
  - Verdict: investigate training, investigate rendering further, or defer.

  Keep browser frame rate, CUDA rendering throughput, reconstruction time, and video playback rate separate.

  Choose training only after reviewing these observations. Preserve the existing HUST synthetic training
  guide as a later option.

  ## Validation and assumptions

  - Check documentation links, shell syntax, workspace paths, ignore rules, and viewer patch applicability.
  - Verify that commands never initiate training during these experiments.
  - Test viewer pause, scrub, resume, loop, and frozen-time camera movement; verify local playback after
    downloads.

  - Require a real CUDA render before marking an environment working.
  - Confirm that each checkpoint reloads and outputs visibly different temporal states.
  - Record failures as results; do not replace missing runtime evidence with upstream claims.

  Assume Ubuntu 24.04, an RTX 4090, and the confirmed 591 GB free space. GPU access remains an execution
  prerequisite: the sandbox’s driver query failed, and host visibility was not established. Browser
  inspection can proceed independently.

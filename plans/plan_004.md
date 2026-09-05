  # Compare Native STG contenders using SelfCap and VRU Basketball

  ## Summary

  Add and execute experiments for STG Full, FreeTimeGS, MoE-GS, ATGS, and FreeTimeGS++, alongside a newly
  trained STG-lite baseline.

  Replace sear_steak with SelfCap dance1 for detailed appearance and motion inspection. Retain VRU
  Basketball DG for larger motion. Use released checkpoints where suitable and train matched scenes when
  necessary, within the agreed 24-hour total training budget.

  Deliver reproducible commands, rendered artifacts, measurements, visual analysis, and comparison reports.

  ## Datasets and evaluation protocol

   Profile              Frames                      Evaluation resolution        Held-out cameras
  ━━━━━━━━━━━━━━━━━━━  ━━━━━━━━━━━━━━━━━━━━━━━━━━  ━━━━━━━━━━━━━━━━━━━━━━━━━━━  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   SelfCap dance1       [4120, 4180) — 60 frames    Undistort, then              0015; train on remaining
                                                    downsample by 0.5 using      cameras
                                                    area interpolation;
                                                    approximately 1080p
  ───────────────────  ──────────────────────────  ───────────────────────────  ────────────────────────────
   VRU Basketball DG    [0, 50) — 50 frames         960×540                      0, 10, 20, 30; train on
                                                                                 remaining cameras

  - Obtain SelfCap from the official Hugging Face release. dance1 is in hair-release.tar.gz, with the
    separate calibration archive. Follow its documented FreeTimeGS split and synchronization corrections.

  - The user has accepted the access conditions. Check existing download credentials; browser acceptance may
    still require authenticating the local download client.

  - Before training, inspect original-resolution start/middle/end frames from the test camera and four
    distributed training cameras. Record exposure, motion blur, compression, calibration, and
    synchronization observations.

  - If the selected window has unusable images or unresolved synchronization, finish unaffected work and
    report the problem before substituting another scene.

  - Save a shared manifest containing source revisions, hashes, camera calibration, frame IDs, source frame
    rate, synchronization offsets, undistortion, resizing, and normalized-time mappings.

  - Use identical processed inputs across methods. Generate initialization geometry from training views
    only; audit supplied point clouds before using them to prevent held-out image leakage.

  ## Experiments and implementation

  Create experiments 006–010, each covering both scenes:

   ID     Method          Configuration
  ━━━━━  ━━━━━━━━━━━━━━  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   006    STG Full        Original full representation, appearance decoder, and native renderer
  ─────  ──────────────  ─────────────────────────────────────────────────────────────────────────────
   007    FreeTimeGS      Author implementation where available; identify any reproduction explicitly
  ─────  ──────────────  ─────────────────────────────────────────────────────────────────────────────
   008    MoE-GS          Four experts plus router, recording the exact expert implementations
  ─────  ──────────────  ─────────────────────────────────────────────────────────────────────────────
   009    ATGS            Hash encoder with the selected short frame window
  ─────  ──────────────  ─────────────────────────────────────────────────────────────────────────────
   010    FreeTimeGS++    Fixed B configuration for both scenes, without scene-wise selection

  Train STG Lite on both matched profiles. Preserve the earlier sear_steak outputs as historical evidence.

  - Audit and pin source, submodules, checkpoints, configurations, and licenses. Prefer complete released
    models for preliminary previews; use them in quantitative comparisons only when training splits and
    frame coverage match.

  - When checkpoints are missing or unmatched, train the specified profiles. If essential implementation
    components are unavailable, record the blocker and continue other experiments; a new implementation from
    the paper is outside scope.

  - Follow the existing uv, Python 3.14, Torch/cu130 environment policy. Add isolated environments and
    tracked compatibility patches. Resolve STG training and preprocessing dependencies before training.

  - Extend scripts/render-stg-preview.py with explicit full/lite support and decoder validation while
    preserving existing lite behavior.

  - Add thin method adapters using the shared scene manifest. Export lossless PNGs, camera/time metadata,
    checkpoint provenance, and timing records.

  - MoE-GS’s STG expert uses a modified appearance representation. Validate its expected format rather than
    substituting the original STG Full model.

  - Extend docs/pretrained-experiments.md with preview procedures and experiment links, retaining section 6.
    Put training commands in the training guide.

  - Reuse existing measurement, inventory, contact-sheet, and sequence-analysis helpers. Store new assets
    and outputs in separate .local/ directories.

  ## Training budget and execution

  Run GPU experiments sequentially.

  - Allocate four hours per contender, split into two hours per scene.
  - Allocate four hours to the matched STG-lite baseline, also split equally.
  - Include failed training attempts and retries in these limits.
  - For MoE-GS, allocate up to 25 minutes per expert and 20 minutes for router training per scene.
  - Use one fixed seed and upstream training defaults unless adaptation to the shared profile requires
    changes. Record every change.

  - Save resumable checkpoints periodically and before reaching the limit. Evaluate the final completed
    checkpoint and identify incomplete training.

  - Track downloads, builds, preprocessing, and evaluation separately. Do not automatically redistribute
    unused training time or exceed 24 hours.

  - Use memory-saving changes that preserve the evaluation profile first. If a method cannot run within
    available GPU memory, record that failure rather than silently lowering its resolution.

  ## Evidence, validation, and acceptance

  For every successful method/scene combination:

  - Render every timestamp from every held-out camera.
  - Produce a 20-pose frozen-time sweep at the middle frame. Define one shared path between the held-out
    view and the nearest training camera by camera-center distance, using consistent pose interpolation.
    Assess this path qualitatively where ground truth is unavailable.

  - Save PNGs, MP4s, contact sheets, and identical detail crops selected from ground truth before inspecting
    model results.

  - Compute per-frame and aggregate PSNR, SSIM, and LPIPS-Alex with a shared evaluator. Present separate
    tables for SelfCap and Basketball, including differences from STG Lite and STG Full.

  - Describe ghosting, floaters, blur, edge failures, and flicker with image or timestamp references. Do not
    invent a combined artifact score.

  - Measure command wall time, checkpoint size, sampled GPU peak/baseline, and synchronized warm rendering
    throughput: ten warmup renders followed by 100 timed renders, excluding saving and encoding.

  - Reload the complete model in a fresh process with network access disabled and report exact equality or
    numerical differences.

  Validate camera transforms, synchronization, time mappings, held-out exclusions, output dimensions, and
  missing-model-state errors. Check the evaluator using identical and deliberately perturbed images. Verify
  existing STG-lite behavior, documentation links, command syntax, and git diff --check.

  Completion requires five experiment reports and a comparison summary, with a reproducible result or
  specific blocker for every method/scene pair. Recommendations must prioritize observed artifacts and
  qualify unfinished training. These short experiments assess quality within the selected budget; they do
  not establish full-paper rankings or long-sequence performance.

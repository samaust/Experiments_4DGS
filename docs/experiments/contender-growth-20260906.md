# STG growth and offline evaluation — 2026-09-06

This record supersedes the earlier untested densification/EMS and offline
rendering statuses. The two-hour scene allocations and full comparison remain
unfinished; iteration-2000 results are provisional, not paper-level rankings.

## Correctness fixes and tests

The original eight checkpoint-resolver tests were restored from commit
`b7907f9` into `tests/test_stg_checkpoint_resolver.py`, alongside the newer
training-state tests. The suite currently passes 28 tests. Measurement now
aborts if its GPU sampler exits, including before launching the workload;
a synthetic failing-sampler test verifies this behavior.

Further inspection withdrew the claimed Lite EMS signature mismatch:
`densification_postfix()` has a `dummy=None` argument. It already accepts the
extra argument supplied by `addgaussians()`.

The actual failure was zero initialization of EMS-added quaternions in both
Lite and Full. In `verify-stg-growth.py`, each native model started with 32
synthetic points, added six via EMS, split to 44, and pruned to 43. Before the
fix, forward/backward immediately after EMS was finite, but subsequent splitting
produced nonfinite positions. After initializing quaternions to identity,
positions, gradients and optimizer shapes were valid, and checkpoint-restored
renders matched exactly (maximum pixel difference zero) for both models.

Evidence: `.local/runs/stg-growth-before-20260906.json` and
`.local/runs/stg-growth-after-20260906.json`. The two-line correction is tracked
in `patches/stg-ems-quaternion.patch`; no renderer mathematics or learned
checkpoint tensors were edited. Applying it changes the model-source hash,
so old pre-patch integration checkpoints must retain their matching old source
for strict provenance validation. The later training runs start from audited
initialization with the fixed source and share the existing budget ledger.

## Lite real training

Under `.local/runs/`:

- `stg-lite-selfcap-growth-20260906`: fresh training to iteration 650,
  86.157769 seconds supervisor wall time. Iteration 600 densification grew
  5,077 points to 7,461. A periodic checkpoint was saved during training.
- `stg-lite-selfcap-ems-20260906`: resumed from 650 to 2000,
  183.381149 seconds supervisor wall time. It completed the remaining
  densification rounds and EMS insertions at iterations 1660 and 1764.
  Point counts grew to 428,062 and 748,014 after those insertions and ended
  at 682,704 after pruning. Framework peaks were 1,533,910,528 allocated
  bytes and 2,826,960,896 reserved bytes; no device-wide sampler covered
  these Lite training runs.

All Lite attempts so far charge 295.572707 seconds in total to its SelfCap
allocation, including earlier integration controls. The latest checkpoint is
253,686,721 bytes, including optimizer/resume state. Its exported PLY is
87,386,889 bytes. Training remains incomplete against the 30,000-step schedule.

## Offline reload and artifacts

`scripts/offline-python.py` installs a Linux seccomp filter before importing
Torch. It denies non-Unix-domain sockets and `io_uring_setup`, while retaining
local IPC and GPU access. Its IPv4/IPv6 probes must return EPERM and its Unix
socket probe must succeed. These are intentional restriction self-tests, not
unexpected sandbox failures. This is an offline execution restriction, not a
general hostile-code sandbox; local IPC is allowed. The implementation follows
the [libseccomp API](https://github.com/seccomp/libseccomp/blob/main/include/seccomp.h.in).

Both iteration 650 and iteration 2000 were rendered in two fresh restricted
processes. Every held-out PNG (60/60) and every sweep PNG (20/20) was byte-exact
between reloads. Latest evidence directories:

- `.local/runs/stg-lite-selfcap-2000-offline-a-20260906`
- `.local/runs/stg-lite-selfcap-2000-offline-b-20260906`

The second directory contains `reload-heldout.json` and `reload-sweep.json`.
At iteration 2000 the native no-grad training rasterizer measured 527.717 FPS
at 1890×1061 using ten warmups and 100 synchronized renders, excluding loading,
camera construction, saving and encoding. GPU experiments ran sequentially.

`configs/detail-crops.selfcap-dance1.json` fixes four regions selected from
ground-truth frame 4150 before inspecting model renders: hair motion, face/hair
boundary, hands/body boundary, and static book text. The configuration includes
the selection-image hash and pixel bounds; these do not vary by method.

`scripts/package-stg-evidence.py` reuses the contact-sheet and sequence-analysis
helpers and creates fixed crops plus CPU-encoded MP4s. PNGs remain 1890×1061;
H.264 videos are padded to 1890×1062 without resizing. Lite's package is
`.local/runs/stg-lite-selfcap-2000-evidence-20260906/`, with exact commands and
provenance in `evidence.json`.

## Provisional Lite findings

All 60 held-out frames were evaluated using the shared evaluator and cached
AlexNet weights under the offline guard: PSNR **20.095080 dB**, SSIM **0.795017**,
LPIPS-Alex **0.331961**. Per-frame values are in the first offline-render
directory's `metrics.json`.

`prediction-contact.png` shows the bookcase and cabinet structure is substantially
clearer than the moving person. At 4120 and 4150, hair and face regions are
strongly blurred/ghosted; the head-to-background boundary is indistinct. Frame
4179 retains a recognizable face but weak hair and hand detail. The fixed
sweep shows soft leg silhouettes and patchy floor appearance toward its endpoint.
These observations come from the sampled sheets, not a full temporal review:
no flicker conclusion is inferred from adjacent-frame differences. Source
ground truth itself contains motion blur, especially in the hair at 4150.

CPU packaging and Lite metric evaluation overlapped Full's integration training,
with encoding/metric threads limited to two; do not interpret these partial
training wall times as an isolated training-speed comparison.

## Full iteration-2000 integration

`.local/runs/stg-full-selfcap-growth-20260906` completed a fresh 2,000-step run
in 308.962994 supervisor seconds. Six densification rounds grew 5,077 points
to 39,889; EMS at iterations 1660 and 1764 grew the model to 433,377 and
818,292 respectively. Pruning left 667,064 Gaussians at iteration 2000.
Framework peaks were 1,995,489,792 allocated bytes and 3,502,243,840 reserved
bytes. The device-wide 200 ms sampler recorded a 983–986 MiB baseline and
5,059 MiB peak (including baseline usage); brief peaks may be missed.
The measurement wrapper wall time was 309.171002 seconds.

All Full SelfCap attempts charge 326.851688 seconds of its 7,200-second
allocation; 6,873.148312 seconds remain. Lite has 6,904.427293 seconds remaining.
The Full resumable checkpoint is 296,088,861 bytes. Its final PLY is
101,394,634 bytes and decoder sidecar is 2,373 bytes.

Fresh offline processes rendered the checkpoint to
`.local/runs/stg-full-selfcap-2000-offline-a-20260906` and the corresponding
`offline-b` directory. The first run measured 293.383913 FPS using the same
1890×1061 camera, ten warmups and 100 synchronized native no-grad renders.
GPU rendering was sequential; the benchmark did not overlap CPU packaging
or metric evaluation. These later CPU tasks overlapped only the second,
untimed reload. The evidence package is
`.local/runs/stg-full-selfcap-2000-evidence-20260906`, using the unchanged
ground-truth-selected crop configuration.

All 60 held-out PNGs and all 20 sweep PNGs were byte-identical between the
two reloads; `offline-b` contains `reload-heldout.json` and `reload-sweep.json`.
Offline evaluation with the shared evaluator and cached AlexNet weights gives
PSNR **22.064535 dB**, SSIM **0.805183**, and LPIPS-Alex **0.340954** over all
60 held-out frames. Per-frame values are in `offline-a`'s `metrics.json`.

The Full prediction sheet shows pronounced face/hair blur and ghosting at
4120 and 4150, while bookcase edges remain clearer. At 4179 the face is
recognizable but soft, and hair blends into the background. These are sampled
image observations, not evidence of temporal flicker or a completed-budget
ranking.

The unchanged face/hair crop confirms these soft boundaries at all three
sampled timestamps. The Full sweep sheet at poses 0, 10 and 19 shows blurred
hand/knee boundaries and patchy floor appearance. Endpoint framing cuts off
the head; this follows the shared camera path and is not by itself a model
artifact. No full-video flicker assessment has been completed.

### Full reproduction commands

Run from the repository root with the pinned environment and applied patches.
Output directories must be new; repeated training is charged to the same
central budget ledger. The following reproduces the integration, not the
eventual full-budget run:

```bash
.local/envs/stg-render/bin/python scripts/measure-experiment.py \
  --output .local/runs/stg-full-selfcap-growth-measurement-20260906 \
  --cwd /home/auss/git_repos/samaust/Experiments_4DGS -- \
  /home/auss/git_repos/samaust/Experiments_4DGS/.local/envs/stg-render/bin/python \
  scripts/train-stg-manifest.py --checkout .local/SpacetimeGaussians \
  --manifest .local/data/selfcap/dance1-processed-20260906/manifest.json \
  --initialization .local/data/selfcap/dance1-initialization-20260906 \
  --output .local/runs/stg-full-selfcap-growth-20260906 --model full --max-steps 2000

.local/envs/stg-render/bin/python scripts/offline-python.py scripts/render-stg-manifest.py \
  --checkout .local/SpacetimeGaussians \
  --manifest .local/data/selfcap/dance1-processed-20260906/manifest.json \
  --checkpoint .local/runs/stg-full-selfcap-growth-20260906/checkpoint.pt \
  --output .local/runs/stg-full-selfcap-2000-offline-a-20260906 --benchmark

.local/envs/stg-render/bin/python scripts/package-stg-evidence.py \
  --render-directory .local/runs/stg-full-selfcap-2000-offline-a-20260906 \
  --manifest .local/data/selfcap/dance1-processed-20260906/manifest.json \
  --crops configs/detail-crops.selfcap-dance1.json \
  --output .local/runs/stg-full-selfcap-2000-evidence-20260906
```

Repeat rendering to a new `offline-b` directory without `--benchmark` for
the second reload. Run `scripts/analyze-sequence.py` on `images/0015` and
`sweep` with `--previous-run` pointing to the matching first-render directory.
Run the shared evaluator under `scripts/offline-python.py` with
`--lpips-alex`, using the cached Torch weights and two CPU threads as above.

Validation after these additions: all 28 research-environment unit tests pass;
`git diff --check` passes. Native growth checks cover both variants separately.

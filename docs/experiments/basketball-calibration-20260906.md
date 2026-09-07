# Plan 005 — Basketball estimated-calibration pilot

Status: **blocked at the four-camera intrinsic-prior pilot**. No accepted rig,
synchronization, processed Basketball scene, initialization or model result was
produced. This executes plan 005 through its section 1.6 stop condition; sections
2–4 remain unexecuted. This is an estimated-calibration experiment, not official
benchmark calibration.

## Evidence and stopping criterion

The pilot configuration was written before inference. A fixed-camera prior was
considered unusably unstable when `(max(fx) - min(fx)) / median(fx) > 0.20` across
source frames 50, 75, 100, 125 and 149. This is an implementation-defined pilot
sanity threshold for the plan's “intrinsic estimation is unusable” gate, not one
of the plan's final geometric acceptance thresholds. Its purpose is to reject
large frame-dependent focal changes for one fixed physical camera before using
those estimates as reconstruction priors. It does not prove calibration is
impossible. No threshold was adjusted after observing the pilot.

| Camera | Minimum fx | Median fx | Maximum fx | Relative range | Pilot stability |
| --- | ---: | ---: | ---: | ---: | --- |
| 4 | 827.250 | 887.706 | 1007.407 | 20.2948% | **Fail** |
| 12 | 677.219 | 710.598 | 727.194 | 7.0328% | Pass |
| 21 | 824.540 | 830.241 | 864.666 | 4.8330% | Pass |
| 29 | 871.369 | 880.392 | 890.160 | 2.1344% | Pass |

Focals are expressed at 960×540. GeoCalib ran independently on five fitting
frames per camera using its pinhole model and internal resize/unscale wrapper.
The external resize used OpenCV INTER_AREA from 1920×1080. These are unrefined
priors; no COLMAP/OpenCV pixel-center conversion or accepted intrinsics are
claimed. Depth and semantic masking were skipped after the intrinsic gate
failed. Temporal neighbor differences were saved as diagnostics, but they are
not validated static masks.

The [tracked evidence](basketball-calibration-20260906.json) contains all 34
video hashes, all 20 intrinsic observations and uncertainties, runtime and
weight hashes, budget totals, and hashes binding the full local records:

- `.local/calibration/basketball-v1/frame-roles.json`
- `.local/calibration/basketball-v1/input-audit.json`
- `.local/calibration/basketball-v1/pilot/config.json`
- `.local/calibration/basketball-v1/pilot/result.json`
- `.local/calibration/basketball-v1/pilot.log`
- `.local/calibration/basketball-v1/gpu-ledger.json`
- `.local/calibration/basketball-v1/status.json`

The full pilot result includes hashes of tracked ViPE source/configuration and
the top-level compiled extension. RGB and temporal-difference diagnostics are
retained alongside it. No calibration cloud or Gaussian initialization exists.

## Input and runtime audit

All 34 filenames are exactly `0.mp4` through `33.mp4`. Each file was SHA-256
hashed and fully decoded with ffprobe: 250 frames, 1920×1080 throughout, 25 FPS,
250 monotonically spaced presentation timestamps, and no reported decoder
errors. Timestamps run from 0 to 9.96 seconds at 0.04-second intervals. This
verifies container timing and coverage, not dynamic synchronization or physical
camera-ID correctness; those require the unexecuted geometry/timing stages.

Frame assignments were saved before inference: experiment 0–49, fit 50–149,
selection 150–199, final validation 200–249. The pilot's guarded reader permits
only training-camera fitting frames. ViPE reindexed frame IDs retain an explicit
mapping to original source IDs. The input audit decodes all frames for integrity
but supplies no decoded images to estimation.

ViPE remained clean on branch `tridi`, revision
`de50e6ab1066e32c96d32499a282ecaa2fbf2d90`, using its existing `.venv` without
installation or source changes. Python 3.14.6, PyTorch 2.13.0+cu130, CUDA runtime
13.0; host RTX 4090 with driver 595.84. `vipe_ext`, GeoCalib, UniDepth and
TrackAnything imports succeeded. The pinned PyCOLMAP environment reports 4.2.0.
Import success does not establish execution of every compiled dependency;
UniDepth/TrackAnything kernels were not exercised after the gate failed.

PyTorch reported CUDA unavailable in the sandbox. The single required host
retry succeeded; the pilot then ran with host GPU access. This blocker is a
numerical pilot gate, not a remaining sandbox or permission denial. The NVIDIA
catalog lookup succeeded; no additional skill was installed.

## Resources and budget

The GPU worker took 21.0424 seconds under the supervisor, including source/weight
hashing and startup; its inference section took 17.8921 seconds. PyTorch peak
allocated memory was 531,574,272 bytes; peak reserved memory was 648,019,968 bytes
(these exclude unrelated host/display allocations). The 1,800-second attempt
reservation was finalized as failed and charged for its elapsed wall time.
Two short runtime import/device probes were additionally charged a conservative
60 seconds each, including the failed sandbox probe. These two charges were
recorded retrospectively as upper bounds, not measured GPU utilization.

Total calibration charge: **141.0424 / 28,800 seconds** (0.03918 GPU-hours),
leaving 28,658.9576 seconds. Jobs ran sequentially. The separate calibration
ledger uses a lock, durable reservation before worker launch, crash-conservative
accounting, and the existing process-group deadline supervisor. It does not
change the global training ledger or redistribute any method allocation.
Basketball training charge in this task: **zero**.

## Implementation and checks

New scripts: `basketball_audit.py`, `basketball_vipe_pilot.py`, and
`calibration_budget.py`. The optional UniDepth/TrackAnything paths are present
in the thin adapter but remain unvalidated at runtime because the earlier gate
failed. Do not treat them as a validated all-camera estimator or synchronization
pipeline. No SelfCap adapter, checkpoint, or training implementation changed.

Validation passed: 10 new unit tests, 8 existing training-budget/supervisor
tests, and 9 existing SelfCap scene-adapter tests (27 total). CLI help syntax,
evidence hashes, documentation links and `git diff --check` also passed.

Unit checks cover decoded coverage, irregular/duplicate timing, dimensions and
rates, disjoint frame roles, forbidden fitting-frame/camera access, original
frame-ID mapping, intrinsic gate boundaries/nonfinite input, failed-attempt
charging, crash reservations and rejecting a training ledger. Geometry,
initialization leakage, processed-manifest and Basketball reload tests remain
pending with their unimplemented stages.

Reproduce the audit with:

```bash
python3 scripts/basketball_audit.py \
  --videos .local/data/vru-basketball/Basketball_dg \
  --vipe /home/auss/git_repos/samaust/Tridi/vipe \
  --output .local/calibration/basketball-v1
```

The executed pilot command was:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 scripts/calibration_budget.py \
  --ledger .local/calibration/basketball-v1/gpu-ledger.json \
  --seconds 1800 --log .local/calibration/basketball-v1/pilot.log \
  -- /home/auss/git_repos/samaust/Tridi/vipe/.venv/bin/python \
  scripts/basketball_vipe_pilot.py \
  --workspace .local/calibration/basketball-v1 \
  --vipe /home/auss/git_repos/samaust/Tridi/vipe
```

Existing pilot/log outputs are deliberately protected against overwrite. Do not
rerun or relax the pilot gate automatically. Continuing requires an explicit
revision to the blocked pilot strategy; manual annotation, substitute cameras,
and model search are not authorized by this result.

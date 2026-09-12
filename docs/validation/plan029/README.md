# Plan 029 validation

Implemented [Plan 029](../../../plans/plan_029.md) as a standalone task, without
starting or resuming the continuous-improvement loop. All acceptance checks pass.
No production initializer generation, model inference, model training, or EDGS
oracle execution was performed. Historical archives, licenses, and reports were
left intact. Source hashes are in [implementation-hashes.json](implementation-hashes.json).

## Evidence

| Check | Result | Evidence |
|---|---|---|
| CPU numerical and full caller integration | 9 tests passed, no skips | [CPU log](cpu-tests.txt) |
| CUDA numerical and full caller integration | 9 tests passed, no skips | [CUDA log](cuda-tests.txt) |
| Dense-cloud, fusion, recovery, reporting and resources | 21 tests passed | [Dense log](dense-tests.txt) |
| Temporal geometry, motion support and cropped matching | 5 tests passed | [Temporal log](temporal-tests.txt) |
| FreeTimeGS initialization and temporal assembly | 5 tests passed, no skips | [Initialization log](initialization-tests.txt) |
| Basketball camera geometry | 5 tests passed | [Geometry log](geometry-tests.txt) |
| SelfCap frame selection and split exclusions | 3 tests passed | [Frame log](selfcap-frames-tests.txt) |
| 15,000-match CUDA smoke | 14,998 accepted; 2 individually rejected | [Smoke report](cuda-smoke.json) |

The numerical tests cover known points with nonidentity poses, unequal focal
lengths and off-center principal points; seeded noisy input against independent
NumPy float64 equations; residual checks; a parallax/rank sweep; separated cameras
with parallel optical axes; coincident cameras and zero disparity; nonfinite
matches/cameras/overflow; mixed, empty and all-rejected batches; shared and distinct
per-point projections; noncontiguous tensors, both dtypes, ordering, unchanged
inputs and detached outputs. Solver spies prove rejected systems never reach
`lstsq`; simulated execution failures propagate, and nonfinite solutions are rejected.

Both actual caller entry points run with deterministic matcher stubs and synthetic
images/calibration, through artifact/report generation. EDGS path reads/stats,
geometry loading and source subprocess calls deliberately fail. The fixtures
include negative depth, excessive reprojection residual, NaN coordinates, rank
failure and NaN/Inf sampling confidence. The SelfCap output is also loaded as both
v2 and historical v1, and corrupted archive/image digests still fail validation.
CPU integration redirects only device operations; CUDA integration uses real
CUDA solves, transfers, synchronization and memory APIs. Matcher source/weight
verification remains unchanged; inference itself is stubbed to honor the plan.

## Runtime and limits

The required environment is `.local/envs/roma/bin/python`: Python 3.14.6,
PyTorch 2.13.0+cu130, CUDA runtime 13.0. Host execution exposes one RTX 4090
with driver 595.84. The sandbox reported CUDA unavailable; the authorized host
retry succeeded. Every validation invocation had a 300-second timeout and
`CUDA_VISIBLE_DEVICES=0`; GPU invocations ran sequentially. Initialization
regressions used the existing `.local/envs/freetimegs/bin/python` environment.

The passing cold smoke call took 0.108975 seconds including transfers, screening,
solve and synchronization, and peaked at 15,232,000 allocated bytes. Maximum XYZ
difference from the independent reference was 5.79056e-6; the XYZ assertions retain
`rtol=atol=2e-4`. Maximum unscaled residual difference was 0.000209363 and maximum
scaled residual excess was 1.65219e-8, below four float32 epsilons (4.76837e-7).
This is a synthetic smoke measurement, not reconstruction quality evidence.

Three 15,000-match validation invocations occurred, all within their individual
five-minute timeouts; the plan sets no attempt ceiling. Retained failed attempts:

1. The first passed XYZ comparisons but failed an overly strict, unit-dependent
   residual assertion for 1/14,998 systems. At index 10121 the residual was
   0.00024265598846681164 versus the NumPy minimum 0.00003329346858072996;
   the difference 0.0002093625198860817 exceeded the attempted absolute 0.0002
   tolerance. The plan specifies 2e-4 for well-conditioned XYZ, not unscaled
   equation residuals. The harness now bounds residual excess by
   `4*eps*(||A||_F*||x_reference||_2 + ||b||_2)`, accounting for float32 equation
   and solve roundoff. The implementation and XYZ tolerance did not change.
2. All numerical assertions passed, but JSON serialization failed with
   `TypeError: Object of type float32 is not JSON serializable` for
   `scaled_residual_limit`. The partial output (trailing whitespace trimmed) remains in
   [cuda-smoke-attempt2.partial.txt](cuda-smoke-attempt2.partial.txt), and is not
   a completed report. The harness now casts the threshold to Python float
   and serializes before opening the output.
3. All checks and report serialization passed: [cuda-smoke.json](cuda-smoke.json).

To reproduce the primary checks (request host execution for CUDA):

```bash
CUDA_VISIBLE_DEVICES=0 timeout 300 .local/envs/roma/bin/python -m unittest discover -s tests -p 'test_triangulation*.py' -v
CUDA_VISIBLE_DEVICES=0 TRIANGULATION_DEVICE=cuda:0 timeout 300 .local/envs/roma/bin/python -m unittest discover -s tests -p 'test_triangulation*.py' -v
CUDA_VISIBLE_DEVICES=0 timeout 300 .local/envs/roma/bin/python tests/triangulation_cuda_smoke.py --output /tmp/plan029-new-smoke.json
```

Regression commands use unittest discovery with the filename patterns
`test_basketball_dense*.py`, `test_basketball_temporal*.py`,
`test_basketball_geometry.py`, `test_selfcap_initialization_frames.py` in the RoMa
environment, and `test_freetimegs*initialization.py` in the FreeTimeGS environment.
All use the same one-device visibility and 300-second timeout.

## Provenance and limits of the result

The [derivation](../../triangulation.md) was saved before the helper was written.
This task inspected existing callers, the RoMa loader, and the beginning of the
historical extraction loader. It did not inspect or copy EDGS triangulation or
nearest-neighbor bodies. Prior repository work did inspect EDGS source; this is
independently derived work, not a clean-room or legal-clearance claim.

The numerical mask does not establish positive depth, reprojection quality,
parallax or semantic support. Those caller gates remain in place, as does the
existing multiview velocity solver. There is no claim of bitwise identity or
unchanged trained/reconstructed quality. Historical EDGS-specific tests were not
used as an oracle; independent numerical tests and affected local regressions
provide this implementation's evidence.

  # Plan 029 — Independent PyTorch triangulation for Basketball and SelfCap

  ## Summary

  Implement a small, reusable triangulation module using standard camera matrices and
  batched torch.linalg.lstsq. Replace EDGS geometry usage in both active callers,
  including SelfCap’s nearest-neighbor operation.

  Preserve the current unweighted, inhomogeneous least-squares formulation, float32
  production calculations, CUDA execution, and downstream geometric acceptance rules.
  Reject invalid matches individually, as requested.

  Success means both callers can generate geometry without accessing an EDGS checkout,
  supported by independent numerical tests and an actual CUDA validation run.

  ## Mathematical design and interface

  Create scripts/triangulation.py with this interface:

  triangulate_points(
      P1, P2, points1, points2,
      *,
      device,
      dtype=torch.float32,
      rank_rtol=None,
  ) -> tuple[torch.Tensor, torch.Tensor]

  - Accept projections shaped [3,4] or [N,3,4], and corresponding pixel coordinates
    shaped [N,2].

  - Use conventional column-vector projections, P = K[R|t], with undistorted pixels
    expressed in the same coordinate convention as K. Perform no implicit pixel-center
    adjustments.

  - Return xyz[N,3] and boolean valid[N], preserving input correspondence order and using
    the requested device. Invalid points contain NaNs.

  - Support float32 and float64; production callers explicitly select float32/CUDA.
    Convert and detach inputs without modifying their data or retaining their autograd
    graph.

  - Raise descriptive errors for malformed shapes, unsupported dtypes, non-finite camera
    matrices, and unavailable devices. Empty correspondence batches return correctly
    shaped empty tensors.

  Document the derivation before writing the implementation. For each observation (u,v)
  and projection rows p1,p2,p3, form:

  (u·p3 − p1) · [X,Y,Z,1] = 0
  (v·p3 − p2) · [X,Y,Z,1] = 0

  Stack the four equations from two cameras. Move their fourth-column constants to the
  right-hand side and solve the resulting [N,4,3] systems with:

  torch.linalg.lstsq(A, b, driver="gels")

  Do not introduce homogeneous DLT, normal-equation inversion, weighting, regularization,
  or row normalization.

  Write from this mathematical specification and PyTorch’s public APIs. Do not copy,
  translate, or extract EDGS function bodies. Record prior source inspection honestly;
  describe the work as independently derived, without claiming a clean-room process or
  legal clearance.

  ## Numerical safety and integration

  Protect the CUDA solver before invocation.

  - Exclude matches containing NaN/Inf coordinates or producing non-finite equation
    coefficients.

  - Compute singular values of the remaining coefficient matrices on the requested
    device.

  - Require sigma_min > rank_rtol * sigma_max, with rank_rtol defaulting to 4 *
    torch.finfo(dtype).eps; require a supplied threshold to be finite and strictly
    between zero and one.

  - Send only eligible systems to lstsq. Leave rejected rows invalid, and reject non-
    finite solutions afterward.

  - Handle entirely rejected batches without invoking the solver. Propagate CUDA,
    allocation, or linear-algebra execution failures; do not silently substitute CPU
    execution.

  This explicit screening is necessary because CUDA’s gels driver assumes full-rank
  inputs. Passing rcond to that driver does not provide the required protection. PyTorch
  least-squares documentation

  The returned mask means numerically solved, not geometrically accepted. Positive depth,
  reprojection accuracy, parallax, and semantic support remain caller responsibilities.

  Update both consumers.

  - In scripts/basketball_temporal_cloud.py, use the existing standard projection
    matrices and combine numerical validity with the existing geometry mask. Preserve the
    2-pixel reprojection threshold, 1-degree parallax threshold, multiview/semantic
    checks, and velocity calculation.

  - In scripts/initialize-edgs-selfcap.py, construct standard projections and preserve
    positive-depth and 0.01 normalized L1 reprojection checks. Replace EDGS nearest-
    neighbor selection with torch.cdist, self-distance masking, and minimum-distance
    selection over the same flattened camera transforms. Break exact ties by lowest
    camera index and document that convention.

  - Remove EDGS revision checks, source extraction, and projection packing from active
    paths. Retain the existing RoMa loader and its source/weight verification.

  - Keep the SelfCap script name. Accept --edgs temporarily as an optional deprecated
    argument, emit a warning when supplied, and never inspect its path.

  - Return only XYZ and validity from the new helper: both callers already discard EDGS’s
    reprojection-error arrays, so their unused epsilon-adjusted error calculation need
    not be reproduced.

  Preserve artifact history.

  - Give newly generated Basketball configuration and SelfCap reports version-2 schemas.
    Record the local implementation hash, solver identifier, dtype, driver, rank
    threshold, and numerical rejection count; remove new-output claims of an EDGS source
    revision.

  - Update the SelfCap cloud loader to accept historical version-1 and new version-2
    reports while retaining its existing data/hash validation.

  - Preserve old archives, licenses, experiment reports, and their provenance. Update
    current workflow documentation to distinguish the new implementation from historical
    EDGS-generated results.

  ## Validation and acceptance

  Use synthetic calibrated scenes and an independently assembled NumPy float64 least-
  squares reference. Do not execute EDGS as the test oracle.

   Scenario                        Required evidence
  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   Exact correspondences           Recover known 3D points with nonidentity poses,
                                   unequal focal lengths, and off-center principal
                                   points. For well-conditioned float32 fixtures, use
                                   rtol=atol=2e-4.
  ──────────────────────────────  ───────────────────────────────────────────────────────
   Noisy correspondences           With fixed random seeds, compare against the float64
                                   reference using the same quantized inputs. Verify
                                   least-squares residuals rather than expecting
                                   recovery of noiseless ground truth.
  ──────────────────────────────  ───────────────────────────────────────────────────────
   Nearly parallel viewing rays    Sweep decreasing parallax. Reject systems below the
                                   numerical rank threshold; assess residuals for
                                   accepted ill-conditioned systems. Avoid asserting
                                   precise depth where geometry cannot establish it.
  ──────────────────────────────  ───────────────────────────────────────────────────────
   Parallel camera orientations    Confirm that separated cameras with adequate parallax
                                   remain valid; parallel optical axes alone are not
                                   degeneracy.
  ──────────────────────────────  ───────────────────────────────────────────────────────
   Rank deficiency                 Cover coincident cameras and zero-disparity cases.
                                   Verify rejected systems never enter lstsq.
  ──────────────────────────────  ───────────────────────────────────────────────────────
   Invalid inputs                  Cover shape mismatches, NaN/Inf matches, non-finite
                                   cameras, empty batches, mixed valid/invalid batches,
                                   and all-invalid batches.
  ──────────────────────────────  ───────────────────────────────────────────────────────
   Points behind cameras           Confirm the numerical helper can solve them and both
                                   caller acceptance paths reject them.
  ──────────────────────────────  ───────────────────────────────────────────────────────
   Tensor behavior                 Cover shared/per-point projections, noncontiguous
                                   inputs, float32/float64, unchanged inputs, detached
                                   outputs, and correspondence ordering.
  ──────────────────────────────  ───────────────────────────────────────────────────────
   Caller integration              Exercise both paths with deterministic matcher stubs
                                   and synthetic inputs. Make EDGS file access fail
                                   deliberately; geometry and report generation must
                                   still work.
  ──────────────────────────────  ───────────────────────────────────────────────────────
   Compatibility                   Verify historical SelfCap reports remain loadable and
                                   new reports identify the local solver. Run affected
                                   geometry, dense-cloud, initialization, and fusion
                                   tests.

  Require an actual CUDA run using the existing Python 3.14/PyTorch 2.13.0+cu130
  environment. A skipped GPU test cannot establish completion.

  Include one 15,000-correspondence CUDA smoke test, matching SelfCap’s current per-pair
  scale. Record device/runtime versions, accepted/rejected counts, maximum numerical
  differences, synchronized elapsed time, and peak allocated memory. Use one GPU, a five-
  minute timeout per validation invocation, and no new model inference or training.

  Completion requires passing CPU/CUDA numerical and integration checks, preserved legacy
  artifact loading, and no EDGS runtime access by either caller. Commit the validated
  implementation with task-specific staging and a descriptive local commit; do not push.

  The scope excludes changing the existing multiview velocity solver, regenerating
  production initializers, training models, adding Kornia/PyTorch3D, or claiming bitwise
  identity or unchanged reconstruction quality.

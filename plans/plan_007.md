  # Diagnose short-window timing and implement fixed-calibration shared trajectories

  ## Summary

  Implement a bounded investigation that first measures the current estimator’s limitations, then evaluates
  shared-trajectory timing against independent observations.

  Preserve all 34 cameras, the current 72-edge graph, accepted calibration and scale, and the 0.25-frame
  timing requirement. Preserve the failed selection evidence. End with either a documented blocker or a
  selected candidate and frozen final-validation protocol. Do not open frames 200–249 or launch downstream
  experiments.

  ## 1. Establish the baseline and audit identifiability

  - Reverify calibration, profile, source-video, graph and static-validation-marker hashes. Use the existing
    CPU calibration environment and version new outputs without modifying historical scripts or results.

  - Retain frames 50–149 for fitting, 150–199 for already-observed selection, and 200–249 for untouched
    final validation.

  - Exercise the existing absolute-epipolar and temporal-bias estimators on fitting-only 50-frame windows
    starting at 50 and 100, and 25-frame windows starting at 50, 75, 100 and 125.

  - Inject offsets −0.75, −0.25, −0.10, 0, 0.10, 0.25 and 0.75 frames by resampling saved trajectories.
    Define shifted camera-B observations as B_new(f) = B_original(f − δ), making the expected change in
    estimated lag +δ. Trim to identical interpolation support across all injections; never extrapolate or
    cross a role boundary.

  - Distinguish these relative-shift tests from absolute ground truth. Add calibrated synthetic trajectories
    with known offsets, constant velocity, acceleration and direction changes, at 0, 0.25 and 0.5 pixels of
    observation noise.

  - Report recovery error, interval coverage, ambiguity, motion characteristics and support by window
    length. Include the analytic constant-velocity case where removing a per-track constant residual removes
    timing information.

  - Do not lower thresholds to improve the audit. An unidentifiable case must be reported as unsupported
    rather than confidently synchronized.

  ## 2. Build and fit shared trajectories

  Observations and associations

  - Produce consistent native-resolution fitting tracks for all cameras using the existing masked SIFT/LK
    and appearance-continuity policy.

  - Associate tracks through the fixed graph using mutual RootSIFT matching at the existing 0.8 ratio. Form
    multiview groups with at most one trajectory per camera; reject conflicting associations rather than
    resolving them using the desired timing result.

  - Require each modelled trajectory to have observations from at least three training cameras. Additional
    held-out observations may estimate their camera offsets, but cannot update training trajectories.

  - Merge overlapping duplicate tracks before splitting data. Assign entire multiview groups—including every
    camera observation—to deterministic optimization and assessment halves using seed 0. Require at least 12
    supporting groups per fixed edge in each half; insufficient support is a blocker.

  - Store original frame IDs, pixel coordinates, camera IDs, group membership, split membership and source
    hashes. No calibration-cloud points become dynamic trajectory observations.

  Model and optimization

  - Represent each dynamic point with a continuous cubic B-spline. Optimize spline coefficients and one
    constant offset per training camera; anchor camera 1 at zero.

  - Keep all intrinsics, distortion coefficients, rotations, translations and scale fixed. Use distortion-
    aware reprojection in the existing 960×540 pixel convention.

  - Minimize robust reprojection error with a one-pixel soft-L1 scale plus mean squared acceleration
    regularization. Normalize spatial coordinates by rig diameter and express time in source seconds.

  - Predeclare six configurations: knot spacing 5 or 10 frames, crossed with acceleration weights 0.1, 1 or
    10. Normalize data and regularization terms by their respective sample counts.

  - Use SciPy sparse least squares. Initialize from triangulated training observations at the current
    fitting offsets. Evaluate three deterministic starts: current offsets, zero offsets, and current offsets
    perturbed by seed-0 uniform noise within ±0.5 frames. Preserve the ±25-frame search boundary and reject
    boundary solutions.

  - Choose the configuration using fitting assessment evidence only: require the timing gates first, then
    minimize assessment reprojection error; break ties by fewer knots and then lower regularization weight.

  - After training-camera fitting, estimate held-out offsets 0, 10, 20 and 30 against frozen training
    trajectories. Do not jointly update those trajectories using held-out images.

  ## 3. Validate independently and evaluate selection

  - Evaluate each candidate using multiview groups excluded from its production optimization. Production
    offsets must remain frozen during assessment.

  - Measure pairwise offsets independently on assessment groups, using separate per-edge time gauges and
    nuisance trajectory fits. Do not supply production-offset priors or cycle penalties to these independent
    measurements.

  - Retain at least 12 groups per edge, the existing spatial-consistency limits, identifiable nonboundary
    optima, and 95% bootstrap halfwidth ≤0.25 frames. Bootstrap entire multiview groups, not individual
    observations, using 256 resamples and seed 0.

  - Require independently measured offsets to agree with production offsets within 0.25 frames, and require
    independent pairwise cycles to close within 0.25 frames. Cycles calculated directly from global camera
    offsets do not count as validation.

  - Repeat independent checks in the 50-frame and 25-frame fitting windows. Preserve uncertainty and
    ambiguity failures; do not require recovery from deliberately unidentifiable negative controls.

  - Freeze one fitting-qualified configuration, association policy, graph and evaluator before reevaluating
    frames 150–199.

  - Use the existing hash-verified native selection tracks where the extraction policy is unchanged. Apply
    the revised method to the full selection window and its two temporal halves, retaining within-role
    interpolation support.

  - Require all 72 fixed edges to satisfy the revised independent checks, full-versus-fitting agreement,
    temporal-half agreement, and full-rig cycle requirements at 0.25 frames. Do not remove failing edges or
    select a different model from these results.

  - Clearly label this as a new selection attempt on previously inspected data. If it passes, freeze the
    candidate and an analogous one-use final-validation protocol; leave final frames untouched.

  ## 4. Interfaces, verification and deliverables

  - Add a versioned CLI under scripts/ with stages for audit, associate, fit, assess, select and package.
    Each stage consumes a frozen configuration and hashed predecessor artifacts and writes to a fresh output
    directory.

  - Extend the timing artifact format with multiview-group provenance, spline parameters, optimization
    traces, motion-prior settings, independent edge curves, bootstrap intervals and explicit role/
    consumption metadata. Distinguish candidate offsets from accepted timing.

  - Test fractional-offset sign and recovery, constant-velocity ambiguity, noisy observations, outliers,
    association conflicts, duplicate-group leakage, held-out isolation, pose/distortion conventions,
    interpolation boundaries, cycle inconsistency and unchanged immutable artifacts.

  - Run the Basketball, budget and SelfCap regression suites, verify documentation links and artifact
    hashes, and run git diff --check.

  - Publish the estimator audit, method description, per-edge and per-camera results, resource usage and
    exact blocker or selected candidate. Update the contender summary and method reports while retaining
    previous failures.

  - Create local commits for validated milestones using explicit task-related paths. Do not push.

  ## Assumptions and stopping rules

  - This is an adapted research implementation, not a reproduction of an author’s complete pipeline.
  - Use existing CPU dependencies; no GPU jobs, new learned models or downloads are planned. Bound the
    investigation to four CPU wall-hours, including failed attempts, with no more than six model
    configurations.

  - Stop on inadequate multiview support, failed synthetic safeguards, unresolved identifiability,
    inconsistent independent checks, selection failure or the investigation budget.

  - Never relax the 0.25-frame requirement, change the graph, reset consumed markers or silently assign zero
    offsets.

  - The completion boundary is a frozen selection-qualified candidate and final-validation protocol, or a
    documented blocker. Final validation, Gaussian initialization and training are outside this plan.

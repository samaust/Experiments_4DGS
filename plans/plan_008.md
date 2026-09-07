  # Plan 008: Improve multiview support and evaluate shared-trajectory timing

  ## 1. Objective and fixed constraints

  Resolve the Plan 007 admission blocker, then implement and evaluate the shared-trajectory estimator.
  Finish with either a documented blocker or one selection-qualified candidate and a frozen final-validation
  protocol.

  - Preserve all 34 cameras, the existing 72-edge graph, accepted calibration and scale, held-out cameras
    0/10/20/30, and the 0.25-frame timing requirement.

  - Use frames 50–149 for fitting. Treat 150–199 as previously inspected selection data. Do not decode
    frames 200–249 or launch initialization, training or downstream experiments.

  - Preserve Plan 007 scripts, configurations, results and consumption markers. Create versioned v2
    implementations and fresh output directories.

  - Use existing CPU dependencies, at most eight CPU threads, no GPU work, downloads or learned models.
  - Start a fresh four-hour deadline at the first implementation action, including implementation, tests,
    failed attempts and packaging. Reserve the final 20 minutes for verification and reporting. Do not reset
    the deadline on retries.

  Reverify source-video, calibration, profile, scale, graph and consumption-marker hashes. Reuse the
  completed Plan 007 estimator audit as baseline evidence; its unsupported short-window searches do not need
  another full run.

  ## 2. Improve observations and partition complete groups

  ### Extraction and association

  Freeze one revised extraction and association policy before inspecting its results:

  - Extract native-resolution fitting tracks from seeds 50, 60, …, 140, 149, tracking independently forward
    and backward to the fitting boundaries. Stop each direction on the existing LK or appearance-continuity
    failure.

  - Preserve the current masks, SIFT settings, seed spacing, forward/backward error limit, 0.7 appearance
    threshold, 60-frame fitting-track minimum and motion thresholds. Use only fitting masks and fitting
    images.

  - Retain RootSIFT descriptors at available ten-frame anchors and track endpoints, using tracked positions
    and the seed keypoint’s scale/orientation. Store descriptor frame IDs and extraction provenance.

  - Merge overlapping same-camera duplicates before association using the existing rule: at least eight
    shared frames, maximum separation of one calibration pixel. Preserve every original track ID and
    descriptor sample; deduplicate repeated samples.

  - Define track-to-track appearance distance as the minimum descriptor distance across samples whose
    source-frame separation is at most 25 frames. Apply reciprocal nearest-track matching and the 0.8 ratio
    in both directions, with the runner-up taken from a distinct trajectory.

  - Associate only along the fixed graph. Reject entire connected components containing conflicting same-
    camera trajectories. Require observations from at least three training cameras; held-outs cannot satisfy
    this count.

  - Preserve original pixels, frame IDs, camera IDs, duplicate lineage and group membership. Calibration-
    cloud points must never become dynamic observations.

  Publish extraction and association losses by camera and edge, including track termination, duplicate
  merging, conflicting components and insufficient training-camera membership. Do not revise the policy
  after observing its support.

  ### Deterministic balanced partition

  Use only the binary group-to-edge membership matrix:

  - Assign entire groups to optimization or assessment; group counts must differ by at most one.
  - Require at least 12 groups per edge in each half. Immediately record a blocker if any edge has fewer
    than 24 eligible groups total.

  - Use SciPy mixed-integer optimization to minimize maximum edge imbalance, then total edge imbalance.
    Resolve equivalent partitions through seed-0 ordered group decisions.

  - Limit partition solving to 120 seconds. Independently reconstruct every edge count from the returned
    assignment. Distinguish proven infeasibility from solver timeout or incomplete optimization.

  - Never use timing estimates, residuals, motion scores or selection evidence to choose the partition. Do
    not try alternate seeds.

  Stop and package the evidence if admission fails. Passing membership counts only permits subsequent
  testing; geometric and temporal support may still fail.

  ## 3. Implement the spline estimator and independent measurements

  ### Production fitting

  Implement the solver after admission passes, and validate it synthetically before fitting real offsets.

  - Represent each group with a continuous cubic B-spline in rig-diameter-normalized coordinates. Use source
    seconds at 25 fps and corrected_time = (frame − camera_offset) / 25.

  - Optimize training-camera offsets and training-group spline coefficients, anchoring camera 1 at# Plan
    008: Improve multiview support and evaluate shared-trajectory timing

  ## 1. Objective and fixed constraints

  Resolve the Plan 007 admission failure through improved fitting tracks and a deterministic, coverage-
  balanced split. If support passes, implement the missing spline optimizer and independent evaluator, then
  attempt selection once.

  - Preserve all 34 cameras, the fixed 72-edge graph, accepted calibration and scale, held-outs 0/10/20/30,
    and the 0.25-frame timing requirement.

  - Use frames 50–149 for fitting. Frames 150–199 remain previously inspected selection data; frames 200–249
    remain untouched.

  - Preserve historical scripts, outputs and consumption markers. Reverify their hashes and reuse the
    completed Plan 007 estimator audit rather than rerunning it.

  - Allow one revised extraction/association policy and the same six model configurations. Do not tune
    policies, partition seeds or thresholds after seeing their outcomes.

  - Apply a fresh four-hour elapsed deadline covering implementation, tests, failed attempts and packaging.
    Reserve the final 20 minutes for verification and reporting. Use existing CPU dependencies, at most
    eight CPU threads, and no GPU jobs or downloads.

  - Finish with either an evidenced blocker or a selection-qualified candidate and frozen, unexecuted final-
    validation protocol. Training and initialization remain outside this plan.

  ## 2. Improve observations and balance whole-group support

  ### Tracking and association

  Version the implementation separately from Plan 007.

  - Extract native 1920×1080 fitting tracks using seeds at 50, 60, …, 140 and 149. Track each seed
    independently forward and backward to its appearance discontinuity or fitting boundary; join its two
    contiguous branches.

  - Retain the existing masked SIFT/LK settings: 16,000 SIFT features, at most 1,000 tracks per seed, eight-
    pixel seed spacing, 31-pixel LK window, one-pixel forward/backward limit and 0.7 adjacent-patch
    correlation.

  - Preserve the fitting minimum track length of 60 frames and existing motion thresholds. Use only hash-
    verified fitting masks. Keep the existing pixel-center conversion and radial undistortion.

  - Retain RootSIFT descriptors at the seed and supported ten-frame checkpoints along each trajectory, using
    the tracked position and stored keypoint scale/orientation. Store descriptor frame IDs.

  - Merge duplicates before matching: at least eight overlapping frames, with maximum separation at most one
    calibration pixel. Preserve source-track identities and descriptor provenance. Keep transitive duplicate
    families indivisible; reject incompatible families rather than splitting them across assessment.

  - Define track-to-track appearance distance as the minimum descriptor distance over checkpoint pairs
    separated by at most 25 source frames. Apply mutual nearest-neighbor matching and the 0.8 ratio in both
    directions, with the runner-up taken from a different trajectory.

  - Form connected components through the fixed graph. Reject entire conflicting components containing
    multiple trajectories from one camera. Require at least three training cameras per eligible group; held-
    out cameras do not satisfy that count.

  - Record losses at each step: tracking failure, length/motion rejection, duplicate merging, failed
    matching, conflicting components and insufficient training-camera membership.

  ### Deterministic partition

  Use only the binary group-to-edge membership matrix. Do not supply offsets, residuals, motion scores or
  selection evidence to the partitioner.

  - Immediately block if any edge has fewer than 24 eligible groups.
  - Use the installed SciPy integer-programming solver to assign each complete group to exactly one half,
    with half sizes differing by at most one and at least 12 groups per edge in each half.

  - Minimize maximum edge-count imbalance, then total edge-count imbalance. Resolve remaining ties through
    seed-0 ordered group decisions. Freeze the resulting membership and solver provenance.

  - Cap partition solving at 120 seconds. Report infeasibility separately from timeout or inability to
    complete the deterministic tie-break.

  - Reconstruct all edge counts from the saved partition and verify no original trajectory or duplicate
    family crosses halves.

  - If admission fails, stop the investigation and package the blocker before implementing the production
    optimizer.

  ## 3. Implement and safeguard the shared-trajectory model

  Implement the optimizer and evaluator after support admission, then validate them synthetically before
  fitting real offsets.

  ### Production fitting

  - Represent each group by a continuous cubic B-spline in coordinates normalized by rig diameter. Use
    source seconds: corrected time is (source_frame − camera_offset) / 25.

  - Optimize training-camera offsets and spline coefficients only. Anchor camera 1 at zero; preserve fixed
    poses, intrinsics, distortion and scale.

  - Use distortion-aware reprojection in the existing 960×540 convention. Minimize mean one-pixel soft-L1
    reprojection loss plus weighted mean squared acceleration. Apply sample normalization after
    robustification; acceleration remains a quadratic penalty.

  - Use clamped cubic splines with knot spacing 5 or 10 frames, crossed with acceleration weights 0.1, 1 and
    10. Use source-frame-spaced acceleration quadrature in seconds.

  - Initialize coefficients from training-only triangulation at each start’s offsets. Interpolation used for
    initialization must remain inside the current role/window; insufficient triangulation support is
    explicit.

  - Evaluate three starts per configuration: current fitting offsets, zero offsets and current offsets
    perturbed by seed-0 uniform noise within ±0.5 frames.

  - Use sparse SciPy least_squares, trust-region reflective optimization and LSMR, with tolerances 1e-6 and
    at most 200 function evaluations per solve. Record convergence, objectives, evaluation counts and
    elapsed time. Unconverged fits cannot qualify.

  - Bound offsets by ±25 frames and reject solutions within 0.01 frames of a boundary. Require qualifying
    starts to agree within 0.25 frames; retain disagreements as instability.

  - Estimate held-out offsets afterward against frozen training trajectories. Held-out observations cannot
    update those trajectories.

  ### Independent assessment

  - Keep production offsets frozen throughout assessment.
  - For assessment reprojection, fit new nuisance trajectories using assessment training observations at the
    frozen offsets. These nuisance fits never modify production state.

  - Measure independent edge lags through separate edge gauges and group-separable nuisance fits. Use only
    assessment observations and calibration, with no production-offset initialization, priors or cycle
    penalties.

  - For training-to-training edges, anchor one endpoint at zero and profile the other endpoint’s lag;
    remaining training-camera offsets and trajectory coefficients are nuisance variables local to that group
    and edge.

  - For edges involving a held-out camera, estimate nuisance trajectories and training offsets from training
    observations first, then freeze them before evaluating held-out lag.

  - Search integer lags throughout ±25 frames, refine every detected minimum basin to 0.05 frames, then
    refine competing minima to 0.01 frames. Preserve competing basins and boundary failures.

  - Bootstrap entire multiview groups with 256 seed-0 resamples. Cache group-separable profile curves so
    resampling reaggregates independent group evidence without treating individual observations as
    independent.

  - Also compute nuisance profiles with the acceleration penalty removed. A timing estimate cannot qualify
    solely because regularization creates a narrow optimum; unsupported or ambiguous data-only evidence
    remains a blocker.

  ## 4. Qualification and one selection attempt

  ### Synthetic safeguards

  Extend the existing tests to exercise the actual spline optimizer and independent evaluator.

  - Test known offsets −0.75, −0.25, −0.10, 0, 0.10, 0.25 and 0.75 frames; lengths 25, 50 and 100; and
    observation noise 0, 0.25 and 0.5 pixels.

  - Include acceleration, direction changes and identifiable constant-velocity examples, plus stationary and
    epipolar-direction negative controls. Constant velocity is not automatically unidentifiable under every
    calibrated reprojection geometry.

  - Require noiseless identifiable controls to recover within 0.05 frames. Any noisy case reported as
    qualified must recover within 0.25 frames. Preserve uncertainty, coverage and rejected-case statistics.

  - Verify that deliberately ambiguous cases remain rejected across all acceleration weights, including
    cases where the penalized objective alone appears confident.

  - Test outliers, fractional-offset sign, fixed interpolation support across injections, pose/distortion
    conventions, held-out isolation and absence of production information in independent assessment.

  - Test association conflicts, duplicate-family leakage, deterministic feasible/infeasible partitions,
    inconsistent independent cycles, immutable hashes, deadline enforcement and fresh-output requirements.

  - Stop before real fitting if safeguards fail.

  ### Fitting qualification

  Evaluate all six configurations within the remaining budget. Assess each configuration on the full fitting
  window, 50–99 and 100–149, and the four 25-frame fitting windows. Keep whole-group split membership
  unchanged when clipping windows.

  Every required edge/window must retain:

  - At least 12 supporting assessment groups and existing spatial-consistency limits.
  - An identifiable nonboundary optimum, including data-only evidence.
  - A 95% bootstrap halfwidth at most 0.25 frames.
  - Independent-versus-production lag disagreement at most 0.25 frames.
  - Independent cycle closure at most 0.25 frames.

  Do not substitute cycles derived from global offsets, extrapolate across windows, or narrow the qualifying
  search to manufacture support. Unsupported real windows block qualification.

  Choose among configurations passing every timing gate by lowest assessment reprojection error, then fewer
  knots, then lower acceleration weight. Do not refit production offsets using assessment groups.

  ### Selection

  - Freeze the configuration, associations, evaluator and graph before selection access.
  - Because extraction changed, freshly extract selection tracks with the same policy adapted to seeds 150,
    160, …, 190 and 199, with the existing 30-frame selection minimum.

  - Treat every selection group as assessment data; selection performs no production optimization.
  - Apply independent checks to 150–199, 150–174 and 175–199. Require all 72 edges, full-versus-fitting
    agreement, temporal-half agreement and independent cycle closure at 0.25 frames.

  - Record this as a new attempt on previously inspected data, with a separate attempt marker. Preserve
    prior markers.

  - On failure, stop without selecting another model. On success, freeze the candidate and analogous one-use
    final-validation protocol, but do not access final frames or mark timing accepted.

  ## 5. Interfaces, evidence and completion

  - Add a versioned CLI under scripts/ with prepare, associate, safeguard, fit, assess, select and package
    stages. Use a new frozen configuration under configs/basketball-rev2/; do not modify the v1
    configuration.

  - Each stage consumes hashed predecessors, shares the investigation deadline and writes a fresh output
    directory. An orchestration watchdog must terminate work before the packaging reserve.

  - Extend artifacts with descriptor checkpoints, duplicate families, group/partition provenance, spline
    parameters, optimizer traces, independent and data-only profiles, group-bootstrap intervals, resource
    accounting and explicit role-consumption metadata.

  - Distinguish candidate_offsets, accepted_timing, scientific rejection, numerical failure and budget
    exhaustion. Missing evidence remains missing; never substitute zero offsets or success-shaped
    placeholders.

  - Publish per-camera extraction counts, all-edge support changes, partition feasibility, synthetic
    results, configuration assessments and the exact terminal outcome. Update contender and method reports
    while retaining previous failures.

  - Run Basketball, budget and SelfCap regressions, verify documentation links and artifact hashes, and run
    git diff --check.

  - Create local commits for validated milestones using explicit task-related paths. Continue after commits
    until the candidate/protocol or documented blocker is complete. Do not push.

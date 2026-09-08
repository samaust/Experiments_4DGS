• ## Overall goal

  The project aims to turn the existing SelfCap and Basketball multiview images into complete 4D Gaussian
  models that can be saved, reloaded, and rendered across viewpoints and time. It must then compare
  reconstruction quality, motion fidelity, rendering speed, and resource cost to recommend a practical
  workflow. The authoritative definition is in docs/continuous-improvement/20260908-plan016/objective.md.

  These reports focus on a prerequisite for Basketball: estimating reliable shared camera timing. None
  produced accepted Basketball timing, trained a Basketball model, or performed the required Basketball
  reconstruction comparison.

  ## Experiment summary

   Report                              v1 (docs/experiments/basketball-shared-timing-v1.md)
   What was tried                      Audited the old short-window estimators and built multiview track
                                       associations.
   What worked                         Local ±2-frame diagnostics gave median error 0 and p95 error 0.10–0.20
                                       frames. All 42 noiseless synthetic safeguards passed. Extracted 5,785
                                       tracks and formed 351 eligible groups.
   What failed or remained incomplete  All 6,048 full ±25-frame curves lacked sufficient temporal support.
                                       Only 56/72 graph edges met the required split support; 16 failed. Zero
                                       spline configurations were fitted.
  ────────────────────────────────────────────────────────────────────────────────────────────────────────────
   Report                              v2 (docs/experiments/basketball-shared-timing-v2.md)
   What was tried                      Increased temporal track coverage, optimized a balanced group split,
                                       and implemented the spline solver plus independent synthetic evaluator.
   What worked                         Retained 46,024 tracks, formed 1,334 groups, and split them 667/667
                                       with at least 19 groups per edge per half. All 72 edges passed. Ran
                                       1,890 optimizer controls with 5,670 starts. Constant-velocity and
                                       acceleration controls passed.
   What failed or remained incomplete  On the direction-change control, 71/612 data-only fits hit the 200-
                                       evaluation cap, leaving 0/12 complete data-only profiles. Only 3/117
                                       independent controls ran before the stop. No real configuration ran.
  ────────────────────────────────────────────────────────────────────────────────────────────────────────────
   Report                              v3 (docs/experiments/basketball-shared-timing-v3.md)
   What was tried                      Added Jacobian scaling, stabilized rank-deficient least squares, and
                                       used cold/ascending/descending profiles.
   What worked                         All 6,984 synthetic attempts terminated; best-of-three regularized and
                                       data-only profiles recovered the true −0.10-frame offset. Regularized
                                       sweeps were complete for 12/12 groups.
   What failed or remained incomplete  Twelve data-only results had negative depth. Data-only directional
                                       evidence was only 11/12 ascending and 10/12 descending, so it could not
                                       qualify. Data-only Jacobians had rank 43–49 of 55.
  ────────────────────────────────────────────────────────────────────────────────────────────────────────────
   Report                              v4 (docs/experiments/basketball-shared-timing-v4.md)
   What was tried                      Replaced unconstrained fitting with positive-depth trust-constr
                                       optimization and transfer sanitation.
   What worked                         All returned states had positive depth. Regularized fits qualified in
                                       1,693/1,836 attempts.
   What failed or remained incomplete  Neither objective produced one complete group profile: regularized 0/12
                                       and data-only 0/12. Data-only qualified only 62/1,836 attempts; 1,774
                                       reached the 200-iteration ceiling. Weak transferred coefficients
                                       reached roughly (10^{43}) and caused enormous destination depths.
  ────────────────────────────────────────────────────────────────────────────────────────────────────────────
   Report                              v5 (docs/experiments/basketball-shared-timing-v5.md)
   What was tried                      Proved the raw log-depth barrier was unbounded and replaced it with a
                                       bounded constraint transform. Audited 172 displacement rays with 3,956
                                       probes.
   What worked                         Removed the known negative-infinity barrier incentive. All 72
                                       regularized attempts passed. The ray audit classified 64 invariant, 78
                                       observable-but-worse, and 30 infeasible rays.
   What failed or remained incomplete  Only 21/72 data-only attempts passed; total qualification was 93/144.
                                       The other 51 all reached 200 iterations. Five problems disagreed across
                                       starts, nine missed historical costs, and three required data-only
                                       transfers remained absent.
  ────────────────────────────────────────────────────────────────────────────────────────────────────────────
   Report                              v6 (docs/experiments/basketball-shared-timing-v6.md)
   What was tried                      Added the exact objective Hessian, including projection, robust-loss,
                                       spline-time, and acceleration curvature.
   What worked                         All 2,769 stable finite-difference actions agreed with the analytic
                                       Hessian. Regularized remained 72/72.
   What failed or remained incomplete  Qualification improved by only one attempt, from 93/144 to 94/144.
                                       Fifty data-only attempts still hit 200 iterations; five start
                                       disagreements, nine cost failures, and three transfer failures
                                       remained. Missing objective curvature was therefore not the dominant
                                       obstacle.
  ────────────────────────────────────────────────────────────────────────────────────────────────────────────
   Report                              v7 (docs/experiments/basketball-shared-timing-v7.md)
   What was tried                      Diagnosed saved v6 states and attempted to compare their KKT
                                       contributions with the nine best historical v4 states.
   What worked                         Rechecked 432 v6 references and nine historical states; objectives
                                       agreed within (4.0\times10^{-15}) and depths within
                                       (3.56\times10^{-15}).
   What failed or remained incomplete  V4 had discarded the returned depth and bound multipliers. The nine
                                       required historical KKT decompositions could not be verified, so
                                       conditioning, basin search, and qualification ran zero attempts. This
                                       was an evidence blocker.
  ────────────────────────────────────────────────────────────────────────────────────────────────────────────
   Report                              v8 (docs/experiments/basketball-shared-timing-v8.md)
   What was tried                      Reconstructed historical multipliers from the installed SciPy
                                       implementation, then tested a conditioning transform and exhaustive
                                       scalar basin search.
   What worked                         Recovered all nine historical states and verified 288 v5/v6 multiplier
                                       records. Conditioning qualified 116/144 attempts. Scalar search
                                       recovered all nine historical basins.
   What failed or remained incomplete  Conditioning preserved only 93/94 prior successes, recovered 23/50
                                       failures versus the required 25, and produced a median KKT ratio of
                                       0.250 versus the required ≤0.1. Scalar search had 12,126 records, 3,641
                                       failed required attempts, 1,530 missing-seed paths, and 835 path
                                       disagreements. Both screens were rejected.
  ────────────────────────────────────────────────────────────────────────────────────────────────────────────
   Report                              v9 (docs/experiments/basketball-shared-timing-v9.md)
   What was tried                      Corrected state accounting, created a canonical numerical ledger, and
                                       froze metric, initialization, and stopping adaptations for an 81-
                                       outcome benchmark.
   What worked                         Explained all 22 suspect v8 attempts using 474 distinct-canonical/same-
                                       physical witnesses. The fresh baseline completed 75 optimizer
                                       invocations; six paths had no qualifying seed.
   What failed or remained incomplete  All 18 detailed baseline artifacts were unreadable because NumPy arrays
                                       were passed to the JSON writer. Fifty qualifications were reported by
                                       events but could not be independently verified. Adaptation arms and
                                       final benchmark ran zero attempts.
  ────────────────────────────────────────────────────────────────────────────────────────────────────────────
   Report                              v10 (docs/experiments/basketball-shared-timing-v10.md)
   What was tried                      Implemented durable journals, atomic publication, recovery, and a five-
                                       policy focused benchmark.
   What worked                         Persisted and verified all 405 outcomes: 366 optimizer invocations and
                                       97,268 numerical entries. Conditioning reached 60/81 versus baseline
                                       50/81. Initialization made all three infeasible cold states feasible.
                                       All 47 archived qualified controls retained acceptable costs.
   What failed or remained incomplete  The final initialization-only policy still passed only 50/81, with six
                                       missing seeds and eight conditional path disagreements. Conditioning’s
                                       median KKT ratio was 0.24197, above 0.1. No policy qualified for full
                                       screens.
  ────────────────────────────────────────────────────────────────────────────────────────────────────────────
   Report                              v11 (docs/experiments/basketball-shared-timing-v11.md)
   What was tried                      Examined 48 saved trajectory snapshots and 24 displacement rays to test
                                       for runaway or feasible escape behavior.
   What worked                         All snapshots and all 24 analytical-limit classifications passed. Every
                                       one of the 12 data-only rays eventually violated depth, so those
                                       sampled directions were not indefinitely feasible escapes.
   What failed or remained incomplete  Independent verification failed 63/600 finite probe slots and 367
                                       gradient components, concentrated in three regularized rays. The error
                                       appeared in acceleration-gradient rows 0–1 at amplitudes (10^4) through
                                       (10^{44}).
  ────────────────────────────────────────────────────────────────────────────────────────────────────────────
   Report                              v12 (docs/experiments/basketball-shared-timing-v12.md)
   What was tried                      Used two independent exact-rational acceleration references on six
                                       retained v11 states.
   What worked                         The exact references agreed on all six costs, all 36 selected gradient
                                       components, and all signed summands.
   What failed or remained incomplete  The archived primary float implementation failed 25/36 components and
                                       the independent float implementation failed 17/36. Another 57 v11
                                       failed states remained unadjudicated. This proved an arithmetic error
                                       in both float paths, without qualifying the full evaluator.
  ────────────────────────────────────────────────────────────────────────────────────────────────────────────
   Report                              v13 (docs/experiments/basketball-shared-timing-v13.md)
   What was tried                      Implemented a Decimal80 acceleration calculation for the six exact-
                                       reference states.
   What worked                         Passed all six costs and all 36 selected partials: 42/42 comparisons.
                                       Both 12-case toy suites passed. Numerical execution took 0.1225
                                       seconds.
   What failed or remained incomplete  Coverage was limited to acceleration cost and coefficient rows 0–1 on
                                       six states. It did not validate image terms, all 54 gradient
                                       components, Hessians, constraints, transforms, KKT, or the other 57
                                       failures.
  ────────────────────────────────────────────────────────────────────────────────────────────────────────────
   Report                              v13 integration (docs/experiments/basketball-shared-timing-v13-
                                       integration.md)
   What was tried                      Mapped the Decimal kernel into the complete evaluator and enumerated
                                       the remaining timing gates.
   What worked                         Produced a detailed source and validation map covering objective,
                                       gradient, Hessian, constraints, KKT, coordinate transforms, callbacks,
                                       and accounting.
   What failed or remained incomplete  It was source analysis only: zero scientific execution and no
                                       integrated evaluator. It also showed that acceleration arithmetic
                                       cannot repair the weight-zero failures because their acceleration term
                                       is disabled.
  ────────────────────────────────────────────────────────────────────────────────────────────────────────────
   Report                              v14 (docs/experiments/basketball-shared-timing-v14.md)
   What was tried                      Built the first integrated Decimal evaluator for 16 cases and 32 cold/
                                       returned states.
   What worked                         Admission passed. Two frozen 20-case toy invocations passed their
                                       implemented assertions.
   What failed or remained incomplete  Readiness inspection found two coverage gaps: the candidate offset/
                                       mixed assembly and real TransformCache path were never exercised. A
                                       residual_only flag was also ignored. Scientific execution was therefore
                                       0 invocations and 0 comparisons.
  ────────────────────────────────────────────────────────────────────────────────────────────────────────────
   Report                              v15 (docs/experiments/basketball-shared-timing-v15.md)
   What was tried                      Repaired readiness and ran a complete evaluator comparison on the 16
                                       cases/32 states.
   What worked                         All 20 readiness groups passed. All 1,651 entries completed. Canonical
                                       comparisons passed in 91/96 contexts, new-transform comparisons in
                                       15/16, and historical corroboration in 16/16.
   What failed or remained incomplete  One returned weight-zero case caused five canonical failures and one
                                       new-transform failure involving Hessian symmetry and y-coordinate KKT.
                                       All 16 sequence-5 public replays were rejected. No timing solve ran.
  ────────────────────────────────────────────────────────────────────────────────────────────────────────────
   Report                              v16 (docs/experiments/basketball-shared-timing-v16.md)
   What was tried                      Formed centered image residuals directly and constructed Hessians
                                       symmetrically by unordered index pairs. Planned to test four states
                                       from cases 12/13.
   What worked                         Nineteen readiness groups passed, including exact dyadic congruence and
                                       asymmetric-input rejection. Physical and canonical Hessian checks
                                       preceding the failure passed.
   What failed or remained incomplete  Group 14’s transformed y Hessian failed in 11/169 entries; maximum
                                       error was (3.09\times10^{-11}), 6.10 times its allowance. Groups 15 and
                                       21 then could not complete. A NumPy-array serialization error also lost
                                       the supplemental protocol artifact. Scientific coverage was 0/32 states
                                       and 0/211 planned entries.

  ## How close the project is

  The latest saved state is:

   Criterion                                   Status               Position
  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  ━━━━━━━━━━━━━━━━━━━  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   SC-01: reproducible SelfCap and             Not met              SelfCap is supported; Basketball timing,
   Basketball preparation/reconstruction                            preparation, and reconstruction remain
                                                                    unqualified.
  ──────────────────────────────────────────  ───────────────────  ───────────────────────────────────────────
   SC-02: complete saved models reload and     Met                  Supported SelfCap models have saved/
   render                                                           reload/render evidence.
  ──────────────────────────────────────────  ───────────────────  ───────────────────────────────────────────
   SC-03: measured quality, motion, speed,     Not met              The required Basketball reconstruction
   and resource comparison                                          and comparison do not exist.
  ──────────────────────────────────────────  ───────────────────  ───────────────────────────────────────────
   SC-04: practical recommendation             Met                  A supported SelfCap recommendation exists
                                                                    with limitations.
  ──────────────────────────────────────────  ───────────────────  ───────────────────────────────────────────
   SC-05: reproducible retained evidence       Currently not met    Most evidence is strong, but v16 ended
                                                                    with incomplete readiness and a missing
                                                                    protocol artifact. Earlier evidence
                                                                    remains preserved.

  That is 2 of 5 criteria met outright. Considerable infrastructure has been completed: Basketball
  calibration, multiview association, balanced splitting, solver accounting, durable attempt storage,
  independent arithmetic references, and evaluator comparison machinery.

  The project remains far from the full objective in execution terms. Basketball is still before accepted
  synchronization and production reconstruction. The remaining path is:

  1. Qualify the complete evaluator and coordinate contract.
  2. Pass the focused timing benchmark.
  3. Pass the full conditioning, scalar-search, and combined timing gates.
  4. Fit and accept real Basketball timing.
  5. Prepare and train supported Basketball reconstruction methods.
  6. Save, reload, render, and measure those models.
  7. Compare Basketball and SelfCap quality, motion, speed, and resources.

  Across v1–v16, zero real Basketball timing configurations were accepted, zero Basketball models were
  trained, and zero Basketball reconstruction comparisons were produced.

  ## Failure mechanisms and likely causes

   Failure mechanism                                      Evidence and likely cause
  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   Insufficient temporal support                          V1’s full search was structurally impossible on a
                                                          50-frame window: 49 intervals cannot support both
                                                          −25 and +25 shifts on common samples. Sparse cross-
                                                          camera association then left 16/72 edges below the
                                                          required support. V2’s broader seeding and balanced
                                                          partition fixed this part.
  ─────────────────────────────────────────────────────  ─────────────────────────────────────────────────────
   Weakly observed data-only spline directions            Data-only Jacobians repeatedly had rank 43–49 of
                                                          55, sometimes with 6–12 initially zero columns.
                                                          Weak columns could acquire coefficients around
                                                          (10^{43}), then become observable after transfer.
                                                          This produces flat directions, large states, bad
                                                          seeds, and difficult positive-depth constraints.
  ─────────────────────────────────────────────────────  ─────────────────────────────────────────────────────
   Unbounded raw barrier                                  V5 established that the v4 barrier
                                                          (F-\mu\sum\log(d-m)) rewards arbitrarily large
                                                          common positive-depth translation even though the
                                                          original image objective approaches a finite limit.
                                                          The bounded transform removed this exact defect.
  ─────────────────────────────────────────────────────  ─────────────────────────────────────────────────────
   Constrained optimizer stagnation                       After repairing the barrier, most failed data-only
                                                          fits still stopped at 200 iterations with only 192–
                                                          197 distinct objective evaluations. Some xtol exits
                                                          had KKT norms above (10^{-6}). The likely cause is
                                                          weak conditioning combined with active constraints
                                                          and small trust regions, rather than simple
                                                          exhaustion of objective evaluations.
  ─────────────────────────────────────────────────────  ─────────────────────────────────────────────────────
   Multiple basins and path dependence                    V8 found 835 scalar path disagreements; v10
                                                          retained eight target disagreements and six missing
                                                          directional seeds. Cold, ascending, and descending
                                                          initialization reached different local states. This
                                                          is consistent with a nonconvex timing/trajectory
                                                          problem whose weak directions make warm-start
                                                          history influential.
  ─────────────────────────────────────────────────────  ─────────────────────────────────────────────────────
   Missing Hessian information was not the main cause     V6’s exact Hessian passed 2,769 derivative checks
                                                          but improved qualification by only one attempt.
                                                          This rules out omitted objective curvature as the
                                                          primary explanation for the data-only failures.
  ─────────────────────────────────────────────────────  ─────────────────────────────────────────────────────
   Historical evidence loss                               V7 could not recover exact v4 KKT terms because
                                                          returned multipliers had never been serialized. V9
                                                          lost detailed results because NumPy arrays reached
                                                          a JSON encoder. V16 repeated that serialization
                                                          class in a supplemental artifact. These are
                                                          persistence failures, not evidence that the
                                                          scientific model failed.
  ─────────────────────────────────────────────────────  ─────────────────────────────────────────────────────
   Floating-point cancellation in acceleration            V11 localized large-state gradient disagreement to
   derivatives                                            acceleration rows 0–1. V12’s exact rational
                                                          references proved both float implementations wrong
                                                          on many components, while v13’s Decimal80 path
                                                          passed 42/42 selected comparisons. Large signed
                                                          terms were cancelling to a tiny derivative, making
                                                          normal binary64 evaluation order significant.
  ─────────────────────────────────────────────────────  ─────────────────────────────────────────────────────
   Loss of small image residuals                          In v15’s failing case, the candidate computed
                                                          approximately (focal projection + principal point)
                                                          - observation, subtracting nearly equal values
                                                          around 400 pixels to obtain residuals near
                                                          (10^{-5}). The reference centered the observation
                                                          first. The lost low bits were multiplied by image
                                                          Jacobians around 157,000 and then exposed by
                                                          cancellation between gradient and depth-force terms
                                                          in KKT.
  ─────────────────────────────────────────────────────  ─────────────────────────────────────────────────────
   Hessian symmetry represented only mathematically       V15 computed the two directions of symmetric
                                                          contractions separately. They differed by one ULP
                                                          in one physical cross term, and dense coordinate
                                                          congruences amplified the asymmetry. V16
                                                          constructed one value per unordered pair, but its
                                                          transformed y Hessian then differed from the
                                                          unchanged matrix-multiplication oracle. The likely
                                                          v16 cause is floating-point reduction-order
                                                          disagreement between the mandated pair/left-fold
                                                          calculation and BLAS-style matrix multiplication;
                                                          this remains a hypothesis because the failed
                                                          transform artifact was not retained.
  ─────────────────────────────────────────────────────  ─────────────────────────────────────────────────────
   Public-coordinate replay mismatch                      All saved-y probes passed in v15, but all 16 new-
                                                          transform sequence-5 replays failed because
                                                          binary64 P @ y + origin did not reproduce the
                                                          originally admitted canonical vector exactly. This
                                                          is a coordinate-contract issue and cannot be fixed
                                                          by better acceleration or residual arithmetic.
  ─────────────────────────────────────────────────────  ─────────────────────────────────────────────────────
   Incomplete readiness coverage                          V14’s tests passed while bypassing two real
                                                          candidate paths, and source inspection found an
                                                          ignored flag. V16 stopped at another readiness
                                                          assertion before science. These failures correctly
                                                          prevented apparently successful toy code from being
                                                          treated as a qualified evaluator.

  The evidence does not show that Basketball synchronization is scientifically impossible. It shows that the
  current data-only nuisance formulation and its strict independent qualification gates have not produced
  stable, reproducible timing evidence, while the evaluator used to judge those fits still has unresolved
  arithmetic and coordinate-contract failures.
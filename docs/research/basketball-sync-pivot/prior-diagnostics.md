# What the earlier Basketball failures establish

The earlier work does not establish that Basketball has clock-rate drift, that a
particular camera is wrong, or that a spline representation cannot synchronize
it. It establishes distinct data-support, optimization and evaluator limitations.
Those distinctions matter when interpreting a learned cross-check.

The saved SIFT/LK recovery contains 67 passing edges. Under this campaign's common
robust estimator it covers only eight cameras from reference 1; disconnected
components are not assigned reference-relative offsets. The full 561-pair
inventory, two bridges in the whole graph, cycle residuals and leave-one-edge-out
sensitivity are retained in [the graph diagnostic](sift-common-graph.json).
This reuses saved correspondences and is not a new SIFT extraction or a passed
historical acceptance gate. The learned graph remains unavailable because the
released VisualSync preprocessing chain could not be completed within the
missing-core restriction. Empty learned evidence is not a measurement of poor
learned correspondence quality.

The [clock diagnostic](../../experiments/basketball-clock-diagnostic.md) found
zero *integer* lag on all ten inspected loop connections, using green display
changes in fit frames 50–149. Its integer bootstrap intervals were [0,0], while
two motion cycles closed at 0.30 frames against the unchanged 0.25-frame gate.
A display transition is interval-censored by exposure and refresh: identical
frame labels do not certify a subframe offset, and physical display-face delays
were not validated. An initially incorrect court-logo locator was rejected and
is not clock evidence. The present [metadata audit](basketball-freeze.json)
finds uniformly spaced 25-fps PTS through frame 249 in all 34 files; that rules
out irregular encoded PTS in this range, not independently drifting capture
clocks before encoding. Exact-pixel duplicates were checked only in 0–49.

The [v10 focused benchmark](../../experiments/basketball-shared-timing-v10.md)
persisted all 405 outcomes, but its final policy qualified 50/81, lacked six
required seeds and disagreed across conditional paths at eight targets. This
was a scientific qualification rejection, despite successful persistence.
The [v11 trajectory diagnostic](../../experiments/basketball-shared-timing-v11.md)
found very large returned trajectories in the metric-conditioned weight-zero
cases and original-coordinate KKT norms above qualification. Its independent
verification also failed on 63 regularized-control probe gradients. Lower cost,
solver-coordinate optimality or an incomplete independent check cannot replace
a qualified original-coordinate solution.

Later work increasingly examined the evaluator itself. [V15](../../experiments/basketball-shared-timing-v15.md)
completed its frozen schedule, but retained five failed canonical comparisons,
16 rejected public replays and one failed new-transform context. Failures in the
returned weight-zero metric/joint case involved Hessian symmetry and the
transformed KKT vector. [V16](../../experiments/basketball-shared-timing-v16.md)
then failed readiness before any scientific invocation: 11/169 integrated toy
Hessian entries exceeded the frozen arithmetic tolerances. A supplemental NumPy
serialization failure further limited retained diagnosis. This is not a new
measurement of camera timing or a failed Gaussian reconstruction.

Consequently the pivot is justified as an independent evidence path, not as a
claim that a learned method has already solved the old failure. Do not relax
historical gates, replace unqualified timings with zeros, or restart the consumed
spline/evaluator allocations. Plan 024 explicitly permits zero-offset Gaussian
controls even when a full-rig correction remains unavailable; label zero as an
operational assumption and preserve the missing paired comparison.

# Plan 026 — Basketball duration and initialization study

**Execution is in progress; this is not a completed nine-trajectory study.**
The dense temporal initializer failed the prescribed pilot gate after both
coarse and person-cropped matching. The six independent sparse trajectories
continue under the fixed plan. No dense model has been trained.

## Dense prerequisite

The cropped pilot produced recognizable person components and greater semantic
person coverage than the sparse prior, but visible detached fragments and
foreground smearing remained. The plan requires the absence of gross
foreground floaters, so those observations prevent accepting and freezing the
initializer. [Pilot review](pilot-review.md) retains the visual assessment,
counts, rejection evidence, motion-validity limitations, and large-artifact
locations. Numerical triangulation and tracking checks did not establish
acceptable visual geometry. Static fusion and full production assembly were
not reached. No synthetic court plane or additional recipe variant was used.

## Available comparison and protocol

STG Full and sparse FreeTimeGS each resume the verified historical 5,000-update
checkpoint for seeds 0, 1, and 2. Their targets are 50,000 absolute updates,
with intermediate snapshots at 10,000, 20,000, and 30,000. STG keeps its native
30,000-step position learning-rate decay and continues optimizer updates at
the final rate thereafter. FreeTimeGS keeps its native 70,000-step schedule.
STG uses two sampled images per update; FreeTimeGS uses one. Equal update
counts therefore do not imply equal training work or compute.

Calibration, scale, image resolution, camera IDs, and the zero-offset
operational assumption remain unchanged. Initialization uses only training
cameras and allowed frames. Evaluation uses the same 350 targets, frozen
regions and motion masks, and final Plan 024 protocol v3. Historical baseline
reuse is backed by [hash and coverage verification](baseline-reuse.json).
[Bootstrap parity](baseline-bootstrap-validation.json) reproduces all 32
historical baseline summaries, including both confidence bounds.

Native checkpoint restoration preserves saved optimizer, random-generator,
sampler, and method state exactly. Split GPU training is not bitwise identical
to uninterrupted training; repeated uninterrupted runs also vary. This is
documented with the actual differences in
[implementation validation](implementation-validation.md), rather than
claimed as exact post-training reproducibility. Both 5,002-update validation
checkpoints pass all 13 fresh-process PNG and raw-float render comparisons.
Production snapshot reload checks are still pending.

## Scientific effects

| Planned effect | Current status |
| --- | --- |
| Sparse FreeTimeGS: 50,000 versus 5,000 updates | Pending completed trajectories and matched evaluation |
| Dense versus sparse FreeTimeGS at matched updates | Unavailable: dense prerequisite failed |
| Initialization × training-duration interaction | Unavailable: dense prerequisite failed |
| STG Full versus dense FreeTimeGS learning curves | Unavailable: dense prerequisite failed |

The STG-versus-sparse-FreeTimeGS comparison is supplemental. It cannot replace
the missing planned dense workflow comparison or identify whether a qualifying
dense initializer would repair FreeTimeGS's weakness.

At 5,000 updates, inspected seed-0 player crops from all four held-out cameras
show severely blurred or missing players in both sparse workflows. Any claim
of improved dynamic reconstruction at 50,000 must be supported by player
regions and motion metrics; court or full-image improvements alone are
insufficient. Final endpoint interpretation is pending.

## Artifacts and limitations

The [baseline artifact index](analysis-baseline/artifact-index.json) and
[baseline curves](analysis-baseline/curves.csv) are explicitly partial outputs.
The large baseline visual bundle is
`.local/basketball-dense-temporal/visuals-005000-v2/`: 48 fixed comparison PNGs
and 12 videos, each containing all 50 source frames at 25 fps. The videos show
ground truth and the two available arms; the dense arm is absent. No
intermediate frames were synthesized.

Training, initialization, evaluation, failures, and resumed validation segments
are charged separately in `.local/basketball-dense-temporal/ledger.jsonl`.
Historical accounting remains unchanged. GPU-job wall time includes startup
and CPU work within each job, and is not GPU-kernel busy time. Standalone CPU
inspection, tests, plotting, and video encoding are outside that ledger.
Historical sparse-initialization CPU cost was not separately measured.

Confidence intervals use the pinned three-seed/five-frame-block bootstrap.
Temporal interpolation contains only one temporal block. Results concern one
scene and fixed cameras; the retained zero-offset assumption is operational,
not independent proof of physical synchronization. The dense recipe would
jointly change point count, geometry, and initial velocity, so this design
would not isolate those contributions even if its prerequisite had passed.

[Execution status](status.md) records the current handoff and validated local
commits. Completion cannot be declared while any of the nine required
trajectories or their required evidence is missing.

# Dense initialization pilot: prerequisite not met

Both the coarse and prescribed person-cropped RoMa pilots completed at frames
0/1, 25/26, and 45/46 using all 30 training cameras. All 12 fixed-view native
foreground renders from the cropped pilot were inspected. Players are
recognizable, and semantic-person projected coverage exceeds the sparse prior,
but detached fragments remain in cameras 21 and 31 at frame 0. Frame 45 also
contains visible foreground smearing. These observations fail the plan's
no-evident-foreground-floaters gate. No dense recipe is accepted or frozen and
no dense training is authorized by this assessment.

See [camera 21, frame 0](pilot-camera21-frame0.png),
[camera 31, frame 0](pilot-camera31-frame0.png), and
[camera 1, frame 45](pilot-camera1-frame45.png). These are native untrained
foreground-only renders, not trained reconstructions. Occlusion, people outside
the image, and missing backsides limit the visible components. The masks also
include spectators; semantic-person coverage is not a player-only quality score.

[Compact evidence](pilot-evidence.json) records counts, hashes, and coverage.
The cropped pilot retained 618,372 static observations, 480,215 person
observations, and 769 ball-labeled observations before fusion/deduplication.
442,237 foreground observations passed the image-tracking/geometric velocity
checks; 38,747 retain zero initialization velocity with an invalid-motion flag.
These are observations, not unique physical points or verified identities.
Large false-positive ball masks were observed; ball-label support is not proof
of ball reconstruction.

The pilot applies positive-depth, finite-coordinate, one-degree angle and
two-pixel reprojection checks. Foreground points need three supporting cameras.
The cropped matcher uses view-local labels to constrain associations; different
IDs are permitted between cameras. Adjacent-frame tracking uses the specified
31-pixel/four-level LK configuration, one-pixel round-trip bound, and the same
tracked local instance. Native KNN displacement is retained only as a diagnostic.
The surviving visual artifacts demonstrate that these numerical checks alone
do not establish an acceptable initialization.

Static fusion and production assembly were not reached. No court plane was
added. Static point count does not establish complete floor coverage; remaining
floor holes and static fusion quality are unresolved. The only assessed dense
recipe variants are the plan's coarse pilot and person-cropped fallback. No
held-out scores were used, no synchronization was changed, and no further dense
variant is launched.

Large evidence is under `.local/basketball-dense-temporal/`:

- `masks-pilot-001/`: masks, local phrases, source hashes, changing-region masks.
- `neighbors.json`: all considered training pairs, shared static-track counts,
  selected neighbors and explicit rejections.
- `cloud-pilot-001/` and `cloud-cropped-pilot-001/`: point arrays, region labels,
  camera support, pixel observations, velocity flags, rejection counts, and
  exact executed matcher adapters. Crop records retain coordinate mappings and
  candidate-label votes.
- `inspection-pilot-002/` and `inspection-cropped-pilot-001/`: fixed-camera
  sparse/dense projections, motion overlays and per-instance coverage counts.
- `preview-pilot-001/` and `preview-cropped-pilot-001/`: native foreground-only
  PNGs and raw float arrays.
- `motion-audit-cropped-pilot-001/`: adjacent-frame tracked pixels and validity,
  per-instance supporting observations, and native KNN diagnostics.
- `segments/` and `ledger.jsonl`: separate measured GPU segments and logs.

One CPU inspection was launched before the coarse worker published its result;
it failed with a missing `result.json`. Its empty `inspection-pilot-001/` is
retained, and the successful inspection uses a new directory. No images or
prior outputs were overwritten to hide that failure.

The dense arm is stopped at its prerequisite gate. The independent STG and
sparse FreeTimeGS duration comparison continues. The complete nine-trajectory
study and its initialization/interaction/workflow comparisons remain incomplete.

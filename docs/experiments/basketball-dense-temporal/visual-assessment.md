# Available-arm visual assessment

The 50,000-update outputs still do not reconstruct detailed players. This
assessment covers all 12 fixed frame-22 player comparisons (four held-out
cameras × three seeds), the seed-0 court/display crops in all four cameras,
and decoded seed-0 video frames 0, 25, and 49 in all four cameras. The latter
samples confirm that the player failures are not confined to the reserved
interpolation interval. These are visual observations, not a new numerical
acceptance threshold or an additional experiment.

Both methods frequently represent black uniforms as diffuse dark silhouettes
and white uniforms as pale smears or nearly absent players. Individual limbs,
uniform numbers, and ball detail remain missing or unstable in the inspected
views. Some silhouettes become more distinct than at 5,000 updates, especially
for sparse FreeTimeGS, but they remain far from the source images. Better
background reconstruction must not be described as a solution to player
reconstruction.

Court lines and logos are much clearer than the players. Display crops retain
blur and incorrect digits, particularly in sparse FreeTimeGS. Their cause is
not identified by these observations. Calibration and synchronization were not
modified, and zero camera offsets remain an operational assumption.

The fixed player crops use the same frame and boxes selected from ground truth
before production endpoint inspection. Example copies are byte-identical to
the retained comparison PNGs:

| View | 5,000 updates | 50,000 updates |
| --- | --- | --- |
| Camera 0, players | [baseline](visual-examples/camera0-seed0-players-005000.png) | [endpoint](visual-examples/camera0-seed0-players-050000.png) |
| Camera 20, players | [baseline](visual-examples/camera20-seed0-players-005000.png) | [endpoint](visual-examples/camera20-seed0-players-050000.png) |
| Camera 0, court | [baseline](visual-examples/camera0-seed0-court-005000.png) | [endpoint](visual-examples/camera0-seed0-court-050000.png) |
| Camera 0, display | [baseline](visual-examples/camera0-seed0-display-005000.png) | [endpoint](visual-examples/camera0-seed0-display-050000.png) |

All examples show ground truth, STG Full, and sparse FreeTimeGS, left to right.
The dense arm has no trained output because its initialization prerequisite
failed. These are explicitly two-arm comparisons.

[Visual validation](visual-validation.json) records two bundles, each with
48 comparison PNGs and 12 videos. Every video contains all 50 source frames at
25 fps, without synthesized intermediate frames. All bundle artifact hashes
were checked. Large files are in
`.local/basketball-dense-temporal/visuals-005000-v2/` and `visuals-050000/`.
The decoded video contact sheets and source hashes are retained in
`.local/basketball-dense-temporal/video-inspection-050000/`; inspection of these
samples is not a claim that every video frame received manual review.

Metric conclusions remain separate from these observations. Frozen motion
regions are an image-difference proxy and may contain court, lighting, or
display changes; they are not verified player segmentation. Full paired
duration and workflow statistics belong in the final report.

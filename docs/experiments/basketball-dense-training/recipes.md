# Coarse and person-cropped dense initialization

These are **two recipes for building the initial 3D Gaussians before FreeTimeGS
training**. The difference is how they find corresponding pixels across cameras.

| Aspect | Coarse dense | Person-cropped dense |
|---|---|---|
| Initial matching | RoMa matches full camera images | Same full-image pass |
| Additional matching | Uses those predictions directly | Runs RoMa again on paired crops around people |
| Background and ball | Full-image matching | Full-image matching |
| Subsequent training | FreeTimeGS | Same FreeTimeGS model |

**The coarse recipe** processes the complete, calibrated 960 × 540 images. For
each reference camera, it matches three neighboring camera views. A
correspondence means, for example, "this pixel on a player's shirt in camera 1
corresponds to that pixel in camera 2."

It samples up to 5,000 candidate correspondences per camera pair. Approximately
half the sampling quota is distributed across detected people, with the
remainder drawn from the remaining image locations. Consequently, the coarse
recipe already gives people extra attention. "Coarse" names the full-image
matching approach; its output is still a dense initializer. See the
[matching and sampling implementation](../../../scripts/basketball_temporal_cloud.py).

**The person-cropped recipe** adds a refinement step:

1. Use the initial full-image correspondences to associate a person mask in one
   camera with a person mask in another.
2. Crop a bounding box around each associated person, adding approximately
   **10% padding on each side**, with a minimum of two pixels and clipping to the
   image boundaries.
3. Run the same pretrained RoMa matcher on those two crops.
4. Convert the predicted crop coordinates back into full-image coordinates,
   then replace the corresponding person-region matches and confidence scores.

The purpose is to give the matcher a closer view of the player. Arms, legs,
and clothing occupy more of its input, which may improve correspondence
accuracy. Mapping predictions back into full-image coordinates lets
triangulation use the existing camera calibration correctly. This is
implemented in `person_crop_warp()` in the
[dense cloud builder](../../../scripts/basketball_temporal_cloud.py).

The refinement requires additional matching calls and depends on the masks and
initial person association. Those associations are estimates, so cropping does
not guarantee better geometry.

**After matching, both recipes use the same preparation stages:**

- Triangulate matches into 3D and reject inconsistent geometry. Foreground
  points require agreement from at least three cameras.
- Estimate foreground velocities from adjacent-frame tracks; flag unsupported
  estimates and initialize them to zero.
- Fuse static observations and package positions, colors, velocities, temporal
  centers, and durations into the initializer.

See the [geometry and motion checks](../../../scripts/basketball_temporal_geometry.py)
and [fusion implementation](../../../scripts/basketball_dense_fusion.py).
The [shared code provenance](../basketball-code-provenance.md) explains which
components come from upstream repositories and which were added here.

For the [future workflow](../../../README.md), **either initializer uses all
recorded training frames and the duration repair from D**. Person cropping
happens during initialization; FreeTimeGS subsequently trains against the
complete camera images. The recipe choice is separate from those two training
settings. The [crossing explanation](../basketball-crossing-repair/workflow-explanation.md)
records their implementation and the evidence from the validated continuation
experiments.

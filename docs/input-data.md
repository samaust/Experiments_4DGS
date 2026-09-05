# Preparing input for dynamic Gaussian reconstruction

[Repository overview](../README.md) · [Research](research.md) · [Local creation](local-creation.md) · [Rendering](rendering.md)

This guide starts after the animated world has been generated. It describes what to retain and how to map it to existing research loaders. It does not implement a capture system or a universal dataset converter.

## Capture information to preserve

For every image, retain its camera identity, scene timestamp, camera intrinsics, camera pose, dimensions, and path. All cameras observing a particular timestamp must see the same animation state. A collection of plausible but geometrically inconsistent videos is not equivalent to synchronized observations of one world.

| Information | Recommended capture convention | Why it matters |
| --- | --- | --- |
| Images | Lossless RGB or RGBA frames; consistent exposure and color processing | Compression, independently changing lighting, or changing alpha backgrounds can be learned as false motion |
| Time | Preserve source seconds, frame number, and frame rate; normalize only in the method adapter | Different loaders normalize timestamps differently |
| Camera identity | Stable IDs across the sequence | Camera number must not be mistaken for time |
| Intrinsics | `fx`, `fy`, `cx`, `cy`, width, height, and distortion model | Resizing/cropping changes the pixel-space intrinsics |
| Extrinsics | Explicitly label camera-to-world or world-to-camera and axis conventions | Matrix inversion alone does not convert between all graphics conventions |
| Scene coordinates | One origin, orientation, and scale across all times/cameras | Per-frame recentering can erase motion or create apparent camera motion |
| Optional geometry | Depth definition, valid-depth mask, and points in the same coordinates | Provides a potential initialization route without estimating already-known cameras |
| Optional masks | Identify alpha, foreground segmentation, and invalid pixels separately | These have different meanings; a loader must explicitly support their intended use |

These are recommended capture records, not a new required file format. Archive originals separately from resized images, COLMAP work directories, and other preprocessing outputs.

### Camera and time checks

For a world-to-camera transform, `X_camera = R * X_world + t`; the camera center is `-Rᵀ * t`. COLMAP stores world-to-camera poses, with camera axes right, down, and forward. Blender/OpenGL camera axes differ. Use the selected loader's conversion, and verify known points project into the correct pixels. [COLMAP format reference](https://colmap.github.io/format.html)

Before training, inspect three synchronized time slices: beginning, middle, and end. In each slice, check that objects occupy compatible 3D positions in all views. Also verify the following:

- Every expected camera/time pair exists and names sort correctly, such as `00001` before `00010`.
- A moving camera has a pose for every frame; a fixed-camera loader must not silently reuse its first pose.
- Intrinsics match the decoded image size. Cropping requires a principal-point update as well as any scaling.
- The animation has a nonzero time span, consistent units, and no unnoticed loop boundary or camera cut.
- Camera frusta and initialization points use the same coordinate system and cover the intended scene bounds.

## HUST synthetic input: preserve known camera poses

Use the D-NeRF/Blender-style loader for the first synthetic experiment. Its inputs include `transforms_train.json`, `transforms_test.json`, and their referenced images. Each frame has `file_path`, `transform_matrix`, and `time`; the top-level horizontal field of view is `camera_angle_x` in radians. [Loader source](https://github.com/hustvl/4DGaussians/blob/843d5ac636c37e4b611242287754f3d4ed150144/scene/dataset_readers.py)

Example metadata shape for two observations from a fixed camera looking toward the origin from positive Z:

```json
{
  "camera_angle_x": 0.7,
  "frames": [
    {
      "file_path": "train/cam00_t00000",
      "transform_matrix": [[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, 4], [0, 0, 0, 1]],
      "time": 0.0
    },
    {
      "file_path": "train/cam00_t00001",
      "transform_matrix": [[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, 4], [0, 0, 0, 1]],
      "time": 1.0
    }
  ]
}
```

This illustrates fields only; it is not a sufficient training capture. Add the other cameras with their actual poses and the same timestamps. Supply the referenced `.png` images and a separate held-out test manifest.

Source-specific constraints: paths omit the image extension; timestamps are divided by the maximum time across train and test, so use a zero-based sequence with a positive maximum. The reviewed loader resizes to 800×800 and assumes a simple field-of-view camera. Start with square pinhole images. Arbitrary aspect ratios, offset principal points, or changing focal lengths need loader work. Alpha is composited against the configured background. [Synthetic-loader implementation](https://github.com/hustvl/4DGaussians/blob/843d5ac636c37e4b611242287754f3d4ed150144/scene/dataset_readers.py)

Keep evaluation enabled to preserve test separation; the reviewed CLI already defaults to it, and the walkthrough states `--eval` explicitly. If a configuration or adapter passes `eval=False`, the loader merges test observations into training. It initializes from `fused.ply` or a fixed synthetic-scene point region. Adapt initialization bounds and the camera path for a differently scaled world. [Split/initialization behavior](https://github.com/hustvl/4DGaussians/blob/843d5ac636c37e4b611242287754f3d4ed150144/scene/dataset_readers.py), [CLI defaults](https://github.com/hustvl/4DGaussians/blob/843d5ac636c37e4b611242287754f3d4ed150144/arguments/__init__.py)

## Multi-view loader mappings

| Implementation/input | Expected organization | Adaptation considerations |
| --- | --- | --- |
| HUST Neural 3D / DyNeRF | `poses_bounds.npy`, per-camera frame folders, and initialization points | Follow its Neural 3D loader and preprocessing. An LLFF pose/bounds array is not an arbitrary stack of 4×4 matrices. |
| HUST custom multiple-view | `cam01/frame_00001.jpg` etc.; derived `sparse_`, `points3D_multipleview.ply`, and `poses_bounds_multipleview.npy` | Use the actual custom loader/configuration. If poses are known, producing its derived metadata is adapter work; camera estimation is not intrinsically required by 4DGS. |
| SpacetimeGaussians Neural 3D | `colmap_0`, `colmap_1`, … with corresponding images and COLMAP sparse metadata | Use upstream preprocessing for the benchmark first; custom synthetic input must reproduce the loader's names and pose conventions. |
| NoPo4D | Camera-major image grouping plus timestamps and camera count | Its example uses four cameras × four frames. Feed-forward inference estimates cameras; evaluate whether that is preferable to preserving known synthetic calibration. |

Sources: [HUST data preparation](https://github.com/hustvl/4DGaussians#data-preparation), [HUST Neural 3D loader](https://github.com/hustvl/4DGaussians/blob/master/scene/neural_3D_dataset_NDC.py), [SpacetimeGaussians loader](https://github.com/oppo-us-research/SpacetimeGaussians/blob/427abfc/thirdparty/gaussian_splatting/scene/dataset_readers.py), [NoPo4D input API](https://github.com/bralani/NoPo4D#quick-start).

HUST detects the loader from files present in the scene root. A directory named `sparse` takes precedence over synthetic JSON and multi-view markers. Its generic COLMAP path assigns time by image order, so accidentally selecting it can corrupt synchronized time semantics. Keep method-specific prepared directories separate and inspect the reported scene type. [Dispatch source](https://github.com/hustvl/4DGaussians/blob/843d5ac636c37e4b611242287754f3d4ed150144/scene/__init__.py), [COLMAP camera reader](https://github.com/hustvl/4DGaussians/blob/843d5ac636c37e4b611242287754f3d4ed150144/scene/dataset_readers.py)

SpacetimeGaussians' Neural 3D reader reuses each camera pose across a window. It computes time as `(frame_index - window_start) / duration`; 50 frames therefore span 0 through 49/50. Do not substitute a 0–1 inclusive mapping or assume moving-camera support. Consistent per-camera image basenames across the `colmap_<frame>` directories are part of the mapping. [Reader implementation](https://github.com/oppo-us-research/SpacetimeGaussians/blob/427abfc/thirdparty/gaussian_splatting/scene/dataset_readers.py)

Known synthetic cameras can be written into an implementation's expected calibration format after conversion. If initialization needs triangulated points, use simultaneous views with those fixed poses, or investigate supported depth-derived points. Feeding all animation frames to a static-scene structure-from-motion pipeline can create inconsistent geometry. This is a proposed custom-data adaptation strategy, not a converter supplied by this repository.

## Evaluation split and failure cases

For custom captures, choose held-out camera IDs before training and retain their entire temporal sequences for novel-view testing. A separate temporal holdout tests interpolation; report it separately. Preserve benchmark splits when comparing with published results. Never describe training-camera replay or an all-camera pretrained checkpoint as held-out evaluation.

| Symptom | First checks |
| --- | --- |
| Double edges, translucent duplicates | Synchronization, camera poses, independently generated geometry |
| Scene mirrored or upside down | Camera axes, matrix direction, quaternion convention |
| Geometry drifts with time | Frame/pose alignment, normalization, moving camera treated as fixed |
| Good observed views, poor orbit | Coverage, occlusion, camera extrapolation beyond the capture |
| Flicker at chunk boundaries | Timestamp offsets, independently optimized chunks, missing continuity |
| Background artifacts | Alpha compositing, exposure changes, masking and color-space assumptions |

Keep at least one deliberately simple animated scene for debugging. Establish correct geometry, timing, and reloading before increasing resolution, duration, or world size. Continue with the [local creation guide](local-creation.md).

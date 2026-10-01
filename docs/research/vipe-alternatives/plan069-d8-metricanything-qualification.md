# D8 MetricAnything PointMap adapter qualification

**Status:** CPU fake-runtime qualified. Native weight bytes, bundled-runtime
compatibility, installed dependency terms and GPU profile await admission.

D8 pins [MetricAnything source `616a5e6762f5fc40d1a4ef990fee04c800532f59`](https://github.com/metric-anything/metric-anything/tree/616a5e6762f5fc40d1a4ef990fee04c800532f59)
and [PointMap student revision `8f1f08c53c683d4e19864601dfaf78515f29a63b`](https://huggingface.co/yjh001/metricanything_student_pointmap/tree/8f1f08c53c683d4e19864601dfaf78515f29a63b),
file `student_pointmap.pt`. The source and exact model card identify Apache-2.0;
separate third-party terms must be checked in #55. Record actual checkpoint
bytes and SHA256 before any model load. The PointMap student is 326M
parameters. [Pinned release README](https://raw.githubusercontent.com/metric-anything/metric-anything/616a5e6762f5fc40d1a4ef990fee04c800532f59/README.md),
[model card](https://huggingface.co/yjh001/metricanything_student_pointmap).

Use the **bundled** `models/student_pointmap/moge/model/v2.py` loader and
`MoGeModel.infer`, not the separate DepthMap student or the D5 upstream source
checkout. The bundled loader requests `student_pointmap.pt`; its native
inference supports `fov_x` in degrees. D8 deliberately supplies the accepted
horizontal FoV, while the release's example script uses predicted FoV
(`fov_x=None`). Keep `resolution_level=9`, `force_projection=True`,
`apply_mask=True`, `use_fp16=True`, eval mode and no stochastic sampling.
Require returned normalized intrinsics to equal the supplied camera. Preserve
native point/depth arrays and use z-depth directly in metres without another
focal or radial conversion. [Bundled native source](https://raw.githubusercontent.com/metric-anything/metric-anything/616a5e6762f5fc40d1a4ef990fee04c800532f59/models/student_pointmap/moge/model/v2.py),
[release example](https://raw.githubusercontent.com/metric-anything/metric-anything/616a5e6762f5fc40d1a4ef990fee04c800532f59/models/student_pointmap/infer.py).

The pinned bundled requirements request `torch<2.5.0`, torchvision, Gradio,
click, OpenCV, SciPy, Matplotlib, Trimesh, Pillow, Hugging Face Hub and
`utils3d` at `3fab839f0be9931dac7c8488eb0e1600c236e183`. Audit the
bundled MoGe/DINOv2 source and installed wheel licenses. The bounded
execution proposal must confirm a compatible isolated environment, measure
first load, 256 independent inferences at most (60 anchors plus 196 clip
frames), peak GPU memory, CPU publication and artifact size under the 22 GiB
ceiling. [Pinned requirements](https://raw.githubusercontent.com/metric-anything/metric-anything/616a5e6762f5fc40d1a4ef990fee04c800532f59/models/student_pointmap/requirements.txt).

CPU tests reject an alternate checkpoint, predicted-camera output and a wrong
grid. The 30-camera fit/check fixture reuses its frozen fit through worker,
scale and frame package boundaries. No native GPU result is claimed.

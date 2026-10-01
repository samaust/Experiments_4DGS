# D6 MoGe-3 adapter qualification for Plan 069

**Status:** CPU fake-runtime qualified. Exact native weight bytes, GPU memory,
runtime and installed dependency terms await separately admitted setup/run.

D6 pins [MoGe source `74fbce054ebed49800de42d0ad0e83495065719a`](https://github.com/microsoft/MoGe/tree/74fbce054ebed49800de42d0ad0e83495065719a)
and [Ruicheng/moge-3-vitl revision `184008f877d7ad1ad4c2cd2182a9bd1f63d0e5be`](https://huggingface.co/Ruicheng/moge-3-vitl/tree/184008f877d7ad1ad4c2cd2182a9bd1f63d0e5be).
The release and model page label source/weights MIT, subject to the separate
transitive dependency inventory in #55. The asset is `model.pt`; record its
actual SHA256 and size before execution. The exact source/dependency list is
in the [D5 inventory](plan069-d5-moge2-qualification.md); MoGe-3 additionally
uses its sparse 3D refiner and pinned FlexGEMM dependency.

Use [`moge.model.v3.MoGeModel.infer`](https://raw.githubusercontent.com/microsoft/MoGe/74fbce054ebed49800de42d0ad0e83495065719a/moge/model/v3.py)
with the accepted horizontal FoV, `resolution_level=9`,
`force_projection=True`, `apply_mask=True`, **`refine_steps=3`**,
`return_per_step=False` and native default `use_fp16=False`. The adapter
requires returned normalized intrinsics to agree with the supplied camera,
preserves final native point/depth arrays, and outputs float32 camera-z metres
with NaN invalid pixels. It rejects changed grids and all-invalid metric maps.
Native `infer` applies metric scale; no focal or point-norm conversion is added.

The README lists 370M parameters for the ViT-L release. D6 has 60 anchors and
at most 196 additional clip frames, inferred independently. The sparse
refiner's memory and latency on this host need measurement under the 22 GiB
device cap; the D5 CPU fixture timing is not a D6 GPU estimate. Admission must
record first-load memory, three-step per-frame runtime, artifact bytes and
CPU clip publication cost before a bounded attempt. [Pinned README](https://github.com/microsoft/MoGe/tree/74fbce054ebed49800de42d0ad0e83495065719a).

CPU tests cover the exact three-step call, supplied-camera rejection,
wrong-grid and invalid-metric rejection, and the immutable 30-camera
worker→scale→package fixture. They make no claim about native GPU output.

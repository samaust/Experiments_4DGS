# Local two-view triangulation

For column-vector projection `P = K[R|t]`, an undistorted observation `(u,v)`
obeys `u = p1 H / p3 H`, `v = p2 H / p3 H`, where `H = [X,Y,Z,1]`.
Thus `(u p3 - p1) H = 0` and `(v p3 - p2) H = 0`.
Stacking these equations for two cameras gives four rows `M`. Set
`A = M[:, :3]`, `b = -M[:, 3]` and minimize `||A XYZ - b||₂`.
This is unweighted inhomogeneous least squares, without normalization,
regularization, normal equations, or homogeneous DLT.

This derivation was recorded before implementation for Plan 029. The repository
previously inspected and extracted EDGS helpers; this work is independently
derived from the plan's mathematics and public PyTorch APIs, not a claim of a
clean-room process or legal clearance. Existing source, licenses, archives, and
historical reports retain their provenance.

The helper screens nonfinite equations and requires
`sigma_min > rank_rtol * sigma_max` before invoking batched
`torch.linalg.lstsq(..., driver="gels")`. The default threshold is four times
the requested dtype's epsilon. CUDA gels assumes full rank; its `rcond` does
not replace screening. See the [PyTorch least-squares API](https://docs.pytorch.org/docs/stable/generated/torch.linalg.lstsq.html).
Invalid correspondences retain their indices and receive NaN XYZ and false
validity. Validity establishes numerical solvability only; caller depth,
reprojection, parallax and semantic checks still apply. No pixel-center shift
is applied. Production calls use float32 on CUDA; execution failures propagate.

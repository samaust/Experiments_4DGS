# Plan 071: D6 runtime replacement and maps retry

Approved by the user on 2026-10-05 (`depth-D6-runtime-replacement-authority-001.json`) after D6 maps-001
failed: flex_gemm 1.0.0 uses Triton `dtype.itemsize`, absent from the accepted setup's Triton 3.2.0.

Feasibility (CPU probe, no installs): the run's own `setup-cache` resolves and dry-run installs the D6
requirements offline with torch 2.14.1+cu130 / torchvision 0.29.1+cu130 / triton 3.8.0 / numpy 2.1.3,
indexes pypi + cu130 + cu124. Triton 3.8 has `dtype.itemsize`.

## Milestones

A. **Runtime-replacement recovery.** `plan069-D6-setup-recovery-001` in the recovery table with a
   `superseded_complete` original; D6 profile `depth_moge_runtime_replacement.py`; runner reusing the
   accepted source, checkpoint and derived flex_gemm archive, provisioning a new runtime offline (zero
   downloads). Result is a drop-in for the MoGe setup result. Ledger byte limits for this offline job are
   the global caps; the job enforces zero downloads and the amended whole-slot artifact budget.
B. **Run A** (setup resource, ~minutes), preserve outcome.
C. **Requalification on the new runtime.** Triton 3.8 helper cache (built via `CudaUtils()` with a bound
   `TRITON_LIBCUDA_PATH`, the worker sets the same path), method-012 accepting the recovered setup, attempt
   009 whose lineage switches setup only through the accepted recovery, source review, CPU capture,
   commercial rebind (new dependency manifest needs fresh licence comparison), finalize.
D. **Maps-002.** `RETRIES['D6']` with pinned approval after the clean zero-output maps-001; dispatch; clips;
   outcome; formal #59 package; close #56/#59.

Each milestone: tests, mypy, independent review, commit; CPU charged; GPU steps checked first.

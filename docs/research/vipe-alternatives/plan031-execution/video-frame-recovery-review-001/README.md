# D9 recovery / D10 frame-input amendment — REVIEW

D9 setup001 failed at strict `uv pip check`, after packages and immutable source/checkpoint were acquired. The published Decord wheel is named `decord-0.6.0-py3-none-manylinux2010_x86_64.whl`, but its installed WHEEL declares `cp36-cp36m-manylinux2010_x86_64`. The actual environment is Python 3.11.15. This establishes incompatible declared metadata; it does not establish a UV false positive or prove binary usability.

## Proposed fix

Use a new immutable v4 recipe that removes only optional CLI Decord from the previous 49-package dependency closure. Keep all other 48 pins, official PyPI Torch 2.14.1 / TorchVision 0.29.1, CUDA 13.0 observations, original upstream requirements, source/checkpoint and scientific settings. Keep strict `uv pip check`. Explicitly capture and require installed Decord and Xformers absence.

The native adapter receives RGB frame arrays and imports `video_depth_anything.video_depth` and `utils.util`. Static traversal of the acquired pinned source reaches neither `decord` nor `utils.dc_utils`; the latter is used by upstream CLI `run.py` and includes an OpenCV fallback when Decord is unavailable. Static inspection and the fake adapter smoke test supply CPU preparation evidence. They do not establish actual runtime qualification or visual quality.

## Recovery and approval boundary

D9 setup001 remains failed and its maximum one attempt consumed. Preserve its environment, lock, source, checkpoint, protected grant/finish and byte checkpoint. Propose a distinct `plan069-D9-setup-recovery-001`, one attempt, at most 1,200 setup seconds, a new environment and offline exact cached dependencies. Preserve the combined original/recovery 6 GiB dependency and 9 GiB artifact caps and all earlier charges; no new independent allowance. Reuse assets only with exact records and approved causal lineage. Do not mutate the failed environment or rewrite its receipts.

A fresh REVIEW and explicit approval must bind both the recovery proposal and updated v4 standard D9 map proposal before a new DO can authorize execution. D10 has not started; it needs an explicit reviewed v4 amendment. Existing v3 DO authority rejects v4. This packet has **no execution authority**. Its `proposal-fragments.json` is a draft input to the root-owned protected recovery authority, not a dispatchable proposal.

## Evidence and verification

- `failure-evidence.json`: exact local Decord WHEEL, source, failure and primary published-distribution records.
- `native-import-evidence.json`: hashed local static import closure, with explicit limitations.
- `inspect_native_imports.py`: reproducible read-only evidence producer; it never imports models.
- `cpu-validation.json`: 56 video unittest cases passed; four modified modules passed mypy; independent Standards and Spec reviews found no actionable findings.

No package installation, network access, model/binary import, GPU operation, production ledger mutation or live environment change occurred in this preparation.

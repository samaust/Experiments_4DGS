# Retained D8 CPU qualification method

**Prepared method; not an actual qualification receipt.** No D8 setup, install,
model/asset read, model execution, network, GPU job or live ledger event occurred
while writing this method. Fixture files are synthetic.

The method is derived from retained MoGe CPU method002, using native D8 setup's
inline `runtime` result and `environment` request. It preserves the exact approved
Torch2.14.1+cu130 / TorchVision0.29.1+cu130 profile and original source constraint
exception. A separate minimal production correction handles uv's permitted empty
PEP610 archive hashes for pinned offline utils3d (commit1b1738c0); integrate it
only after the current source freeze, then refresh source qualification.

## Actual root-owned phases after accepted setup

1. Verify exact canonical completed D8 setup, request and dispatch, one accepted
   setup ledger reservation and cleanup-confirmed finish; approved DO002 and
   current production recipe; exact source/weight pins and asset bytes.
2. Run `capture` through the root's separately admitted, measured CPU wrapper.
   It invokes only the prepared interpreter with CUDA hidden, offline flags,
   isolated owned caches, a new process group, finite wall/artifact limits and
   retained terminal failure evidence. The launcher does not authorize or charge
   CPU work. Root independently checks full descendant cleanup and charges every
   attempted phase, including failed preflight and finalization.
3. The child checks complete installed inventory/lock/command receipts, exact
   original recipe and native package provenance, verified source manifest and
   checkpoint. It constructs the same pinned bundled MoGeModel used by
   native_d8, loads `weights_only=True`, `map_location=cpu`, strict state loading,
   eval mode **twice**, then releases each model. It never invokes infer or CUDA.
   CUDA initialization is rejected before importing the native model. Python
   network/process audit guards supplement the root wrapper; they are not a
   native syscall or network namespace sandbox.
4. Independently assess exact code, weight, installed dependency and inference
   output terms against the generated installed-dependencies manifest. No model
   card alone may substitute for the actual dependency/license closure.
5. Create a **fresh postsetup source review** that repeats the verified archive
   and nonempty absolute source-file records, current helper records, exact
   source revision and profile inventory. Pre-setup source002 is preserved and
   cannot substitute for this review. Source manifest entries are relative;
   `source_files()` verifies every byte and safely materializes absolute records.
6. Run `finalize` under the same separately bounded CPU review policy. It rehashes
   immutable source/archive, interpreter, installed dependency bytes, asset
   inventory and commercial/source receipts. It writes matching `source_archive`
   and `source_files` into runtime and top qualification receipts. These fields
   also match the independent source-review receipt exactly, enabling completed
   metric-chain review after the later actual admitted native job.

Commands are prospective; substitute accepted paths and admitted bounds:

```bash
<root-cpu-wrapper> <host-interpreter> producer.py capture --root <canonical-checkout> --candidate D8 --setup <accepted-result.json> --setup-request <accepted-request.json> --setup-dispatch <accepted-dispatch.json> --output <fresh-capture-dir> --seconds <at-most-180> --artifact-bytes <admitted-limit>
<root-cpu-wrapper> <host-interpreter> producer.py finalize --root <canonical-checkout> --candidate D8 --capture <passed-capture-dir> --commercial-assessment <exact-assessment.json> --source-review <fresh-postsetup-review.json> --output <fresh-final-dir>
```

The final runtime receipt explicitly leaves GPU model loading, numerical inference
and peak device memory unmeasured. Source/CPU qualification is not successful
actual native inference or a human quality judgment. Actual native compatibility
must be demonstrated within the single previously approved D8 job; no additional
GPU smoke attempt is introduced.

## Fixture verification

Four synthetic CPU tests cover materialization of the accepted relative source
manifest, completed metric-chain acceptance through
`depth_review._completed_qualification(actual=False)`, rejection of missing
archive/source-file bindings and an old pre-setup review, changed source and
installed dependency bytes, and exactly two strict fake CPU loads with inference
and CUDA prohibited. Mypy passes for the method and patched provenance helper.
These fixtures do not import or load D8's model or weights and do not qualify an
installed D8 runtime. Measurement receipts distinguish test/preparation phases
from future actual qualification and ledger charges.

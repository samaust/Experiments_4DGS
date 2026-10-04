# Canonical pre-setup D8 refresh004

Independent source review004 binds canonical commit
`76b0b9a02fb6d9c9bfb0fc12ec8558006a0582a6`. All 40 ordered production helper
records were rehashed; only `ledger.py`, `depth_admission.py` and
`depth_authorization.py` differ from source003. The receipt also records three
D6 driver dependencies used by generic ledger handling, separately from the
production D8 source list.

The reviewed changes keep D6 driver exceptions and D9/D10 runtime amendments
candidate-specific. Historical D6 driver ledger reconstruction uses
`completed=True`. Generic `ledger.note` now rejects unchecked depth setup,
attempt and native qualification grants. D8 retains its original runtime
profile, code and weight revisions, DO002, allocation and attempt limits.

The exact environment record from source003 is preserved, and the production
D8 recipe equals its retained content. The existing selector source and its
focused validation receipt also remain exact. The successful metadata checker
took 0.060926745 seconds; this excludes earlier investigation and review
reasoning. No shared ledger charge or execution authorization was written.

This is a pre-setup source review. It establishes no installed dependency
closure, acquired source archive, checkpoint load or CUDA compatibility.
The previously recorded cu130 metadata sidecar HTTP 403 remains unresolved;
this review performs no transfer or retry. Actual setup and subsequent runtime,
license and CPU qualification remain separate gates owned by the integration
agent.

Historical source reviews, environment records and preparation measurements
remain unchanged. Source004 and `canonical-source-verification-004.json` are
new immutable evidence.

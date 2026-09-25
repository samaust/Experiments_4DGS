# Correction018 plan 001 — qualify the invoked interpreter symlink safely

## Finding

The focused run with exact Main handle 25297 reached all 114 deadline-step subcases and completed in 83.806 seconds, exiting 1 with 111 passes, one error and two cascading failures. The Correction017 child-close control passed. `runtime_guard/before` then raised `ELOOP` on the admitted interpreter spelling `.../bin/python`, which is a symlink to `/usr/bin/python3.14`; `s1_evidence.qualify_runtime` sends that spelling to `s1_progress.checked_file_record`, whose deliberate `O_NOFOLLOW` rejects the final symlink. The runner’s captured executable record is canonicalized to the target. Independent triage [focused005 runtime-guard triage](correction017-focused005-runtime-guard-triage-001.md), SHA-256 `f8473c646f3a11a62500d24d7c3e95c758afdd352eeef4aa37d6a931efaee0ee`, confirms this is a production-path mismatch, not a flaky fixture; a fixture-only adapter would mask it.

## Authorized narrow correction proposal

Add `scripts/vipe_benchmark/s1_evidence.py` and the exact `runtime_guard` portion of `tests/test_vipe_benchmark_supervisor.py` as the only paths for this correction. In `qualify_runtime`, preserve exact equality between the invoked spelling and the admitted request/manifest identity, but resolve that exact request path strictly under the existing deadline gate, require the resolved canonical target to equal the manifest’s executable path, and run the existing no-follow `checked_file_record` only on that canonical target. Require complete file-record equality (canonical path, byte count and digest), then re-resolve the invoked path under the deadline gate after reading and require the same target, so a persistent symlink substitution cannot bind an unrequested file. Do not enable generic symlink following, alter other record/read APIs, relax any runtime/inventory identity check, change setup/work/cleanup deadlines, or weaken tests. Keep the existing `runtime_guard` before/equal/after subtests and all 114 declared cases unchanged. Within the existing before subtest, add negative production-path controls proving rejection of an alternate invoked symlink spelling despite the same target, a mismatched manifest record, and a target substitution between the two resolutions; these controls must call `qualify_runtime` itself without the fixture-only adapter. Before must complete for the real admitted symlink; equality/after must still reject work at W.

## Work sequence

1. Obtain independent review of this plan and exact path/algorithm before editing. Main will adopt only the exact PASS-reviewed plan hash.
2. Implement the two deadline-gated resolutions and canonical-target byte verification in `s1_evidence.py`, plus the bounded negative controls inside the existing `runtime_guard/before` fixture portion in `tests/test_vipe_benchmark_supervisor.py`. Add no subtests or deadline cases.
3. Obtain independent exact-source review before focused execution.
4. Run only the existing deadline-step method with a fresh source-hash, artifact, process/thread-capacity and output preflight; preserve all existing 114 subcases and the 2-second work/1-second safety behavior. Record every error and duration. A focused pass is not a full diagnostic admission.
5. Continue remaining Correction017/Plan031 reviews and serial checks. This plan authorizes no full diagnostic, aggregate, admission, process signal, resource-cap change, or execution deadline change.

## Evidence and constraints

Correction017’s child-retirement follow-up remains adopted and independently source-reviewed. The focused run’s exact output/terminal evidence is in `correction017-focused-005`; its sandbox-denied attempt remains a separate failed setup record and the escalated test result remains failed historical evidence. Plan049’s CPU-only serial scope, `B+max(1,H)≤8`, 150 GiB artifact cap, all original assertions/deadlines and failure-preservation requirements remain controlling. The visible kernel boot ID has not changed from the prior reboot record, so retain the conservative historical H=2 charge until separate reviewed retirement evidence establishes otherwise.

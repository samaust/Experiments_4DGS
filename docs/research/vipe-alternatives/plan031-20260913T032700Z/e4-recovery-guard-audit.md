# E4 recovery authorization guard audit

The controller permits `changes_to_prescribed_runtime: true` only for E4 when
the authorization declares `runtime_amendment: plan031-e4-cu130-20260919` and
the active E4 runtime targets exactly match Python 3.11, torch 2.13.0+cu130,
torchvision 0.28.0+cu130, and NumPy 2.1.3. The authorization remains a verified,
hash-bound record in the append-only recovery event.

All existing recovery checks remain: explicit authority, one attempt per
authorization, sequential identity, original and previous cleaned-up failure
binding, passing source-bound validation, no active attempt, cumulative setup
ceiling, and preservation of previous charges. E1/E2/E3 still reject runtime
changes, including declarations of this E4 amendment.

Validation: `.local/envs/stg-colmap/bin/python -m unittest discover -s tests -p
test_vipe_benchmark_setup_recovery.py` passed **23 tests**. Four added tests cover
the exact E4 exception and recipe pins (including torchaudio), absent/wrong
declarations and each changed runtime target, other environments, and scope,
history, failure binding, retry and validation guards. Initial launcher checks
found no `python` executable and no NumPy in system `python3`; the existing
project test environment ran the suite successfully after correcting the new
fixture's attempt to overwrite an immutable validation file.

This audit qualifies the controller guard only. No setup attempt, network
request, model forward, native compatibility check, or local commit was made
for this guard work. Authorization-004 must include the amendment declaration
and refreshed repair-validation hashes before registration.

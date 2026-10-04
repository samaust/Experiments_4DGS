# Retained D6 proof under locked admission

Admission forwards its current `setup_events` and `run_root` into both retained
qualification validators. The shared reader checks the exact receipt ledger
path, run root, current read-only ledger bytes and hash chain, and requires the
supplied events to match. It avoids taking a second file lock. Standalone calls
retain the existing locked read. Request and retained receipt ledger paths must
also match. Qualification002 additionally requires its explicit reviewed worker
to equal the request worker.

A bounded subprocess reproduced the public admission deadlock while holding a
real private ledger lock. After correction, 35 focused CPU cases pass, including
both retained proof versions, stale/forged events, a foreign run root and the
missing worker binding. Mypy passes for the three changed modules. Independent
Standards and Spec reviews report no actionable findings. The final annotation
fix only adds the type of the checked event list.

Private immutable command captures include the failed TDD run, both passing
test runs, the failed type check and its corrected passing run. No production
ledger, actual model, GPU, installation or network operation was performed.
The new implementation requires fresh reviewed and qualified source bindings
before an actual attempt; it grants no execution authority.

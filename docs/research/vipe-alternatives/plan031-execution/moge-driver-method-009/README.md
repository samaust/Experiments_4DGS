# D6 driver method 009 (qualification006)

Method 008 with one fix. Qualification005 (`depth-D6-driver-outcome-005.json`)
failed before CUDA initialization: `driver_child` re-binds `request` to the
setup request before the Triton cache block, so it read `triton_cache` from the
wrong record (`KeyError`). Method 009 keeps the early-verified qualification
request as `qualification` and binds, re-checks and reports the Triton helper
cache from it. It serves only qualification006.

Everything else is unchanged from method 008: `network_guard.py` is
byte-identical to methods 007/008, `startup.py` differs only in labels, and the
worker keeps every limit (no child processes, no inference, forward, benchmark
or kernel launch, two strict CPU loads, zero GPU allocation).

# Plan053 correction 002 — terminal poll binding and durable stop evidence

This correction responds to [correction001 source review 001](validate-049-plan053-correction-001-source-review-001.md), verdict NEEDS_CORRECTION. It stays in the nine existing Plan053 paths, the existing CPU-only focused test scope, and all unchanged Plan049/Correction015 gates. It grants no diagnostic or aggregate launch.

## Criteria

- C1: direct matching-child descendant retirement must compare `pid` and `wait_status` with its completed terminal `WNOHANG` poll; mismatched status/pid and another poll after terminal remain rejected.
- C2: poison-marker write, readback, and fsync errors must not be swallowed or represented as a durable stop. The append operation must fail closed and include the marker persistence failure in its surfaced evidence.
- C3: exercise cap/rollback stop behavior through a bounded fresh Python process using the exact sidecar marker; verify append rejection and byte-for-byte preservation of the committed ledger prefix. The parent must retain and wait its exact child PID and process result.
- C4: rerun the focused execution mutation method, affected ownership tests, syntax/diff/hash checks, and regenerate a new exact nine-path manifest. Obtain a separate exact-hash independent review PASS before any diagnostic.

The prior [implementation report](plan053-correction-001-implementation.md) and [source review](validate-049-plan053-correction-001-source-review-001.md) remain immutable evidence. No historical failure is overwritten.

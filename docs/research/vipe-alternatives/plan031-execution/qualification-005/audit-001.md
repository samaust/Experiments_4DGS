# Retrospective capture005 audit

The capture005 timeout and its immutable files remain unchanged. During the
Plan067 implementation, inspection of `process-stderr.log` found four errors
before the timeout: the historical S1NextIdentityTests used current AGENTS.md
bytes against process-file amendment001. The earlier OUTCOME.md statement that
no test failure appeared before termination was incorrect. Capture005 was
already classified as failed qualification; it is not newly qualified by this
audit.

The same four errors were reproduced in the full repository suite. Test-only
commit `44005468` supplies hash-verified historical AGENTS.md bytes only inside
historical admission contexts and retains current-byte rejection. Sixteen
focused historical005/current006 tests passed. Production preservation gates,
amendments and live ledger were not changed. A fresh passing current-source
capture is still required before a new S1 or E5 attempt.

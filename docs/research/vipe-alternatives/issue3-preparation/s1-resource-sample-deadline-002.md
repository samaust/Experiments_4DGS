# S1 resource-sample deadline: two seconds

On 2026-09-29 the user explicitly requested increasing the one-second S1 resource-sample deadline to two seconds after recovery004 timed out before model launch. This is a runtime monitor change. It does not allocate or reopen an attempt.

`RESOURCE_SAMPLE_SECONDS = 2.` in `s1_helper_session.py` is shared by sample request dispatch and acquisition timestamp validation. The effective deadline remains the earlier of the caller's phase/job deadline and dispatch plus two seconds. Receipts at or after that deadline remain invalid. Monitor tick, GPU exclusivity, resource ceilings, cleanup, and cumulative allocation checks retain their existing behavior.

Two new real-child CPU regression tests reproduced the old failure before the repair: a 1.05-second sample timed out, and a slow sample was rejected after about one second. After the repair, a 1.05-second prelaunch sample passes and a 2.05-second sample times out at two seconds. Pure timestamp checks cover acceptance at 1.5 seconds, rejection at two seconds, and rejection at a shorter caller deadline. Late-reply fixtures now delay 2.05 seconds so their recovery, foreign-PID, resource-ceiling, and late-census checks still exercise expired samples.

The initial direct supervisor-suite invocation lacked its required process-group leader and failed the `progress process group` fixture precondition. The source-bound qualification uses the prescribed isolated runner. Historical qualification receipts and the failed recovery004 ledger are preserved.

Recovery004 remains consumed. The prior successful source qualification005 describes the older source; qualification006 records this change. Further model execution requires its applicable admission and allocation authorization. This change does not resolve the separately recorded terminal-publication failure or claim successful calibration.

Qualification006 passed 281 tests / 1030 subtests in 228.189 seconds within the 240-second cap. The exact 79-source set was stable across execution, and the validation wrapper passed its strict verifier. The live 472-event ledger remained byte-identical to the preserved post004 snapshot.

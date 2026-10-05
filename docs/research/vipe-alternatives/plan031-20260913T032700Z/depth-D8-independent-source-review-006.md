# D8 source006 independent review (setup recovery)

Canonical commit: `7d6b1101`. Previous passing review: source005 at `7374af21`.
Every D8-closure change since source005 belongs to Plan 070 (#63) and passed
independent Standards and Spec review per ticket before this freeze:

| Ticket | Commits | Standards | Spec |
| --- | --- | --- | --- |
| #64 setup-recovery core | `8039702e`, `7c01d596` | PASS | PASS (after completion commit) |
| #66 D8 recovery authority | `2359400a`, `1547ca31`, `6979e4fc` | PASS (after fixes) | PASS (hardening adopted) |
| #68 offline recovery runner | `2db5cbc0`, `fef6c7c4` | PASS | PASS (after pre-install lock gate) |
| #67 recovered maps admission | `5d1777c1`, `0d699688` | PASS | PASS (after gap fixes) |
| #69 recovery dispatch | `4916349e`, `f639c0a4` | PASS (after hardening) | PASS |

The closure grew from 43 to 47 records (`setup_recovery_core.py`,
`setup_recovery_candidates.py`, `depth_native_setup_recovery.py`,
`basketball_vipe_depth_setup_recovery.py`). This review binds the recovery
proposal `docs/specs/plan031-execution/depth-D8-setup-recovery-review-001.json`.

Known recorded deviations: setup-byte reconciliation refuses a recovered D8
(conservative over-charge risk for the earlier-granted D6 slot, noted on #56);
resolver metadata and cache-miss refetches stay online through the metered
proxy, pinned to the original reviewed hashes.

This pre-setup review establishes no installed runtime or CUDA compatibility
and grants no execution authority.

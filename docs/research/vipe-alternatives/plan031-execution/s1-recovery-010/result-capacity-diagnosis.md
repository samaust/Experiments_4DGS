# S1-010 aggregate result capacity diagnosis

S1-010 consumed its single immutable allocation and individually qualified
510 rows. Final progress publication failed after 2201.842337 seconds with
confirmed cleanup, no surviving processes and `stop_required: true`. The
helper traceback ends in `_accepted_progress` calling `read_bytes` on
`result.json` with the 32 MiB `MAX_METADATA` limit, raising
`progress regular file capacity`.

The actual result is **35,338,620 bytes**. Its scanner counts
**1,726,556 nodes**, above the old aggregate decoder's 1,048,576-node cap.
Its largest canonical row is 63,218 bytes and its outer metadata is 2,321
bytes. The failure therefore comes from applying a single metadata-object
budget to the complete 510-row aggregate. Changing only the read byte limit
would leave the node limit as the next failure.

The same result byte/node ceiling affected `candidate_inventory` read and
decode, raw-result plus canonical-row inventory accounting, and
`ClosedInventory.recheck`. All these result paths now share finite aggregate
bounds. `decode_result` limits the result to 510 times the prescribed 256 KiB
row allowance plus the existing 32 MiB envelope allowance: **167,247,872
bytes**. Its node budget is 510 times the existing 65,536 per-row allowance
plus 1,048,576 envelope nodes: **34,471,936 nodes**.

The envelope is checked independently against 32 MiB and 1,048,576 nodes.
Every canonical row retains its 256 KiB, 65,536-node and original depth/string
guards. Inventory accounting is bounded by the raw aggregate allowance plus
2048 candidate row projections: **704,118,784 bytes**. The early 2048
forensic-candidate bound and exact 510-row accepted-result check are preserved.
Control messages, checkpoints, identity membership, strict no-follow reads,
hash bindings, closure membership and deadlines retain their existing guards.

CPU regressions exercise a real 510-row aggregate above 35 MiB and above the
old aggregate node budget, candidate freezing/rechecking, acknowledged final
progress publication and cold recovery. They also reject changed result
bytes, sparse files above the finite aggregate bound, oversized rows and
envelopes, and row/envelope node overflow. Existing endpoint tests retain
explicit smaller injected budgets for affordable numeric boundary tests and
assert the production arithmetic; existing closed-inventory guards also run.
The three new tests and existing closed-inventory fault method passed in
7.143 seconds. The existing capacity endpoint method passed in 15.588 seconds.
Strict qualification collection includes 13 suites and all three new tests;
the current source inventory contains 104 files.
The actual failed S1-010 result decoded read-only in 1.835 seconds after the
correction. This check does not accept or promote it.

The local acceptance artifact is unpublished evidence only. The consumed
S1-010 finish remains failed with absent accepted result and stopped helper
history. This source correction authorizes no replay of identity 010; the
standing retry controls require a fresh 011 linked to its exact failed finish,
diagnosis, independent review and new source qualification. No GPU execution,
live ledger writes, model operations or environment changes were performed.

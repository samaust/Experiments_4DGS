# Prospective UV command receipt ownership

CPU preparation only. No UV command, network connection, installation, model load,
GPU operation or shared ledger mutation was performed for this milestone.

Baseline: `5265ce97`; branch `plan069-uv-owner-receipts`, isolated worktree
`.local/plan069-worktrees/uv-owner-receipts`.

`transfer_proxy` exposes `receipt_path` after its exact proxy context has stopped
and completed cleanup. The completed receipt must have the same hexadecimal
transfer ID and owned path, `complete: true`, explicit `error: null`, zero reserved
bytes and a nonnegative integer received-byte count. Failed, live, missing,
symlinked or mismatched receipts cannot establish ownership.

After the real UV command's proxy context exits successfully,
`depth_environment` stores `uv_transfer_receipt: file_record(proxy.receipt_path)`
in that actual command receipt. Its literal command, immutable log and this exact
transfer record are now linked. Non-UV commands and injected fixture runners store
`uv_transfer_receipt: null`. Historical command/transfer receipts are unchanged;
no historical attribution is inferred from timestamps, global deltas or old logs.

The parent owns protected before/after setup checkpoints and later-growth credit.
This binding alone grants no credit. A consumer must verify the accepted setup
result/command receipt/transfer record and protected checkpoint lineage, deduplicate
transfer identities, and preserve unchanged global and candidate caps. Installed
runtime inventories plus metadata-only inode snapshots can separately prove newly
retained shared-cache payloads; no full tree content hashing is introduced here.

Validation: 12 socket-free CPU unittest cases passed in 0.068 seconds, including
six malformed-receipt subcases; fixture ownership, absent error, and missing public
receipt boundary were red before their relevant implementation. Four changed Python
files parsed successfully. No available typechecker was installed. The integration
owner's combined full suite must cover the existing localhost proxy context cases.

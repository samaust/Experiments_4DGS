# Conditional D10 authorization publisher

`prepare_D10.py` adds executable publication controls. It has not published an
actual DO, granted an attempt, or modified a production ledger. D10 remains at
REVIEW until an explicit user approval and accepted actual D9 recovery002 CPU
qualification are available.

## Required approval input

Supply a fresh immutable JSON file with these fields. This is a schema example,
not an approval:

```json
{
  "schema": "plan069-D10-frame-user-approval/v1",
  "status": "approved",
  "candidate": "D10",
  "review": {"path": "<exact D10 REVIEW path>", "sha256": "<SHA256>", "bytes": 0},
  "proposal_sha256": "<canonical hash of the single D10 proposal>",
  "max_attempts": 1,
  "optional_decoder_omission_approved": true,
  "authorization_basis": "<actual explicit user approval and its scope>"
}
```

The publisher does not create this record or infer approval from DO003. The
operator must supply the actual approval. The `review` must be the exact single
D10 frame amendment REVIEW. Integer `max_attempts: 1` preserves the existing
attempt scope; it does not reset consumption.

## Invocation after approval and qualification

Use the explicit CPU interpreter and provide every path:

```sh
/path/to/venv/bin/python -B \
  docs/research/vipe-alternatives/plan031-execution/video-post-recovery-controls-001/prepare_D10.py \
  --checkout /absolute/canonical/checkout \
  --run /absolute/owned/run \
  --review /absolute/D10-review.json \
  --qualification /absolute/actual-D9-runtime-qualification.json \
  --qualification-ledger-prefix /absolute/protected-finalization-prefix.jsonl \
  --user-approval /absolute/explicit-D10-user-approval.json \
  --output /absolute/fresh-D10-DO.json
```

The script requires imports from that exact checkout. It verifies the full
qualification record and a complete recovery002 result owned by the selected
run. Under the ledger shared read lock, the qualification prefix must equal
current ledger bytes. The existing `validate_frame_amendment` public gate then
checks unchanged science and caps, unstarted D10 ancestry, actual D9 receipt
bindings, accepted recovery lineage and its unique protected CPU finalization
charge. Approval and top-level evidence bindings are rechecked before atomic,
exclusive publication. Existing files and symlinks cannot be overwritten.

The output is `plan069-depth-user-authorization/v1`, status `DO`, with one D10
candidate approval, `max_attempts: 1`, the exact user approval file record and
`video_frame_amendment`. It retains the DO003 predecessor, cap amendment, cap
approval and video amendment, and sets `reset_previous_consumption: false`.
Publication writes no ledger event and performs no setup or inference. Actual
admission remains a separate protected operation.

## CPU validation

Ten isolated publisher tests pass; scoped mypy reports no issues. The tests use
the real frame gate and receipt/profile/science checks. Positive fixtures fake
only accepted recovery lineage; a negative fixture confirms that recovery002
schema alone cannot establish accepted ancestry. No fixture is production
evidence or human approval.

`publisher-timings-001.json` records both unique outer captures: **0.6781254680099664
seconds** total. There were no failed validation captures. Independent Standards
and Spec reviews reported no actionable findings (read-only reviews; no further
validation captures).

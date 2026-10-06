# D8 final-render authority (#34)

`authority.py` writes the licence records, QUALIFY/DO envelopes and approvals,
dispatches phases serially through `ActualDispatcher`, and aggregates the QUALIFY
arm. `wrap_qualification.py` turns an S1 CPU capture into the `validation.json`
that the requests bind (qualification-021 is current).

The approvals transcribe the user's 2026-10-05 instructions ("I approve gpu
work", plus the research-use licence choice). Claude writes them, as each
`recorded_by` field states. The user did not review each envelope separately.

## Independent review dispositions

There were two high-effort reviews: the first on the initial change, the second
after the fixes.

| Finding | Disposition |
|---|---|
| Production accepted hand-written or compatibility receipts | Fixed: `verify` re-derives the qualification from the ledger and requires exact agreement; the receipts have their own schema |
| Research-use decision not bound to the stack | Fixed: the decision binds the exact runtime inventory |
| Checkpoint timing scope | Fixed: covers save, metadata reload and hashing |
| Weak reserve gate (against the 3600 s allocation) | Fixed: checkpoint + cleanup must fit the 150 s train publication reserve |
| Aggregator outside the source closure | Fixed: in `required_sources()` |
| Duplicate arm parsing; post-verify loop; `Ledger.__new__` states hack | Fixed: shared `command_keys`, loop removed, ledger passed through |
| Unmeasured CPU coerced to 1 | Fixed: zero or missing usage refuses |
| No QUALIFY admission tests | Fixed: `command_keys` and reserve-gate tests added |
| 50 GiB per-request artifact limit vs 260 GiB cap | Fixed: 12 GiB limit (spec) |
| `native_adapter_qualified=True` on QUALIFY runs | Kept and documented: it means "ran under a reviewed envelope"; the reservation role marks qualification. Changing it would alter worker, geometry and supervisor validators and the matcher inventory |
| `cleanup_seconds` is not pure cleanup | Kept as a documented conservative upper bound (allocation time outside the worker budget) |
| Production per-call `verify` cost is not in the QUALIFY tail | Accepted: a hashing and ledger scan of a few records; monitored in production |
| QUALIFY admission does not check production feasibility | Checked numerically: 19,041 + ≤9,900 + 49,500 = 78,441 ≤ 93,600 GPU-s |
| `save_seconds` uses the wall clock rather than the injected clock | Accepted: actual workers require `time.monotonic`, so the clocks agree |
| Self-written human approvals | Recorded as transcriptions (`recorded_by`) of the user's explicit approval |

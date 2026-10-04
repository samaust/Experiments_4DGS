# D6 post-setup static source review008

Standards PASS and Spec PASS; no actionable findings. Both independent reviewers
verified frozen canonical commit `76b0b9a02fb6d9c9bfb0fc12ec8558006a0582a6`
and draft SHA256
`b43612ccda98cdfc69ae78e6b443eccbdbb695756729291bd6fdfcf1b83cf8ba`.

Verified 177 exact file records: 40 ordered local helpers, nine setup helpers,
123 accepted native source files, archive, profile, recipe, REVIEW and original
DO. The local closure includes the new driver qualifier, dispatcher and producer.
Supplied FoV, three refinements, FP32 inference and the original D6
`torch==2.6.0+cu124` recipe remain unchanged. Separate driver qualification
requires its exact DO, one bounded reservation and prohibited inference,
benchmark and kernel guards.

Ledger protections strengthen checked authorization transitions. Supervisor
changes reject stale or already started reservations and missing acceptance
results; actual peak reporting changes affect final-render supervision.
Prospective video PyPI selectors and budgets remain restricted to D9/D10 and
do not weaken D6's existing recipe or authority.

No model bytes, model imports, GPU operations or shared ledger writes were used.
This passed static review grants no execution authority. Canonical combined CPU
qualification, exact installed commercial evidence and actual native runtime
qualification remain required. Previous source records remain historical.

## Full CPU capture budget preflight

Use one hash-chain-validated event snapshot under a ledger lock:

```python
totals = ledger.totals(events)
available = (ledger.config['cpu_prepare_score_report_seconds_limit']
             - totals['cpu']['elapsed_seconds']
             - totals['cpu']['reserved_seconds'])
assert available >= 1200
assert not any(row['event'] == 'reserve' for row in ledger.states(events).values())
```

`events()` opens the existing ledger in `a+` mode but appends nothing. For a
strictly read-only inspection, open the existing ledger with `r` and `LOCK_SH`,
verify the sequence/previous hash/event hash with `files.object_hash`, then use
an instance created with `Ledger.__new__(Ledger)` and its existing config. Pass
that validated snapshot explicitly to `totals` and `states`; this avoids
constructor directory creation and the `a+` open. This preparation did not
inspect or mutate the shared ledger. Root must repeat preflight before capture.

`charge_cpu_preparation(elapsed_seconds, evidence)` checks the final measured,
deduplicated charge against the CPU cap. Its elapsed-only cap check does not
replace the reserved-seconds preflight. A 1,200-second timeout does not itself
guarantee sufficient remaining CPU allocation.

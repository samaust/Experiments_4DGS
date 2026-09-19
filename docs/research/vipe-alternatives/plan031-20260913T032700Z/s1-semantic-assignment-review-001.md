# Bounded S1 semantic-assignment repair — 2026-09-19

Implemented for review only. No GPU/model job, recovery authorization, ledger mutation,
setup, download, staging, commit, delegation, or report/aggregation rerun occurred.
The scope is one S1 assignment amendment plus CPU fixtures and this evidence bundle.

## Exact changed paths

- `scripts/vipe_benchmark/backends.py`
- `scripts/vipe_benchmark/contracts.py`
- `tests/test_vipe_benchmark_s1_semantics.py`
- `docs/research/vipe-alternatives/plan031-20260913T032700Z/s1-semantic-assignment-amendment-001.json`
- `docs/research/vipe-alternatives/plan031-20260913T032700Z/s1-semantic-assignment-validation-001.json`
- `docs/research/vipe-alternatives/plan031-20260913T032700Z/s1-semantic-assignment-review-001.md`

## Diagnosis and rationale

Both original jobs terminated at `normalize_phrase('')` in `detection_rows`, before
SAM/refinement/tracking. Calibration consumed 10.414188402937725 seconds;
reconstruction consumed 10.50047472200822 seconds. Both have confirmed cleanup.
The pinned standalone predictor retains queries with maximum sigmoid token score
strictly greater than 0.35, but builds native text with tokens strictly above 0.5.
Consequently a retained query can have an empty phrase. Combined or partial text
can also be unresolved. The failure traces establish empty text, but do not contain
its exact token scores; the score-range explanation is source-based, not a recovered
measurement of the failing query.

The hash-verified S0 `get_best_phrase_from_logits` ignores CLS/SEP IDs 101/102,
sums token probabilities inside period-delimited phrases (1012), and chooses the
first maximum. It does not use the nominal text threshold. The amendment implements
that rule independently in S1; workers do not import or read the S0 checkout.
It derives the class for every retained S1 query, including queries with valid native
text, to avoid a conditional fallback that differs from S0. S2 is unchanged.

Native prediction still controls box selection/order and max-token scores. The
observer computes the same CPU sigmoid as the pinned predictor and verifies exact
selected normalized boxes and scores against its return values before assigning.
It records full token probabilities, raw logits, raw boxes, selected query indices,
caption token IDs, phrase token spans/probabilities/sums, winner, margin, and tie rule.
`native_class` and `score` retain the native phrase (including empty strings) and
native confidence. `class_assignment.derived_class` supplies `class`. Ambiguity reasons
record unresolved native text, native/derived disagreement, exact ties, and a winner
without any token above the native text threshold. No near-tie threshold is invented;
the numeric margin remains available. Assignment evidence propagates with instance
IDs and is retained in detection metadata even for overwritten/skipped detections.
The shared contract accepts empty native text only with validated amendment evidence;
it checks finite phrase scores, sums, winner, class, margin, and ambiguity presence.

Boxes, weights, preprocessing, caption, box/text thresholds, SAM refinement/overlap,
DeAOT behavior, and precision remain unchanged. This changes the semantic protocol,
so the separate amendment is required; it is not an unchanged deterministic retry.
Frozen plan, study, protocol, report, status, old failures, and ledger are untouched.

## Validation

The source-bound validation JSON records the exact interpreter, command, stdout,
source hashes, historical-source/failure hashes, and preservation checks. All **68**
CPU tests pass across S1 semantics, backends, contracts, component recovery, and
execution. New fixtures cover empty/combined/disagreeing phrases, subword sums,
first-phrase ties, low text scores, zero detections, invalid score/layout evidence,
query alignment, native-box/score retention, pair propagation, and forged/missing
assignment rejection. Existing tests cover refinement, tiny masks, overlap, resets,
S2 behavior, and unchanged recovery allocation guards. The printed one-output S1
calibration message comes from the existing stubbed execution test, not a model job.
`git diff --check` passes. Initial fixture failures were corrected (fake tensor dtype,
then the previously hidden empty-native-text contract); the recorded final run passes.

## Remaining uncertainty and bounded recovery recommendation

No real repaired S1 output, CUDA behavior, quality gain, or S1/S0 output equivalence
is established. Actual token scores from the original failed queries are unavailable
in their failure traces. Equal assignment algorithms do not establish equal model
outputs or preprocessing. Runtime alignment/token-layout checks must pass within a
future allocated job; any mismatch stops that attempt. No smoke job is recommended.

The existing `component-recovery` command requires
`changes_to_prescribed_configuration=false`. That is not a truthful authorization
for this amendment. Before dispatch, separately approve and implement a narrowly
scoped amendment-aware admission/recovery binding (including tests), binding this
amendment and current source validation. Do not bypass that guard or use the current
false field to conceal this semantic change. This repair does not authorize that
follow-up admission work or any GPU attempt.

Recommended future scope: first one fresh `S1-calibration-recovery-001` attempt,
maximum 3,600 seconds including first-result qualification and cleanup. Only after
its review, separately authorize one `S1-reconstruction-recovery-001` attempt,
maximum 5,400 seconds. Recheck sequential IDs against the live ledger. Preserve
all previous consumption and the 93,600-second cumulative GPU ceiling, exclusive
one-process GPU rule, 22-GiB total-device cap, and storage/download limits. Bind
original failure event hashes from the amendment, exact E1 qualification/assets,
annotation/input provenance, amendment hash, full current source-bound validation,
and explicit user approval of the semantic change and each additional attempt.
Do not reopen geometry, finalists, aggregation, report, or combined arms. R-S remains
outside these two proposed allocations; its skipped state and immediate-repeat
requirement need an explicit separate disposition before reconstruction execution.

After that separate admission amendment and explicit authorization, the intended
controller command shape is (not executable authorization supplied by this review):

```sh
.local/envs/stg-colmap/bin/python scripts/basketball_vipe_benchmark.py \
  --run-id plan031-20260913T032700Z component-recovery \
  --authorization <future-explicit-amendment-bound-S1-calibration-authorization.json>
```

Use the reconstruction authorization path only for its separately approved attempt.
No authorization file was created and neither command was run.

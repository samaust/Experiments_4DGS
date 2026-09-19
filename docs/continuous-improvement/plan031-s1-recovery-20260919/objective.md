# Objective

Resolve the S1 segmentation semantic-validation blocker while continuing the
authorized implementation of `plans/plan_031.md`.

## Success criteria

- **S1-1** — The S1 semantic amendment is source-bound, preserves native boxes,
  phrases, scores, thresholds, weights, preprocessing, SAM refinement and
  tracking, and assigns every retained detection using the verified S0 token
  score rule. Evidence: amendment, source hashes, and focused CPU tests.
- **S1-2** — S1 recovery admission explicitly binds the amendment, current
  validation, original cleaned-up failure, E1 qualification/assets, one
  calibration attempt, and the existing GPU/resource ceilings. Evidence:
  admission implementation and ledger authorization record.
- **S1-3** — The bounded S1 calibration recovery completes or records a cleaned-up
  failure with first-result qualification and preserved raw evidence. Evidence:
  compact receipt and detailed run artifacts.
- **S1-4** — No frozen plan, prior failure, aggregate, report, or unrelated
  allocation is rewritten or rerun. Evidence: hashes, ledger, and git diff.

## Constraints

Use the existing repository instructions and plan budgets. Never read `prompts`.
Use one Astra subagent at a time, no nested delegation, and leave staging and
commits to the main agent. The calibration recovery is capped at one attempt
and 3,600 GPU seconds; reconstruction requires a separate later authorization
after calibration review.

## References

- `plans/plan_031.md`
- `docs/research/vipe-alternatives/plan031-20260913T032700Z/status.md`
- `docs/research/vipe-alternatives/plan031-20260913T032700Z/s1-semantic-assignment-review-001.md`

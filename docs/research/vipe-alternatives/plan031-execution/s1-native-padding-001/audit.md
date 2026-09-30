# S1 recovery005 native padding audit

Recovery005 is a failed calibration attempt with an auditable outcome. The first camera0/frame50 detector forward produced evidence; zero rows qualified out of the prescribed 510. The original evidence and failed status remain unchanged. No reconstruction or additional attempt is authorized by this correction.

## Exact rejection

`s1_evidence._qualify_row` rejected `invalid raw S1 logits/probabilities/boxes` because its unconditional finiteness check rejected native negative infinity padding. Both retained numerical archives contain logits of shape `(900, 256)`: exactly 225,000 negative infinities, covering columns 6 through 255 for all 900 queries. Columns 0 through 5 are finite. There are no NaNs or positive infinities. All padded probabilities are exactly zero; probabilities and boxes are finite and within their existing range checks. The sigmoid comparison has zero tolerance violations and maximum float32 discrepancy 5.960464477539063e-08.

The frozen caption has token IDs `[101, 2711, 1012, 3455, 1012, 102]`. The pinned GroundingDINO source revision is `856dde20aee659246248e20734ef9ba5214f5e44`. Its `groundingdino/models/GroundingDINO/utils.py`, `ContrastiveEmbed.forward` lines 262–266, explicitly masks unused tokens with negative infinity and pads the output to `max_text_len=256` with negative infinity. That source file's request-bound hash was independently verified as `2827ba921acaa263db7533afb6a818473a957fb2ef559c4f3407da72028a0842`.

## Representation correction

Preserve raw native logits without replacement or clipping. For the frozen six-token caption, accept native width 256 only when all six active columns are finite, every remaining logit is exactly negative infinity, and every remaining probability is exactly zero. Continue rejecting NaN, positive infinity, negative infinity in active columns, finite padded logits, nonzero padded scores, changed caption tokens, and other widths. The existing compact six-column CPU fixture representation remains accepted when all logits are finite. Probability range, sigmoid consistency, box finiteness and native query selection checks remain in force. Thresholds, precision, source/model assets, semantics, inputs and cardinality are unchanged.

This corrects the validator's representation of an explicit pinned native mask sentinel. It does not accept arbitrary nonfinite numerical results. CPU tests exercise the worker row qualification seam with independently constructed padding and adversarial mutations. It does not retroactively qualify the failed attempt or establish successful 510-row calibration.

## Outcome integrity and accounting

Ledger sequence 516 reserves 3,600 GPU seconds; sequence 519 records failure after 29.81751602998702 charged seconds. Terminal publication succeeded. Cleanup is confirmed, cleanup uncertainty is false, surviving PIDs and helper ownership are empty, and no secondary failure or required stop is recorded. The retained temporary directory is evidence retention, not proof of surviving ownership.

Verified file records:

| Evidence | SHA-256 | Bytes |
| --- | --- | ---: |
| Terminal receipt | `b9dfa5e89d9722f0f0efa4c667cf119667c723bcf4256d8c74c496205893b771` | 19782 |
| First-result qualification | `cf2ee328b5e16a9317633fea082ac9a8569bd3c3b2a9879f575d3746fc06a5a8` | 2827 |
| Failure evidence JSON | `85d0651deda5c2083ff269e7b88b6f602735318cce4d9e6f50df7d32400908b3` | 159506 |
| Failure evidence NPZ | `db16ef3e216406fa89a6f11854c29db070f7c886308cc461ac5d802dcbebe668` | 30233382 |
| Helper summary | `31817289ad917b886f373431f67fd64222ad47be13fe22f915f052df25059eb7` | 2492 |

The terminal receipt explicitly records missing successful result, missing partial runtime, and incomplete initial-runtime loaded-file evidence. Those are truthful failure limitations. Ticket #25's one-attempt outcome acceptance can be assessed separately from successful calibration. Any future GPU attempt needs a new concrete proposal, current qualification, review, live checks and explicit additional allocation approval.

The read-only chain audit verified all 520 ledger events through finish519, with head `0eb907e0a3e6509c6863309f289b35aff6d317d48553b1900f33d7f741f64a5f`.

## CPU validation

The native-padding acceptance test first failed at the existing raw numerical guard, then passed after the correction (`red.log`, `green.log`). Final relevant regression selection passed 11 tests in 5.589 seconds (`regression.log`): six new row qualification tests, existing failure preservation tests, and three numerical envelope tests. Unix socket fixture access required the prescribed single outside-sandbox retry; the retry passed. An earlier unsupervised selection also exposed process-group and missing validation-directory preconditions and is not claimed as passing source qualification. Root must qualify and review the final integrated source before any future reviewed dispatch.

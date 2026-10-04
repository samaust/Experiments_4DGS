# D9 reconciliation CPU total correction

The read-only admission producer now accumulates global CPU elapsed time in ledger event order with += starting at0.0, matching Ledger.totals exactly. Compensated builtin sum can produce a different final float on another interpreter; the strict consumer comparison remains unchanged. Candidate attribution, historical owner785 handling and all caps are unchanged.

The public producer regression recreates the accurate-sum mismatch with immutable temporary fixture metadata and checks CPU finish/checkpoint/preparation charges while excluding GPU elapsed. The test failed before the correction and all five focused cases pass afterward; producer mypy and both independent review axes pass. No common runtime helper changed.

Three unique captured validation scopes, including the initial failing regression, are recorded. No model, GPU, network or production ledger write occurred. The changed physical producer record needs scoped source/test qualification before actual reconciliation admission.

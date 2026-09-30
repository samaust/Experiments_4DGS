# Reproducible S1 REVIEW fixtures

The proposal tests previously read the live ledger and therefore failed once the approved recovery005 was consumed. Positive proposal, approval and registration tests now use the retained 514-event pre-dispatch ledger from `e5-recovery-001/outcome/ledger-after.jsonl`. A separate negative test uses the retained actual post005 ledger from `s1-recovery-005/outcome/ledger-after.jsonl` and confirms that consumed005 is rejected.

Historical path spellings remain intact because production preservation checks bind them. Narrow test filesystem reads serve only the historical live ledger pathname and the historical AGENTS pathname. All other file reads and numerical/identity/preservation validators are unchanged. Registration uses the existing disposable append sink. Cleanup checks that the real live ledger bytes remain unchanged.

The historical process-file amendment remains immutable. `historical-agents.md` retains the exact AGENTS bytes from commit4301c559: 4873 bytes, SHA-256 `21c986e57de9b8c4f6d0eb9cf15596b3f005c79706285da23be947944d930ab8`. Tests verify that record against the existing amendment and serve those bytes consistently for hashing, anchored reads and size checks. The later interpreter instruction changes current process documentation; it does not rewrite historical authority or qualify a consumed identity.

All seven `S1ReviewProposalTests` passed in 5.829 seconds (`focused.log`). This is a fixture-only correction; no production validator, dispatch identity or scientific setting changed. No GPU, setup or model attempt was run.

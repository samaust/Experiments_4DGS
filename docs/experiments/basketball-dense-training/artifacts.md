# Plan 027 artifact index

- [Both frozen initializer summaries](preparation-002.json)
- [Native resource qualification](resources-qualified.json)
- [Full-data coarse fusion determinism](fusion-determinism-coarse.json)
- [Full-data cropped fusion determinism](fusion-determinism-cropped.json)
- [Fixed initialization diagnostics](initial-diagnostics.json)
- [Thirty verified historical curve results](baseline-reuse.json)
- [Implementation and runtime validation](implementation-validation.md)
- [Final report](analysis-final/artifact-index.json)
- [Final trajectory audit](audit-final/trajectories.json)
- [Final held-out visuals](visual-validation-050000.json)
- [Final storage measurement](storage-final.json)
- [Current execution state](status.md)

Large artifacts reside under `.local/basketball-dense-training/`:
`initializers/`, `diagnostics/`, `validation/`, full `cloud-*-001/`, and shared
`masks-full-001/`. Each frozen initializer contains `initialization.npz`,
`observation-mapping.npz`, `sources.json`, and `result.json`; the latter binds
all contributing cloud archives and sidecars by SHA-256. Source cloud archives
retain view-local instance labels, regions, camera support, and velocity validity;
their records retain rejection counts and cropped-association rejection reasons.

`ledger.jsonl` records GPU job lifetimes and charges; `historical-links.json`
binds the prior ledger and final curve index. `segments/` retains command logs,
process metadata, and outcomes. `run-state.json` is the live handoff state.
All six dense trajectories reached 50,000 updates with complete render/reload
evidence. The final analysis contains 60 complete metric records; the audit,
visual validation, trained diagnostics, and storage measurement are linked above.

[Initialization panel validation](initial-panel-validation.json) retains the
index for all twelve ground-truth/coarse/cropped training-view comparisons.
[Post-cleanup reuse audit](post-cleanup-reuse-validation.json) confirms all
30 historical curve artifacts and 10,500 historical PNGs remain intact.

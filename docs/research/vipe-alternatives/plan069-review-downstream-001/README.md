# Issues #60, #61, #34 and #35: integration handoff

## Destination

Source branch: `plan069-review-downstream`. Integration destination:
`plan069-depth-extension` in
`/home/auss/git_repos/samaust/Experiments_4DGS/.local/plan069-worktrees/depth-extension`.
The destination owner integrates these changes; `main` is the final destination.
Neither destination was modified by this lane. No push was performed.

Merge the source branch after the owner's execution and qualification are quiet.
It includes destination commit `21a3c293`. Resolve any subsequent destination
changes before running fresh qualification against the integrated sources.

For selective integration onto a branch containing `21a3c293`, first apply
`3811e0dd` with merge parent 2 (`git cherry-pick -m 2 3811e0dd`). This preserves
the stricter aggregate validation prerequisite. Then apply these commits in order:

| Commit | Change |
| --- | --- |
| e2b0ed79 | Checked native initializer payload adapter (#34) |
| b1821272 | Extended visual review and separate metric choice (#60) |
| f10199ea | Selected metric depth at REVIEW admission (#61) |
| fe5408f7 | Real extended-contract adapter integration test (#34) |
| 20fed492 | Exact approved 110/210 budget compatibility (#61) |
| ae1d7ba2 | Actual human import and decision CLI (#60) |
| dea46eb6 | Bound qualitative assessment reporting (#35) |
| 9a7833f8 | Completed native source proof survives later UI edits (#60) |
| cb88e5d5 | Actual child hierarchy, separate historical references (#35) |
| 2f6d4a68 | Shared metric eligibility vocabulary |

The subsequent evidence commit includes this handoff and validation captures;
use the source branch's current HEAD to include it.

## Delivered and remaining work

- **#60:** software review/import/decision contract implemented. Visual preference
  and metric D* are distinct. Relative-only candidates cannot become metric D*.
  Actual extended human feedback is still required by #62/#45.
- **#61:** REVIEW admission implemented with fixed S2, one eligible D* across all
  five arms, exact accepted scale/input lineage and current qualification checks.
  REVIEW grants no execution authority.
- **#34:** checked native input adapter and extended-contract integration test
  delivered. Actual D* assembly, native training/reload/render qualification,
  approved execution and matched final renders remain incomplete.
- **#35:** assessment API/CLI delivered with immutable historical human evidence,
  accounting and recursive issue reconciliation. Actual extended depth and final
  motion/neighbor feedback, completed execution and verification remain missing.

All four issues remain open pending integration and their remaining gates.
No incomplete issue or parent was closed. The actual issue snapshot records #3
already closed with no native children; historical #4–17 remain separate references.

## Validation

- 53 focused tests passed in 10.261 seconds, zero failures/errors/skips.
- Python compilation and CLI/viewer smoke checks passed. No configured or
  installed static type checker was available; no typing pass is claimed.
- Independent standards and spec reviews found zero blocking findings. Their
  source inventories and reviewed base/head are preserved in the review JSONs.
- Corrected full suite: 1,353 tests, zero failures, **six errors**, 22 skips,
  808.606 seconds elapsed, no timeout at the 900-second capture limit.
  **This is not a passing full-suite or qualification receipt.** Four errors concern
  unavailable pytest/matplotlib; one is an existing historical deadline test;
  one rejects a copied historical receipt's original-checkout authority path.
  See `validation-limitations.json` and `full-suite-002/`.
- `full-suite-001/` preserves the unsuccessful capture caused by the original
  launcher/worktree fixture setup. The corrected launcher used a dedicated process
  session, explicit virtual environment and private historical fixture snapshots.
  Successful evidence writes were preserved before retrying.

The corrected full-suite capture and first capture record measured elapsed times.
Ancillary preparation and subagent work were not measured cumulatively; these
records do not establish complete cumulative execution accounting for this lane.

## Evidence and execution boundaries

The assessments are actual **partial, blocked reports**, not invented human
judgments or completion receipts. They preserve samaust's S2/D4 reviews and the
confirmed D2 observation at `camera1-selection-175`. Assessment 002 adds a verified
619-event historical ledger snapshot and explicitly stale resource observation.
The missing aggregate input in these reports does not imply D7 was never generated.

Protocol, scientific configuration and previous human decisions were checked
unchanged. Completed D7 archive/qualification/admission/ledger proof was checked
read-only. Later UI edits may not rewrite completed evidence; new dispatch still
requires current integrated source qualification.

This lane used CPU tests only: no GPU/model setup/download/native experiment or
shared ledger mutation. Fresh resource checks, qualification and admission are
required after integration. GPU execution must use the shared ledger and remain
serial with the other owner. Motion and neighbor effects require final renders.

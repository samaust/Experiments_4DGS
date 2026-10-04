# Prospective PyPI video runtime preparation

**REVIEW only.** This CPU preparation selects the distinct official PyPI Torch
2.14.1 / Torchvision 0.29.1 distribution and all 49 prospectively verified
package pins. It grants no distribution choice, budget change, setup or GPU run.
Existing v1/v2 recipes, reviews and authorizations are preserved.

The v3 recipe uses only `https://pypi.org/simple`. The v3 profiles restore exactly
to the original scientific profiles when the runtime exception is removed. The
preparation review binds this checkout and proposes dependency 6 GiB / artifact
9 GiB per candidate, as justified by `video-pypi-budget-proposal-001`. Root must
create a fresh immutable canonical review after integration and source review.

## Future explicit authorization contract

The root owner may issue a new DO only after explicit distribution and budget
approval plus fresh global allocation reconciliation. Its normal review,
previous_authorization and grants remain required. It must also bind an exact
`video_amendment` object:

- schema: `plan069-video-distribution-budget-approval/v1`
- status: `approved`
- distribution_approved: `true`
- budget_approved: `true`
- recipe: fresh canonical v3 recipe file record
- budget_review: canonical `video-pypi-budget-proposal-001/proposal.json` record

Both D9/D10 proposals must use v3 together and match the reviewed allocations
exactly. Restoring the previous budgets and profiles must recover the immutable
DO001 review exactly. Attempt limits, previous consumption, global cap lineage,
workload, models, weights, source revisions, precision and all other settings
remain unchanged. No DO is included in this preparation.

## Actual observations remain required

Distribution metadata must report exact unsuffixed `torch==2.14.1` and
`torchvision==0.29.1`; all 49 installed versions are checked. Imported modules
may independently report the exact base release or its `+cu130` local suffix.
The observed `torch.version.cuda` must equal `13.0`. Package metadata alone
cannot assert either CUDA compatibility or runtime success.

Dependency capture records actual imported module observations and their recipe
binding. Admission and completed D10 eligibility reject missing or mismatched
observations. Native loading rechecks module versions before constructing a
model. CPU fixtures mock imports explicitly; they establish validation behavior
and grant no actual compatibility receipt. Full native runtime qualification,
commercial dependency review, final renders and human feedback remain pending.

## Validation

Final CPU validation passed 42 video cases and 14 depth-review cases. Scoped
mypy passed all six changed modules. Independent Standards and Spec reviews
have no remaining actionable findings. Initial captures are preserved alongside
final validation-002 records; no GPU, installs, network or shared ledger were used.
The CUDA toolkit pin records the actual wheel version `13.0.3.0`, equivalent
to the prospective resolver requirement `13.0.3` under PEP440.

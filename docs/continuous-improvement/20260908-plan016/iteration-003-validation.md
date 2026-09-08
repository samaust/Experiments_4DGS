# Iteration 003 validation — Plan 019

All four Plan 019 acceptance items pass within this bounded reference experiment.
The [package checks](../../experiments/basketball-shared-timing-v12/package-validation.json)
and [comparison classifications](../../experiments/basketball-shared-timing-v12/comparisons.json)
support the result; archived gradient failures are measured findings, not
reference disagreement.

| Acceptance | Outcome and evidence |
| --- | --- |
| A1 | Met: six pinned physical identities, original source maps, v10 chain integrity and v11 plain-event ownership validated; three 300-observation support certificates strictly exclude rows 0/1; all archived depth minima finite and above unchanged threshold. |
| A2 | Met: 2 owned setups/returns, 12 unique entries/completions; exact equality of 6 paired costs, 36 paired gradients and 5,400 paired signed summands; 72 reference gradients and 12 costs persisted. |
| A3 | Met: all 72 archived gradient and 12 saved acceleration-cost comparisons classified by exact rational forward error against original binary64 allowed error. Original v11 failure report retained unchanged. Primary fails 25 components; independent fails 17. |
| A4 | Met subject to recorded local commit checkpoint below: both fixed 12-case toy suites passed; JSON package/source/budget checks passed; report states limitations and a concrete next action. Link/diff and final integrity checks recorded below. |

The [toy fixture freeze](../../experiments/basketball-shared-timing-v12/toy-freeze.json)
contains exactly 12 fixed cases, unchanged across both invocations. The
[first log](../../experiments/basketball-shared-timing-v12/toy-suite-01.log) and
[second log](../../experiments/basketball-shared-timing-v12/toy-suite-02.log) passed.
No scientific fixtures entered the tests, and no third invocation occurred.
Toy child interruption/timeout retained consumed entries and partial output and
reaped owned nonscientific sessions. Final additional package ownership assertions
were statically inspected and syntax-checked after suite 2, and passed the actual
JSON-only package invocation; no arithmetic/supervisor/ledger/test change followed
suite 2. All final sources were frozen before the first scientific setup.

[Budget](../../experiments/basketball-shared-timing-v12/budget.json) records
1.0269929650239646 supervised numerical seconds, ending at monotonic
270770.221502938 with worker exit 0 and `worker_stopped=true`. Two setups and all
12 bundles are consumed. No unused time transfers to new entries. Library thread
counts were all 1, with one numerical worker plus supervisor. Worker PID/PGID/SID
4 belongs to recorded namespace `pid:[4026533042]`, as does supervisor PID 3;
these are namespace identities, not host kill targets. The owning supervisor
reaped the worker and the tool process session completed. No jobs remain running.

Read-only provenance checks, JSON exact comparison checks and documentation
validation did not call scientific evaluators. An initial admission serialization
failure was a checker defect, not a sandbox restriction, and was corrected before
namespace creation or scientific entry. No sandbox/permission failure occurred.
No git failure occurred before the recorded commit checkpoint.

SC-01/SC-03 remain unmet. SC-02/SC-04 evidence is preserved. SC-05 evidence
integrity advances without retrospective changes to v11 failed checks, Plan 015
gates or any historical resource allocation. No GPU, training, rendering,
network/install, residual/depth evaluator, optimizer, float replay, new ray,
analytical limit, finite difference or Hessian work occurred.

## Local commit and final validation checkpoint

Implementation/evidence milestone committed as `105c88886700751ade37d6afda2bdfa60eb3a09c`. Separate escalated
staging and commit commands succeeded after staged-diff inspection; no push,
amend, history rewrite, permission denial or git failure occurred.

Final retained-data checks verified 10,956 normalized rational values and 39
Markdown links; frozen source hashes and admission-source identity match.
`git diff --check` and staged `git diff --cached --check` passed.
See [final integrity](../../experiments/basketball-shared-timing-v12/final-integrity.json).
All Plan 019 acceptance items A1–A4 are met; main objective remains unmet.

Phase checkpoint at monotonic 271103.561509619: 1093.716750093 elapsed
seconds of 1800, including implementation milestone commit. Numerical charge
remains 1.0269929650239646 seconds; 2 setups, 12 bundles and 2 toy suites consumed.
Only this handoff documentation commit and final repository check follow; the
parent handoff receives their final commit ID and total phase time. No running
worker or command session remains; no scientific work follows the consumed pass.

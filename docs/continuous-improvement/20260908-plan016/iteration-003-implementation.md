# Iteration 003 implementation — Plan 019

Implemented [Plan 019](../../../plans/plan_019.md) within the saved
[authorization](iteration-003-plan019-authorization.json). The two independent
exact references agree on all six costs, all 36 paired partials and every signed
summand. [Report](../../experiments/basketball-shared-timing-v12.md) and
[decision](../../experiments/basketball-shared-timing-v12/decision.json) preserve
the distinction between reference success and archived floating failures:
primary 25/36 gradient values outside tolerance; independent 17/36 outside.
Both methods' saved acceleration costs pass 6/6. All 72 gradient comparisons and
12 acceleration-cost comparisons are classified, none unverified.

The new [primary script](../../../scripts/basketball_acceleration_reference_v12.py)
implements immutable admission, rational basis derivatives, supervisor/ledger,
and JSON-only packaging. The [control script](../../../scripts/basketball_acceleration_control_v12.py)
independently computes differentiated control coefficients and transpose
propagation. Each decodes the same pinned binary64 operands independently.
[Inputs](../../experiments/basketball-shared-timing-v12/inputs.json) retain all
original coefficients, archived full results, slot ownership and provenance.
Support certificates cover all 300 observations in each of three cases and
establish exact zero data/depth partials for rows 0 and 1.

All 2 setup slots and 12 state-bundle slots completed once in 1.0269929650239646
numerical seconds, including startup/imports/setup/I/O, against the 120-second
ceiling. Both allowed fixed 12-case toy suite invocations passed and are consumed.
Admission finished at monotonic 270236.06420132; readiness at approximately
270752.004908516; numerical work ended at 270770.221502938, with no clock reset.
Final phase accounting and local commit checkpoint are appended below.
[Budget](../../experiments/basketball-shared-timing-v12/budget.json) retains the
absolute numerical deadline, actual process namespace, counts and stopped worker.
No jobs remain; forbidden scientific/training/network/install entries are zero.

The first JSON-only admission attempt failed because the new chain checker
included a trailing newline in its canonical serialization. It created no output
namespace and entered no science. Correcting the checker to match the immutable
historical encoding admitted the original bytes; no historical source changed.
The exact admission-stage source is retained and hash verified. The
[command record](../../experiments/basketball-shared-timing-v12/commands.json)
retains that failure and both consumed toy runs. After suite 2, only JSON package
ownership assertions were strengthened; they were inspected/syntax checked and
then exercised by successful packaging. There was no third toy or numerical run.

SC-05 is advanced by the exact reference and retained evidence. SC-01 and SC-03
remain unmet because Basketball timing/preparation and reconstruction comparison
remain absent. Existing supported SelfCap SC-02/SC-04 evidence is preserved.
Accepted timing, production candidate and final-validation protocol remain null;
full-screen readiness remains false. Other 57 failed v11 states are outside
scope, and historical v11 A2/A3 remain failed. Plan 015 gates and historical
Plan 016/018 and 24-hour training allocations remain unchanged.

Next recommendation: one bounded arithmetic correction/qualification plan
against these saved exact outputs, tied back to timing evaluator gates. The
report proposes at most 10 minutes each for sequential Review/Plan with zero
scientific entries, then a separately finalized 30-minute/120-second candidate
phase with six candidate bundles and no new reference evaluations or ray ladder.
Nothing from that next proposal was executed here. Main objective is not attained.

See [validation handoff](iteration-003-validation.md) for acceptance and checks.

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

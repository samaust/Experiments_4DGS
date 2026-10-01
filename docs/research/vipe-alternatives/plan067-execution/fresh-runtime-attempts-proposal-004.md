# Fresh S1 calibration attempt — scope REVIEW only

## Correction and qualification required

Recovery009 reached final acceptance after all510 calibration rows individually
qualified. The retained helper's strict referenced-record read raised OSError
ELOOP at the model-cache `model.safetensors` alias and poisoned the helper. Terminal
evidence publication then failed because that helper was unavailable. This was
neither a timeout nor a Codex permission denial.

The model-cache alias correction received independent Standards and Spec
review with zero remaining blocking findings. It binds the admitted alias and its verified regular target without
weakening ordinary strict referenced-record checks, source/model/input contracts,
ownership, cleanup or deadlines. Complete current-source qualification014 passed
328 tests/1035 subtests in429.160 seconds, zero failures/errors/skips, under600
seconds. Its validation SHA256 is
b5a9f028562f948ca17f05ac2a8cb38cfbdbf39633af75b1e254535500d3dd54.
The source inventory remained unchanged. Full integration ran1171 tests with
zero failures, six known unrelated errors/five skips and no timeout; this is not
a passing full-suite claim. See alias-final-render-fullsuite-001/ and
s1-alias-and-final-render-cpu-review-001.md. Earlier approvals cannot authorize
fresh010 automatically; new controls require their own current qualification.

## Requested allocation

Exactly one **S1-calibration-recovery-010** attempt, maximum **3600 seconds**, to
generate and accept all510 calibration rows:340 fit and170 selection. Root alone
owns the single GPU. No reconstruction, runtime setup, download allocation or
automatic further attempt is included. Approval is pending; this proposal is
REVIEW only and supplies no execution authority.

Preserve source/model/input/precision/threshold contracts, two-second resource
sample deadline,256KiB row metadata limit,22GiB device cap, eight CPU workers,
60GiB downloads,150GiB artifacts and original cumulative ceilings:
93600 GPU seconds,57600 setup seconds and57600 CPU seconds. Final rendering and
training require separate concrete proposals if not already allocated.

## Preserved state and remaining gates

[Recovery009's preserved outcome](../plan031-execution/s1-recovery-009/outcome/OUTCOME.md)
records failure after2209.498 seconds (exact elapsed2209.4980646440526), with510
individually qualified rows and zero accepted complete calibration results.
Finish578 SHA256
db47dacfcb3e35f0e35f677af39390677404e5c361ec50a24d7ad72146470fd4
and the exact579-event ledger prefix remain preserved. Cleanup was confirmed and
there were no surviving pids, but `stop_required=true`, the terminal receipt is
absent, and terminal publication remains `unavailable` with reason
`poisoned_helper`. The raw result stays unaccepted; none of its rows or partial
receipts is promoted into an accepted calibration result. Retain earlier failed
attempts and their original stop/terminal histories as well. The one-attempt009
approval is consumed.

The latest reported579-event budget snapshot has45 GPU attempts consuming
8939.865233584946 seconds, four CPU attempts consuming13820.217350039009 seconds,
and21 setup attempts consuming6055.783853152872 seconds. All three resources have
zero reserved seconds. Adding the requested3600-second GPU maximum gives
12539.865233584946 seconds, within the original93600-second ceiling. These are
reported snapshots, not live admission checks.

The reported resource snapshot has37864969113 download bytes,
104290996224 allocated artifact bytes,180801137605 logical artifact bytes and
1114636288 device bytes, with no GPU pids. The artifact budget uses allocated
bytes; logical bytes remain reported separately. Downloads and allocated artifacts
fit their original60GiB/150GiB ceilings at this snapshot. Recheck current usage,
free storage and cleanup reserves before admission; no new storage or download
authority is created here.

Recovery010 identity-specific controls, approval and immutable REVIEW/DO bindings
are not prepared by this proposal. After explicit approval, the controls must bind
the consumed009 finish and preserved outcome, exact prior histories and fresh010
identity. Independently review the controls and capture a new passing
qualification for their complete current source, binding the explicit approval
and exact ledger prefix. Qualification014 covers the CPU correction only;
later control changes require their own fresh qualification.
Preserve009's failed stop/absent-terminal/poisoned-helper state in those bindings;
do not clear, rewrite or reinterpret that history as success.

Immediately before any separately authorized dispatch, recheck current source and
qualification, helper ownership and cleanup, absence of survivors and conflicting
active allocations, admitted model-cache alias/target and all source/model/input
assets, device/download/storage caps, cumulative budgets and finite deadlines.
An unresolved or failed gate stops dispatch. No010 identity has been registered,
reserved or dispatched by this proposal.

# Guard007 validation

Base: `a2afb5d7`; overall user-approved review baseline: `b1b43c58`.
The initial CPU proposal milestone below changed no canonical source, actual RUN
output, model, GPU or protected ledger. The later CUDA check is recorded separately.

The RED fixture failed because listen was still denied and the new startup proof
was absent (12 tests, two expected failures, fixture time0.004s). After the scoped
change, historical006 passed12 fake tests and007 passed13. Scoped mypy passed for
007/network_guard.py and007/startup.py. These fixtures never install filters or
create sockets. Nine physical ancestry/setup records were verified, including
failed clean finish842. No passing004 request or DO was materialized.

Measured test/typecheck wall:0.523147669s; ancestry check:0.005620349s; total
0.528768018s. The initial RED parent command was not separately metered; its
reported fixture time is0.004s. Private captures are under the isolated checkout's
`.local/guard007-validation-001/`. Root owns resource settlement.

Independent Spec/security and Standards audits both PASS with no actionable
findings. Reviewers inspected physical records read-only. PASS is limited to the
proposal milestone. Execution readiness remains NOT READY until the documented
v4 public contracts, source review, CPU qualification and new explicit approval.

## Versioned004 public seams

The isolated implementation now provides v4 worker/request/result/dispatcher and
protected ledger/admission support. An initial request fixture exposed the absent
v4 authority, then8 public-boundary tests passed (tool wall2.069146701s). A new
negative fixture initially attempted to overwrite immutable fixture JSON with the
production writer; corrected only the disposable fixture (failed test command
wall2.622560798s). Final47 focused v4 and historicalv3 boundary/dispatcher tests
pass in3.902046702s. Scoped mypy passed five owned sources in0.471624867s.
Measured command wall for these four runs totals9.065379068s; the initial missing
module RED parent was not separately metered. No live resource charge was written.

Independent Standards and Spec/security implementation reviews of commits
4405930b and dc864432 found no actionable findings. The fixed baseline remains
b1b43c58; a2afb5d7 identifies the incremental correction.

## Actual CUDA initialization regression

The user's terminal comparison established that this D6 interpreter initializes
CUDA without guard006 and fails with guard006. The retained003 trace identifies
the denied local `listen`. With only that denial removed in guard007, a fresh
outside-sandbox diagnostic passed `torch.cuda.init()` using PyTorch 2.6.0+cu124.
The new trace records successful abstract Unix bind/listen and the unchanged
EPERM for the MPS connection. Guard startup proved one thread, zero inherited
socket descriptors and no numerical imports before installation.

Parent wall:1.773786115s; child wall:1.514073522s; sampled total GPU memory
peak:910163968 bytes. No weights or inference were used. Cleanup confirmed no
owned process or MPS client; the pre-existing idle MPS service was not changed.
Exact probe, results, trace and cleanup hashes are preserved in
[the outcome](../depth-D6-guard007-cuda-outcome-001.json).

This demonstrates the initialization fix. No actual004 request, DO, full model
qualification result or integrated source receipt is claimed.

## Integration

Fast-forwarded `plan069-depth-extension` through `e64c3f4f` after confirming
zero active ledger reservations. Canonical worker, guard, startup, dispatcher
and authority bytes match the reviewed proposal. Existing untracked D9/D10
outcomes were preserved.

On the integrated branch, 96 CPU tests covering the D6 qualification versions,
dispatchers, admission and protected ledger transitions passed, plus 13 guard
fixtures. Captures: `.local/D6-guard007-integration-tests-001/`. Command wall:
7.494010378 seconds. This focused regression check is not the full production
CPU qualification required for a new attempt.

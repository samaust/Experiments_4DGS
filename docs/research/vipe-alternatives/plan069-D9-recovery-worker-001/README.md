# D9 offline recovery worker preparation

CPU fixtures only; no actual recovery approval, command, install, network, model,
GPU or shared-ledger operation is supplied or performed here.

Baseline `7da96364`, branch `plan069-D9-recovery-worker`, separate worktree
`.local/plan069-worktrees/D9-recovery-worker`.

`run_video_setup_recovery` accepts only the fixed new job
`plan069-D9-setup-recovery-001` and schema
`plan069-video-setup-recovery-request/v1`. Actual execution requires the owner's
`depth_setup_recovery.validate_recovery_request(request_record, events, run_root,
require_reservation=True)` authority API. It supplies original immutable asset
lineage, v4 environment request, effective config/current resource reading,
original combined byte limits and separately approved recovery allocation.
The actual worker rejects injected fixture command runners. Fixture requests can
exercise computation through a fake runner; their results remain fixtures.

Original source/archive/checkpoint records are reused unchanged. The checkpoint
is hardlinked into the recovery job's owned directory for the native loader.
The old failed job tree is checked before/after by metadata identity/size/mtime;
all reused immutable asset records are reverified. Original environments, receipts
and failures are never rewritten or removed.

A new environment is created only at `runtime/environment` under the new job.
The recipe must bind exactly 48 constraints and the frame-input profile; Decord
and xformers must be absent. Six fixed commands probe the retained Python seed,
create the offline venv, compile a hash lock from cached PyPI metadata, install
that lock offline, perform strict dependency checking and capture the installed
file inventory without importing models. The actual process installs the existing
seccomp network guard before commands; UV and model offline flags and hidden GPU
visibility are explicit. No proxy, source acquisition, dependency metadata rewrite,
skipped dependency check or automatic retry is provided.

Budget checks use unchanged original combined setup byte ceilings and require no
new downloads. The separate setup reservation's wall limit includes worker output
and publication; 30 seconds remain for external supervisor cleanup. The result
schema is `plan069-video-setup-recovery-result/v1`. A complete fixture or worker
result alone grants neither native qualification nor production DO admission.

The owner must integrate the separately reviewed v4 recipe/proposal, checked new
recovery authority and protected ledger transition, and then qualify combined
sources. New explicit human approval is still required before any actual recovery.
Downstream accepted-setup normalization must preserve both the original failed
job and separately approved clean recovery lineage. Existing original max-attempt
limits are unchanged.

## CPU validation

Five public recovery-boundary fixture cases pass, covering exact reused assets,
original failure preservation, a fresh immutable offline environment, actual
fixture-runner rejection, strict dependency-check failure and excluded-package
rejection. Final focused process capture: 0.113807 seconds (unittest interval
0.056 seconds). Three changed Python files passed syntax parsing. Mypy, using the
owner's existing private tool overlay, passed both production files after one
missing-list-annotation correction; successful full command elapsed 0.164235
seconds. No tool installation was performed.

Every test, syntax and typecheck command, including the initial red and failed
mypy runs, has an immutable measured full-command receipt and retained stdout in
`.local/D9-recovery-worker-cpu-001` in this worktree. These captures are not yet
charged; the owner must settle them once through the shared ledger and run its
combined full-suite qualification after all recovery sources are integrated.

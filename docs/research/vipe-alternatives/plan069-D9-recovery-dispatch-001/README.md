# D9 recovery REVIEW and dispatch producer

`prepare_recovery.py` prepares fresh private REVIEW evidence from protected grant
761, failed clean finish 765 and the retained original request, byte checkpoint,
source archive, inference source records, model acquisition identity, runtime
failure and lock. It reads the approved model digest and verifies its retained
acquisition inode metadata, avoiding a new model payload read during REVIEW.
Actual authority and result acceptance still verify the exact model bytes.

The draft keeps original combined download/artifact/model/CPU allowances and
scientific settings; only the reviewed v4 frame-input runtime changes. The
separate recovery proposes one attempt and 1,200 seconds. It creates no DO,
source review or execution qualification.

Use the canonical tracked producer after integrating its commit:

```bash
/home/auss/git_repos/samaust/Experiments_4DGS/.local/envs/stg-colmap/bin/python -B \
  /home/auss/git_repos/samaust/Experiments_4DGS/.local/plan069-worktrees/depth-extension/docs/research/vipe-alternatives/plan069-D9-recovery-dispatch-001/prepare_recovery.py \
  --checkout /home/auss/git_repos/samaust/Experiments_4DGS/.local/plan069-worktrees/depth-extension \
  --run-root /home/auss/git_repos/samaust/Experiments_4DGS/.local/vipe-alternatives/plan031-20260913T032700Z \
  --mode review --output <fresh-private-directory>
```

Dispatch remains unapproved. Its explicit flags additionally require `--review`,
`--authorization`, `--source-review` and `--qualification`. Root must publish the
independently reviewed draft at
`docs/specs/plan031-execution/depth-D9-frame-recovery-review-001.json`, obtain a
matching DO, then bind the canonical producer and complete executable/config
closure in fresh source review and capture012. Pure approval/evidence commits
may change HEAD if every qualified executable/config byte and path still match.
No fixture or old capture substitutes for that proof.

The worker command is exactly the dispatcher's `sys.executable`, canonical
`scripts/basketball_vipe_video_setup_recovery.py`, `--request` followed by
`RUN/requests/plan069-D9-setup-recovery-001.json`, and `--output` followed by
`RUN/jobs/plan069-D9-setup-recovery-001`. Checked authorization binds that command,
worker and interpreter; reservation evidence includes all six exact bindings.
The existing supervisor enforces 1,200 seconds and original absolute byte caps,
checks the public prefinish callback under the real active reservation, confirms
cleanup and records the finish. Postfinish `accepted_setup_lineage` remains a
separate requirement. An identical unconsumed request may resume without
rewriting it; changed requests or checked grants/reservations/attempts are rejected.

Seven CPU producer tests and mypy pass. Independent Standards and Spec reviews
have no remaining findings after corrections for executable reservation evidence,
identical unconsumed request reuse and canonical approval row shape. Actual
private REVIEW generation succeeded with no live writes or model payload read.
Ten worker/acceptance tests passed in the preceding milestone. Immutable capture
inventories remain private in the worker worktree under
`.local/D9-recovery-worker-cpu-001/`. Preparation timing is separate from any
future supervised setup finish: do not charge a dispatcher's whole wall time as
CPU in addition to setup time. Admission/preflight/postfinish validation outside
supervision need separate parent-monotonic CPU captures when execution is approved.

# D6 execution preparation

CPU preparation for issue #56. No setup, model loading, inference, GPU use,
network access, installation, shared ledger writes or execution authorization
was performed. D6 is MoGe-3 ViT-L. Root remains the sole execution owner.

## Retained methods

- Capture uses unchanged `moge-cpu-method-002/producer.py`: two strict CPU
  model loads, D6 refiner validation, no forward/inference/CUDA, and installed
  dependency evidence.
- Finalization uses unchanged `moge-cpu-method-003/producer.py`: full top-level
  and runtime source archive/files, independently assessed commercial evidence,
  accepted setup and current native helper bindings.
- The D6 wrappers retain D5's seccomp network denial, observed descendant
  cleanup, seven CPU workers, immutable input checks and full disk scopes.
  They require root-supplied exact D6 setup SHA and reviewed source commit;
  the resolved executable is bound separately from explicit venv invocation.
- The dispatch driver retains D5's 160-second CPU preparation alarm around the
  stock dispatcher. Only successful D6 GPU reservation pauses the CPU alarm.
  GPU finish elapsed time is subtracted once; the driver charges remaining CPU
  time once. This does not change the GPU deadline or allow another attempt.

## Prerequisites

Finish D5 publication/previews before D6 downloads: the candidate publication
checks observe whole-run disk growth. Check partial state and existing D6 setup
request, reservations and output before starting; do not duplicate writes.

Pre-setup source review005 is independently passed in the adjacent
`depth-D6-source-review-005.json`; its exact canonical bytes must still match at
execution. Freeze helpers before actual setup.
`source-review-005-draft.json` is only a draft captured during preparation; refresh
it after integrations. Its status is `review`, and it grants no authority.
After setup, create a fresh review including the exact accepted archive/tree.

Current DO002 allocation is setup 1,800 seconds, CPU preparation 1,800 seconds,
GPU 3,600 seconds, 7,923,784,338 download bytes (weights plus the approved 6-GiB
dependency allowance), 9,663,676,416 artifact bytes, and one attempt. Global
caps remain 110/210 GiB. Actual remaining bytes/CPU time and GPU ownership must
be checked by root before each operation. New work stays within these bounds.
Capture/finalizer wrapper defaults are 180 seconds including 20 seconds reserved
for cleanup; root must charge actual elapsed and receipt assembly independently.

## Root commands

Run these from the canonical `plan069-depth-extension` checkout after integrating
this handoff. Paths in angle brackets are immutable root-reviewed inputs to fill
in after setup; do not execute commands with placeholders. Host script preparation
uses python3; actual CPU producers use the explicit qualified interpreter.

```bash
TASK_ROOT=/home/auss/git_repos/samaust/Experiments_4DGS/.local/plan069-worktrees/depth-extension
TASK_RUN=/home/auss/git_repos/samaust/Experiments_4DGS/.local/vipe-alternatives/plan031-20260913T032700Z
TASK_METHOD="$TASK_ROOT/docs/research/vipe-alternatives/plan031-execution/d6-preparation-001"
TASK_BOOTSTRAP=/home/auss/git_repos/samaust/Experiments_4DGS/.local/envs/stg-colmap/bin/python

"$TASK_BOOTSTRAP" -B "$TASK_METHOD/prepare_source_review.py" \
  --root "$TASK_ROOT" --output '<fresh-pre-setup-source-review-draft.json>'
# Independent review must verify the helper/recipe/DO records and pass this draft.
"$TASK_BOOTSTRAP" -B "$TASK_ROOT/scripts/basketball_vipe_moge_setup_dispatch.py" \
  --candidate D6 --run-id plan031-20260913T032700Z \
  --runtime-environment "$TASK_ROOT/docs/specs/plan031-execution/moge-runtime-recipes-001/D6-runtime-environment.json" \
  --source-review '<passed-pre-setup-source-review.json>'

"$TASK_BOOTSTRAP" -B "$TASK_METHOD/prepare_source_review.py" \
  --root "$TASK_ROOT" --setup "$TASK_RUN/jobs/plan069-D6-setup-001/result.json" \
  --output '<fresh-post-setup-source-review-draft.json>'
# Independently pass the post-setup review, checking archive/tree and current helpers.

python3 -B "$TASK_METHOD/prepare_request.py" --mode capture \
  --root "$TASK_ROOT" --run "$TASK_RUN" --interpreter "$TASK_BOOTSTRAP" \
  --source-review '<passed-post-setup-source-review.json>' \
  --disk-roots '<root-approved-disk-roots.json>' \
  --producer-output "$TASK_RUN/prepare/plan069-D6-native-cpu-001" \
  --wrapper-output "$TASK_RUN/prepare/plan069-D6-native-cpu-parent-001" \
  --output '<immutable-capture-request.json>'
"$TASK_BOOTSTRAP" -B "$TASK_METHOD/capture_wrapper.py" \
  --request '<immutable-capture-request.json>'
# Preserve receipt, verify cleanup and charge measured CPU once.
# Obtain independent commercial assessment of this exact installed manifest.

python3 -B "$TASK_METHOD/prepare_request.py" --mode finalize \
  --root "$TASK_ROOT" --run "$TASK_RUN" --interpreter "$TASK_BOOTSTRAP" \
  --source-review '<passed-post-setup-source-review.json>' \
  --disk-roots '<root-approved-disk-roots.json>' \
  --capture "$TASK_RUN/prepare/plan069-D6-native-cpu-001" \
  --commercial-assessment '<passed-D6-commercial-assessment.json>' \
  --producer-output "$TASK_RUN/prepare/plan069-D6-qualification-001" \
  --wrapper-output "$TASK_RUN/prepare/plan069-D6-finalize-parent-001" \
  --output '<immutable-finalize-request.json>'
"$TASK_BOOTSTRAP" -B "$TASK_METHOD/finalize_wrapper.py" \
  --request '<immutable-finalize-request.json>'
# Preserve receipt, verify cleanup and charge measured CPU once.

"$TASK_RUN/jobs/plan069-D6-setup-001/runtime/environment/bin/python" -B \
  "$TASK_METHOD/dispatch_driver.py" "$TASK_ROOT" \
  '<passed-post-setup-source-review.json>' \
  "$TASK_RUN/prepare/plan069-D6-qualification-001/qualification.json" \
  '<root-admitted-D6-qualitative-admission.json>' \
  '<fresh-existing-parent-directory>/D6-driver-result.json'
```

The disk-roots input is a list of the same `global`, `candidate` and
`runtime-cache` records used by the D5 wrapper: `role`, `path`,
`maximum_total_bytes`, `maximum_delta_bytes`. Root must derive current remaining
whole-slot/global allowances; copying D5 numeric baselines is insufficient.
Both wrapper and producer output directories must be fresh. Helpers fail on
changed records before admitting producers; producer evidence is still validated
against the stock admission/worker/result contract before native dispatch.

## Validation

Seventeen standard-library synthetic contract tests passed in 1.185 seconds. They
cover independent capture/finalize method bindings, archive/tree retention,
failed capture rejection, D5/D6 separation and admitted setup substitution.
All retained Python files parse successfully. The selected bootstrap has no mypy installed; no installation was attempted. These checks load no model and
use no GPU. The final canonical combined qualification remains root's gate.

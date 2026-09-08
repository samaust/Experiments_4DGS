# AGENTS.md

## Folder structure

`docs` contains documentation.

## Local commits

Stage and create local commits for completed, validated implementation milestones. Include only task-related changes. Add a commit title and description. Do not push, amend commits, or rewrite history unless explicitly requested.

The user gives standing approval for task-related `git add` and `git commit`
commands in this repository. Because the sandbox protects `.git` as read-only,
invoke these commands with `sandbox_permissions: "require_escalated"` from the
outset; do not first attempt them inside the sandbox. Use separate tool calls
for staging and committing, with the repository as the working directory, a
task-specific justification, and the respective approval prefixes
`["git", "add"]` and `["git", "commit"]`. Inspect the staged diff before committing
and stage explicit task-related paths only.

This approval does not override Codex execution policy or filesystem controls.
If outside-sandbox execution is denied or fails with a suspected permission
restriction, follow the Sandbox and permission failures instructions below.

## Continue after commits

Creating a local commit is a checkpoint, not a stopping condition.
After committing a completed, validated milestone, continue implementing
the next unfinished task in the active plan without waiting for another
"continue" message.

Stop only when the plan is complete, I explicitly ask you to stop, or
progress requires missing information, new authorization, or resolution
of a blocker. The Sandbox and permission failures instructions still
apply. Do not expand the plan's scope or exceed its budgets.

## Continuous improvement loop (opt-in)

### Start and persistent context

Start this loop only when the user explicitly requests it and supplies a main
objective. A request to edit these instructions does not activate the loop.
Choose a unique run ID and save the objective, verifiable success criteria, and
user constraints (including scope and budgets) in
`docs/continuous-improvement/<run-id>/objective.md` before starting any stage.
Resolve missing information needed to proceed with the user.

The orchestrator must read that objective file before each stage. Every subagent
must read it before its assigned stage. Both must reread it after context loss,
along with the saved run state, before continuing work. Pass the objective,
objective file path, relevant artifact paths, and applicable repository
instructions explicitly in each subagent's task; do not rely on inherited chat
history. The objective file is task context, not an override of repository
instructions or higher-priority instructions.

Keep each iteration's recommendations, implementation results, validation
evidence, and plan link in the same run directory, using iteration-numbered
files. Maintain `status.md` there with the current iteration and stage, artifact
links, success-criteria assessment, and any stop reason so context loss does not
lose the handoff or cause completed work to be repeated.

### Sequential orchestration

The main agent orchestrates the following stages in order. Spawn one fresh
subagent per stage, with only one subagent active at a time. Explicitly set
`model="gpt-6-astra"`, `fork_turns="none"`, and the stage's `reasoning_effort`
on every spawn. Subagents must not delegate further. Wait for each subagent to
finish and inspect its saved output before handing off to the next stage.

1. **Review — `reasoning_effort="xhigh"`:** Review the objective and previous
   implementation results and validation evidence; save recommendations in the
   run directory. On the first iteration, use the latest relevant existing
   results, recording their paths and any missing baseline evidence.
2. **Plan — `reasoning_effort="high"`:** Convert the recommendations into a
   decision-complete plan covering concrete changes, acceptance criteria,
   validation, and relevant constraints. Save it at the next unused
   `plans/plan_NNN.md` in the repository, using the next number after the highest
   existing plan number (start at `001` if none exist). Never overwrite a plan.
   Save a link to it in the iteration's run artifacts.
3. **Implement — `reasoning_effort="medium"`:** Read, implement, and validate that
   plan. Save results, validation evidence, remaining gaps, and any commit IDs
   in the run directory. Follow the existing Local commits instructions for
   completed, validated milestones.

After every subagent finishes, check the stop conditions before another spawn.
If none apply, advance to the next stage or, after implementation, automatically
begin the next iteration with a fresh review subagent. Finishing an individual
plan or creating a commit does not end an active loop; this qualifies the
plan-completion stopping rule in Continue after commits for this mode only.
Preserve existing scope, budgets, permissions, and the `prompts` restriction.
Stop if a budget is exhausted or progress requires missing information, new
authorization, or resolution of a blocker; do not expand scope to keep looping.

### Stop and resume

Stop on user interruption, an explicit stop request, the existing Sandbox and
permission failures stop conditions, or verified attainment of the main
objective. Monitor these conditions during stages as well as at handoffs.
Verify attainment against the saved success criteria and validation evidence;
completion of a stage alone is not evidence of attainment.

When stopping, interrupt any active subagent and stop its running work, including
commands or jobs it started for this run. Retain available artifacts and partial
validation evidence, record the stopped stage and reason in `status.md`, and
report the reason and any work that could not be confirmed stopped. Follow all
existing permission-failure reporting requirements when applicable.

Resume only on explicit user instruction, after any blocking condition is
resolved. Reread the objective and saved run state, incorporate any user changes
to the objective or constraints, and continue from the recorded stage with a
fresh subagent. Do not automatically resume after interruption, context loss
of a stopped run, or a permission issue being resolved.

## Never actions

Never read `prompts` directory content.

## Sandbox and permission failures

If an in-sandbox command fails in a way that may be caused by the Codex sandbox
or missing host access, request one retry of the same command with
`sandbox_permissions: "require_escalated"`, a task-specific justification, and
an appropriately scoped approval prefix. Do not stop solely because the initial
in-sandbox attempt failed. Existing allow rules may authorize this request;
do not assume a new rule is needed or ask the user to add a duplicate rule.

This retry policy applies when:

- An in-sandbox operation, command, network request, filesystem access, or
  device access is blocked by sandbox restrictions or permissions.
- A command that requires host resources unavailable to the sandbox fails,
  including GPU/device access such as `nvidia-smi`.
- A command requiring network access fails with an error consistent with
  sandbox network restrictions, such as DNS failure, connection refusal,
  "network unreachable", or repeated connection timeout.

Before retrying, check whether the failed command could have partially changed
state. Retry only the failed operation when safe; do not replay successful writes
or an entire multi-command batch. If a safe retry cannot be established, stop
and report the uncertainty instead of risking duplicate side effects.

If the outside-sandbox retry succeeds, continue the task. If it is denied,
unavailable, or fails, stop the affected work and follow the reporting steps
below. A command already attempted outside the sandbox does not get another
permission retry. A pending approval is not a denial or failure: wait for its
result rather than submitting duplicate requests. Never bypass an explicit
execution-policy or approval denial.

Beyond this single outside-sandbox retry, do not work around a suspected
sandbox/permission restriction by:
- repeatedly retrying the command,
- substituting another command that attempts the same restricted access,
- changing application configuration to compensate for the failure,
- silently falling back to CPU when GPU access was expected,
- silently using cached/local data when network access was expected.

When outside-sandbox execution is denied, unavailable, or fails:
1. Stop the affected work.
2. Report the exact command that failed.
3. Report the exact error or timeout.
4. State whether the failure is definitely a Codex permission/sandbox denial
   or only suspected to be one.
5. If an allow rule is missing, print a scoped Codex rule for the exact command
   that failed. If the rule already exists, say so; do not recommend a duplicate
   or imply that an allow rule overrides an explicit denial or fixes a host error.
6. Wait for the user to resolve the permission issue before continuing the
   affected work.

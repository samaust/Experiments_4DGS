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

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

If a command fails in a way that may be caused by the Codex sandbox or by
missing permission to execute outside the sandbox, stop the task and report
the failure to the user.

In particular, stop when:

- Codex reports that an operation, command, network request, filesystem
  access, device access, or privilege escalation was denied or blocked by
  sandbox, approval, execpolicy, or permissions.
- A command that requires host resources unavailable to the sandbox fails,
  including GPU/device access such as `nvidia-smi`.
- A command requiring network access fails with an error consistent with
  sandbox network restrictions, such as DNS failure, connection refusal,
  "network unreachable", or repeated connection timeout.

Do not work around a suspected sandbox/permission restriction by:
- repeatedly retrying the command,
- substituting another command that attempts the same restricted access,
- changing application configuration to compensate for the failure,
- silently falling back to CPU when GPU access was expected,
- silently using cached/local data when network access was expected.

When this happens:
1. Stop the affected work.
2. Report the exact command that failed.
3. Report the exact error or timeout.
4. State whether the failure is definitely a Codex permission/sandbox denial
   or only suspected to be one.
5. Print the Codex rule to add to allow the exact command that failed.
6. Wait for the user to resolve the permission issue before continuing the
   affected work.

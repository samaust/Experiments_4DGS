# AGENTS.md

## Folder structure

`docs` contains documentation.

## Python commands

Use `python3` for host commands; `python` is available only in Python virtual
environments. For virtual environments, use the explicit interpreter path.

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

For suspected sandbox restrictions or missing host access (filesystem, GPU,
network), request one outside-sandbox retry of the failed command using
`sandbox_permissions: "require_escalated"`, a task-specific justification and
scoped approval prefix. Reuse existing allow rules; await pending approval.

Before any retry, check partial state changes. Retry only the failed operation;
preserve successful writes. If duplication risk is unclear, stop and report it.

If outside-sandbox execution fails:

- **Bug or application error:** diagnose, fix and validate the cause, then retry.
  The user gives standing approval for retries after a relevant fix. Execution
  approvals, task scope, budgets and explicit attempt limits still apply.
- **Permission denial or unavailable host access:** stop affected work, report
  the exact command/error and whether the restriction is confirmed or suspected,
  then await resolution. Print a scoped allow rule only if missing; existing
  rules cannot override a denial or fix a host error.
- **Unclear cause:** investigate before retrying.

Never repeat a failed outside-sandbox command without addressing its cause.
Never bypass an explicit denial or substitute commands, configuration, CPU or
cached data to evade restricted access. After a successful retry, continue work.

## Agent skills

### Issue tracker

For issue lookup, creation, or triage, use GitHub Issues in
`samaust/Experiments_4DGS`. See `docs/agents/issue-tracker.md`.

### Triage labels

For issue triage, use the five canonical label names. See
`docs/agents/triage-labels.md`.

### Domain docs

For domain terms and design decisions, use the single-context layout.
See `docs/agents/domain.md`.

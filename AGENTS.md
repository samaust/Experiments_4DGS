# AGENTS.md

## Folder structure

`docs` contains documentation.

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

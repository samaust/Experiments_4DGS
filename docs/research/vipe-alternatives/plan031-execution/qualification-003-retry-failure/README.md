# Qualification retry preparation failure

Sandbox capture003 is retained intact at `../qualification-003/`; it failed AF_UNIX datagram helper fixtures with `PermissionError: [Errno 1] Operation not permitted`. It is not passing qualification.

The preparatory preservation command used the unavailable `python` alias (`/bin/bash: line 1: python: command not found`, exit127). The host retry therefore stopped before creating a runner or executing tests:

```bash
env PYTHONPATH=scripts .local/envs/stg-colmap/bin/python -B -m vipe_benchmark.s1_validation_capture docs/research/vipe-alternatives/plan031-execution/qualification-003 --timeout 240 > /tmp/plan031-qualification-003-controller.log 2>&1
```

`FileExistsError: [Errno 17] File exists: '/home/auss/git_repos/samaust/Experiments_4DGS/docs/research/vipe-alternatives/plan031-execution/qualification-003'`. This is an output preparation error, not a sandbox/permission denial. The existing scoped environment/Python approval prefix was accepted; no duplicate rule is needed. Qualification stopped under AGENTS.md.

The user subsequently explicitly answered **"Authorize corrected CPU qualification"** to the question explaining the failure, the fresh directory and CPU-only scope. Capture004 was launched outside sandbox in a fresh directory under that authorization. Capture003 and its failed host retry remain unchanged. This permission grants no GPU or setup allocation.

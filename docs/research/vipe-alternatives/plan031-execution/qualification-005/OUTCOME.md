# Capture005 timeout

The final integrated CPU capture used the unchanged 240-second contract:

```bash
env PYTHONPATH=scripts .local/envs/stg-colmap/bin/python -B -m vipe_benchmark.s1_validation_capture docs/research/vipe-alternatives/plan031-execution/qualification-005 --timeout 240 > /tmp/plan031-qualification-005-controller.log 2>&1
```

The execution receipt records `timed_out=true`, child returncode `-9`, outer exit137, and elapsed240.0863366900012 seconds. It terminated near the end of the supervisor suite, during `test_timeout_kills_sigterm_ignoring_group_within_allocation`. No test failure appeared in retained stderr before termination; the complete aggregate receipt does not exist. This is **not passing qualification**.

The timeout is a validation deadline, not a sandbox/permission denial. The environment/Python approval prefix was accepted; no duplicate rule is needed. The agent stopped qualification under AGENTS.md and requested authorization for one further fresh CPU-only capture under the same cap. No GPU/setup/model allocation was requested or consumed, and the cap was not increased.

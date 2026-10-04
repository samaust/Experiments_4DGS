# D6 qualification002 local IPC denial

The approved command, from the canonical depth-extension worktree:

```bash
/home/auss/git_repos/samaust/Experiments_4DGS/.local/envs/stg-colmap/bin/python -B scripts/basketball_vipe_depth_driver_qualification_recovery.py --request /home/auss/git_repos/samaust/Experiments_4DGS/.local/vipe-alternatives/plan031-20260913T032700Z/requests/plan069-D6-driver-qualification-002.json
```

It failed after20.271626626 seconds at `torch.cuda.init()` with CUDA304: `OS call failed or operation not supported on this OS`. Protected finish801 confirms cleanup, no survivors and no exceeded deadline.

The retained trace confirms the reviewed creation-only guard permits the observed Unix socket creation. It then denies a local `/tmp/nvidia-mps/control` connect and an abstract `cuda-uvmfd` bind with `EPERM`. This is a confirmed restriction of our own reviewed guard; it is not evidence of a Codex sandbox or host GPU permission denial. The trace does not independently prove which denied call causes CUDA304.

The exact attempt is consumed. Affected D6 execution is stopped. A changed guard requires review and fresh explicit authority; an allow rule cannot fix this application guard. No failed attempt or trace supplies passing qualification credit. Unaffected D9 CPU preparation continues.

# Plan 024 execution status

2026-09-08: **Blocked during Stage A host-administration preflight. Plan 024 is incomplete.**
This campaign does not activate or resume the continuous improvement loop.

The user authorized implementation of [plan 024](../../../plans/plan_024.md).
Repository instructions require stopping affected work when an outside-sandbox
permission attempt fails and waiting for the user to resolve the issue.

## Evidence

- Host: Ubuntu 24.04.4 LTS, user `auss` (UID 1000).
- `nvidia-smi` succeeded: RTX 4090, 24,564 MiB, driver 595.84,
  advertised CUDA compatibility 13.2. This establishes host visibility only;
  CUDA execution and container GPU access remain unverified.
- `command -v docker` found no executable. `dpkg-query -W docker-ce docker.io
  containerd.io nvidia-container-toolkit sudo` reported the four runtime packages
  absent and sudo version `1.9.15p5-3ubuntu5.24.04.2`.
- Exact failing command: `sudo -n true`, requested directly with
  `sandbox_permissions="require_escalated"`, prefix `["sudo", "-n", "true"]`.
  Exit code 1; exact output: `sudo: a password is required`.
- The command reached sudo; no automatic approval rejection was returned.
  This is a host authentication failure, not evidence of a Codex sandbox denial.
  No missing Codex allow rule was established. Adding one would not provide
  sudo authentication. No retry or alternative privilege route was attempted.
- No host installation, environment modification, baseline setup, data download,
  scientific fit, training, or rendering job started. No campaign jobs remain active.
- NVIDIA catalog discovery (`npx skills add nvidia/skills --list`) completed;
  no skill installation was requested. Official provisioning documentation was
  consulted: [Docker Ubuntu installation](https://docs.docker.com/engine/install/ubuntu/)
  and [NVIDIA Container Toolkit installation](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html).

## Budget checkpoint

The unchanged `.local/runs/plan-004-training-budget.json` has SHA-256
`d0b4daa1aee79361580af3a1bf8fbc597148db7775b26f169a0a1b2e6ac90957`.
All 22 recorded attempts are completed. Total charge is 22,523.41725398203 seconds
of 86,400 seconds; 63,876.58274601797 seconds remain globally.

| Existing method/scene | Charged seconds |
| --- | ---: |
| STG Lite / SelfCap | 3819.048855319008 |
| STG Full / SelfCap | 4652.0273592330195 |
| ATGS / SelfCap | 7026.23324900998 |
| FreeTimeGS / SelfCap | 7026.107790420021 |

No Basketball training entries exist. The existing two-hour method/scene ceilings
remain binding. Plan 024 adds a 12-GPU-hour campaign ceiling with nontransferable
4/3/2/2/1-hour allocations. No research GPU work ran. Reserve one second against
the first allocation for the successful initial `nvidia-smi` visibility check
(conservative accounting, not a measured CUDA workload). Runtime provisioning
and baseline compatibility attempts have not started; this was a privilege preflight.
Historical consumed allocations are not reset by this checkpoint.

## Remaining work and resume prerequisite

Host administration must be made available for the authorized Docker Engine and
NVIDIA Container Toolkit provisioning, followed by an explicit instruction to
continue. Do not ask for or record a sudo password in repository artifacts or chat.
Recheck actual installed state on resume before performing any installation.

The next numbered execution specification has not been created. The literature
study, verified citation map, code/benchmark matrix, protocol freeze, timing
interface, fixtures, baseline setup, pilots, reconstruction comparisons, and
ranked scientific recommendation remain outstanding. No method availability,
accuracy, or reconstruction-benefit conclusion is established by this preflight.
Frames 200–249 were not opened. No source or calibration artifacts were modified.

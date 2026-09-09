# Plan 024 execution status

2026-09-08: **Active: Basketball pilot execution. Plan 024 is incomplete.**
This campaign does not activate or resume the continuous improvement loop.

The user supplied `/tmp/plan024-sync4drf.pdf` and explicitly resumed. Its title
and text extraction are verified; [source provenance](sync4drf-source.json)
retains its hash. The historical HTTP refusal below is resolved through the
user-provided file. Continue remaining authorized work; no additional download
of this paper is needed.

## Synchronization pilots completed; reconstruction active

All three Sync-NeRF pilots exited successfully within their caps at 43,049,
42,944 and 42,999 updates. The [matched-checkpoint analysis](syncnerf-matched-checkpoint.json)
uses update 42,000 for all seeds; non-reference seed ranges are 3.28–5.42 ms.
These describe optimizer repeatability, not physical accuracy. [Final exports](syncnerf-results.json)
retain each actual endpoint; the native 90,001-step schedule remains unreproduced.
The [offset plot](syncnerf-offsets.svg) shows the selected-camera estimates.

The [timing decision](timing-decision.json) freezes no eligible full-rig correction.
Final-window images remain unopened. STG Full zero seed 0 completed 5,000 updates
in 222.49 charged seconds; seed 1 is active. Four further zero controls,
fresh reload/render evaluation and final reporting are pending.
Use [evaluation protocol v3](evaluation-protocol-v3.json), [benchmark/code status](benchmark-code-matrix.md),
[metric interface evidence](metric-interface-check.json) and [global training admission](global-training-admission.json).
The original central ledger was copied byte-for-byte to
`.local/sync-pivot/central-training-before.json` before reconstruction charges.
No consumed allocation or historical attempt was reset.

## Training protocol checkpoint

[Training settings](training-protocol.json) are frozen before scientific GPU execution.
Eight-camera inputs contain 800 fit-window images; no new final-window images
were opened. Native adapters pass CPU ray/time/bucket checks (15 targeted tests).
FreeTimeGS CPU initialization produces 45,828 local static points. Exact benchmark
timing labels and VisualSync core preprocessing remain unavailable as documented
in the protocol. Proceed with three Sync-NeRF seeds and three zero controls for
each reconstruction method; no unsupported full-rig correction is applied.

The sections below preserve earlier checkpoints; current execution and remaining
GPU allocations are authoritative in gpu-budget.json.

## Resolved paper-access blocker

The required Sync-4DRF full-paper download was attempted outside the sandbox:

```sh
curl -fL --max-time 45 https://openreview.net/pdf/2adf84139e687f06c457b0f1817efab3f4159c0e.pdf -o /tmp/plan024-sync4drf.pdf
```

It exited 22 with `curl: (22) The requested URL returned error: 403`.
This is a remote HTTP access refusal; it is not a demonstrated Codex sandbox
or automatic approval denial. No missing Codex allow rule was established;
an allow rule would not resolve the remote response. The command was already
outside the sandbox and receives no further permission retry. Required paper
access is stopped under the repository permission-failure instructions, pending
user resolution and explicit resume. No GPU job remains active.

Sync-NeRF setup milestone is committed as `4ac6f1c`. Training, benchmark runs,
Basketball integration and final reporting remain incomplete. See the
[audit checkpoint](audit-checkpoint.md) for findings retained before this stop.

## Basketball preparation milestone

The [literature matrix](literature.md) and [citation map](citation-map.md) are
committed in `d63c693`. Source and benchmark limitations remain explicit.
The [frozen rig/cadence audit](basketball-freeze.json) preserves the accepted
calibration/scale hashes and selects Sync-NeRF cameras 1, 2, 4, 5, 6, 7, 9, 11
by the specified shared-track expansion. All 8,500 source PTS values match 25 fps.
[Preparation evidence](basketball-preparation.json) records 1,700 undistorted
reconstruction images, 1,350 training keys, zero adjacent exact duplicates in
frames 0–49, and a 5,093-point static initialization recolored on 30 training
cameras at frame 25. This prior does not contain reconstructed player motion.

The [saved SIFT/LK common-estimator diagnostic](sift-common-graph.json) records
all 561 pairs, retains 67 passing saved edges and covers eight cameras from
reference 1. Two bridges remain in the whole graph. The empty learned graph is
labeled unavailable, not a failed learned scientific run. No diagnostic timing
is approved for reconstruction. Final-window images remain unopened.

Eighteen timing/analytic/scene tests and ten campaign/central-budget tests pass.
No scientific GPU runs have started. Backend trainer integration, Sync-NeRF
pilots, zero controls, reload/render evaluation and the final recommendation
remain unfinished. Budget reservations now support per-run caps while preserving
the central 24-hour ceiling. No historical GPU or training charge was reset.

## Current handoff

The isolated runtime is built; the timing interface and independent analytic
controls pass 13 CPU tests. Sync-NeRF setup attempt 1 compiled tiny-cuda-nn but
its entrypoint failed because scikit-image was absent. Attempt 2 adds the author
required dependency and passes the offline GPU-enabled CLI import check.
Both compatibility attempts are consumed; training remains unverified.
See [setup accounting](setup-accounting.json), [GPU accounting](gpu-budget.json),
and [dependency lock](syncnerf-requirements.lock). No GPU job is running.
UDBD Box metadata and image folders resolve, but timing-label provenance remains
under audit. SyncTrack4D's dataset reference is Dynamic Gaussian Marbles;
exact release identifiers remain unresolved. VisualSync's original archive has
unfinished pair-script assignments and missing matching helpers; full pipeline
availability remains under audit. No final-window images have been opened.

The user resolved host group membership, supplied successful non-sudo Docker/GPU
output, and explicitly resumed Plan 024. Docker now works through approved
outside-sandbox execution. [Runtime evidence](runtime-check.json) retains the
failed sandbox check and successful retry. No research GPU workload has started.
The user's no-sudo instruction still applies. A subsequent user interruption was
explicitly resumed; `docker ps` confirmed no containers remained running.

The execution specification is [Plan 025](../../../plans/plan_025.md).
[Source pins](source-pins.json) identify cloned official VisualSync, Sync-NeRF
and MultiViewUnsynch revisions plus four original VisualSync scripts. Downloaded
original code is retained at `.local/sync-pivot/visualsync-original/`. The original
archive contains pairwise and global synchronization implementations omitted from
the main checkout; tracking/matching subdirectory audit is next. Do not conclude
VisualSync is unavailable based solely on its GitHub checkout.

[Syntax audit](source-syntax-audit.json) found an upstream `SyntaxError` at line
1081 of `shaowei_sync_v6.py` (`video1_len =`); the following `end_idx` assignment
is also unfinished. The other three downloaded original scripts parse. This is
a demonstrated release defect, not a scientific failure. Compatibility work must
preserve original hashes and validate any repair before claiming runnable status.

The original Sync-NeRF README's UDBD URL
`https://drive.google.com/drive/folders/1wvLtucVrmFf7fj-kWr-HMk3boaI46cIX`
returned HTTP 404 to outside-sandbox `curl -fL --max-time 45` (exit 22,
`curl: (22) The requested URL returned error: 404`). This is a release-link
availability result, not a demonstrated sandbox denial. No retry of that link
is authorized by the permission-retry rule. Exact benchmark availability remains
under audit using the separately linked project-page dataset index.

The checkpoint sections below retain historical evidence. Superseded socket
blockers and historical statements that the next plan is not created do not
describe the current handoff. Leave the user's untracked `.codex/` untouched.

## Resume checkpoint

The user installed the runtime and explicitly requested continuation. Installed
packages now verified by `dpkg-query -W docker-ce docker-ce-cli containerd.io
nvidia-container-toolkit`:

- Docker Engine and CLI: `5:29.8.0-1~ubuntu.24.04~noble`.
- containerd.io: `2.3.5-1~ubuntu.24.04~noble`.
- NVIDIA Container Toolkit: `1.20.0-1`.

The user explicitly declined granting sudo access. Privileged commands must be
provided for the user to run locally; no sudo invocation was made on resume.
`docker version` failed inside the sandbox and on its one required
`require_escalated` retry (prefix `["docker", "version"]), both with exit code 1:

```text
permission denied while trying to connect to the docker API at unix:///var/run/docker.sock
```

The client reports version 29.8.0, API 1.56, context `default`. Server and GPU
container access remain unverified. No automatic approval rejection occurred;
host socket permissions are the apparent cause, rather than a demonstrated
Codex sandbox denial. No missing allow rule was established; a Codex allow rule
does not grant Unix socket access. No alternative socket or privilege route was
attempted. Container work is stopped, with no new GPU charge or active jobs.

The user can run `sudo docker version` and the previously supplied GPU container
check locally and return their output. Subsequent privileged workload commands
must likewise be prepared for user execution unless the user explicitly chooses
another access arrangement. Do not grant Docker group membership or change socket
permissions on the user's behalf. The original preflight record below is historical.

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

Runtime installation is now verified; the current prerequisite is user-operated
Docker execution as described in the resume checkpoint. Do not ask for or record
a sudo password in repository artifacts or chat. Preserve the user's refusal to
grant sudo access on subsequent resumes.

The next numbered execution specification has not been created. The literature
study, verified citation map, code/benchmark matrix, protocol freeze, timing
interface, fixtures, baseline setup, pilots, reconstruction comparisons, and
ranked scientific recommendation remain outstanding. No method availability,
accuracy, or reconstruction-benefit conclusion is established by this preflight.
Frames 200–249 were not opened. No source or calibration artifacts were modified.

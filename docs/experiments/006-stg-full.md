# Experiment 006: STG Full

Status: **SelfCap training/rendering integration executed; experiment incomplete**.

Full completed initial training/resume checks, then a fresh 2,000-step run
including densification and two EMS insertions, ending at 667,064 Gaussians.
It rendered all 60 held-out timestamps and the 20-pose sweep offline. This does not
establish quality at the agreed training budget. Basketball is still blocked
on calibration. See the [training integration record](contender-training-20260906.md)
for commands, budget charges, limitations and remaining gates.

Full subsequently resumed to iteration 5000, ending at 211,618 Gaussians after
the default opacity reset/pruning. The [5,000-step record](contender-full-5000-20260906.md)
contains the longer run, offline evaluation, checked Lite comparison and current
budget charges. It remains incomplete against the 30,000-step schedule; the
remaining native continuation is still pending.

Release audit, 2026-09-06: downloaded `techni_Birthday_allcam_allpoints.zip`
from `stack93/spacetimegaussians` revision `9534842`. Despite its unsuffixed
filename, saved `cfg_args` explicitly identifies `model='ours_lite'`; the
archive has no decoder `.pt`. It is not suitable for validating Full. Local
archive: `.local/downloads/stg-full/techni_Birthday_allcam_allpoints.zip`.

Use the shared [contender protocol](../contender-experiments.md), the STG source
revision and compatibility patch recorded in [section 6](section6-evidence.md).
This run must retain and validate the appearance decoder state. The native
preview helper accepts `--model full --decoder PATH` and refuses a missing or
mismatched decoder.

Provisional held-out metrics, reload checks, and visual findings are recorded in
the [growth/offline record](contender-growth-20260906.md). The native warm-render
benchmark at iteration 2000 is 293.384 FPS at 1890×1061. The complete checkpoint
retains the appearance decoder and optimizer state; exported inference files
include both the PLY and decoder sidecar. Do not use the all-camera `sear_steak`
checkpoint as held-out evidence.

Native Full forward/backward compatibility is now validated on synthetic points
through a full-size SelfCap manifest camera, including finite decoder gradients.
Native synthetic optimizer checkpoint restoration also passes exact next-step
equality. See the [data and integration record](contender-data-20260906.md).
These checks do not constitute matched-scene training or quality evaluation.

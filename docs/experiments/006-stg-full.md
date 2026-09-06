# Experiment 006: STG Full

Status: **SelfCap training/rendering integration executed; experiment incomplete**.

Full completed two training steps, resumed for two more in a fresh process,
and rendered all 60 held-out timestamps and the 20-pose sweep. This does not
establish quality at the agreed training budget. Basketball is still blocked
on calibration. See the [training integration record](contender-training-20260906.md)
for commands, budget charges, limitations and remaining gates.

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

Results, held-out metrics, reload equality, and visual findings are not yet
available. Do not use the all-camera `sear_steak` checkpoint as held-out evidence.

Native Full forward/backward compatibility is now validated on synthetic points
through a full-size SelfCap manifest camera, including finite decoder gradients.
Native synthetic optimizer checkpoint restoration also passes exact next-step
equality. See the [data and integration record](contender-data-20260906.md).
These checks do not constitute matched-scene training or quality evaluation.

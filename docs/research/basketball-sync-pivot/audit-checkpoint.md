# Source audit checkpoint — 2026-09-08

This is partial evidence, not the completed literature matrix or recommendation.
The campaign remains incomplete. No scientific timing or reconstruction run has
been completed; the Sync-NeRF CLI check establishes imports only.

## Benchmark provenance

SyncTrack4D v1 §4.1 specifies six Panoptic scenes, 150 frames and 31 cameras,
with one test camera, but does not identify the basketball release/start frame.
Its reference [36] resolves to Dynamic Gaussian Marbles. That project's released
dataset table lists DyCheck, monocular NVIDIA and other collections, without a
Panoptic basketball mapping. Thus following this citation has not resolved the
exact required benchmark; do not substitute a similarly named sequence.
[SyncTrack4D v1](https://arxiv.org/html/2512.04315v1),
[Marbles official release](https://github.com/coltonstearns/dynamic-gaussian-marbles).

The official Sync-NeRF project-page Drive index resolves to Box camera folders
and `transforms.json`. The downloaded metadata has 14 poses at 512×512, but no
timing/offset fields. Image acquisition and ground-truth label provenance remain
unfinished. Metadata alone does not establish synchronized capture or justify
a supplied-ground-truth control. Retained local metadata:
`.local/sync-pivot/box-transforms.json`.

## IFID paper inspection

The publisher-linked PDF was retrieved after a successful outside-sandbox retry
of an initial sandbox domain restriction. Local text is
`/tmp/plan024-ifid.txt`. The paper describes ten cameras at 10 fps, a 10 ms
display and 1 ms exposure, with timer readings propagated by frame counts.
This is physical fractional timing evidence at the display's resolution, subject
to the assumed stable cadence. It uses five-frame pose inputs and separate
inter/intra-frame classification. Table 1 reports 0.83-frame mean error for its
method, not demonstrated 10 ms mean accuracy.

There is an internal dataset-count inconsistency: the abstract says 382,500;
the dataset paragraph says 352,500, while 8,500 groups × 45 camera pairs equals
382,500. The listed train/validation/test group counts sum to 8,500. Preserve the
discrepancy rather than silently choosing one statement. The publication links
InSynFormer on GitHub; current code/data accessibility still needs verification.
[Official IFID paper](https://ojs.aaai.org/index.php/AAAI/article/download/28174/28346).

## Scope safeguards

Existing accepted calibration validation includes static observations in frames
200–249. Reading that saved validation is not a new timing evaluation; it also
means this window cannot be described as untouched by all historical work.
No new final-window images were opened in this campaign. Freeze timing before
the plan's one final timing evaluation, and disclose this prior calibration use.

Sync-NeRF's two compatibility attempts are consumed. Attempt 1 built the CUDA
extension but failed an import; attempt 2 adds scikit-image and passes CLI help.
The image and dependency lock are retained. No test-view optimization ran.
Conservative GPU charge is 241.13570702903057 seconds in the checks allocation;
scientific run allocations remain unused.

## Access stop

The outside-sandbox Sync-4DRF OpenReview download returned HTTP 403. The exact
command, error and stop basis are in [status](status.md). Do not retry or use
another access route to bypass this refusal. Search snippets do not replace
full-paper inspection for the required reference/protocol audit.

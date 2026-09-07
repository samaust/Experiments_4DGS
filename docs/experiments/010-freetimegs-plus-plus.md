# Experiment 010: FreeTimeGS++

Status: **pending source/data validation**.

Release search on 2026-09-06 found no author implementation link in the
[paper](https://arxiv.org/abs/2605.03337); its abstract promises a future release.
Fixed B cannot currently be executed from an identified author source. This is
an availability gate for both scenes, not a quality result. No training time
has been consumed. A new implementation from the paper is outside plan 004.

Run fixed configuration B for both scenes without scene-wise selection. Record
the exact implementation revision and configuration, keeping it separate from
the reproduced FreeTimeGS result. Paper numbers are not local measurements.

## Plan 005 Basketball calibration update — 2026-09-06

The [ViPE pilot](basketball-calibration-20260906.md) audited all 34 videos but
stopped at camera 4 intrinsic instability: 20.2948% focal range relative to the
median, above the 20% pilot threshold fixed before inference. No accepted
estimated calibration or synchronization was produced. Basketball training and
evaluation remain blocked; this task charged zero training seconds and left
the existing method allocations unchanged.
The independent implementation blocker also remains; calibration does not
authorize a substitute implementation.

The subsequent user-authorized **25%** pilot passed. The
[all-camera continuation](basketball-calibration-20260906.md#all-camera-continuation-outcome-blocked-at-camera-5)
then stopped at camera 5 (**26.0539% > 25%**); the other 33 cameras passed the
intrinsic check. This supersedes camera 4 as the current calibration blocker.
Shared geometry, synchronization and Basketball training remain unexecuted.
Cumulative calibration charge is 323.0525 seconds; training charge remains zero.


### Current 24-camera variant under the 20% gate

The user restored the intrinsic-prior gate to 20% and excluded all failing
cameras. The current variant has 24 cameras: 21 training and held-outs 0, 10, 30,
with 1,200 expected images (150 held-out). [The complete bounded rerun](basketball-intrinsic20.md)
finished all 32 independent reconstructions. Its best comparison is **0.7182
degrees / 1.1185% of rig diameter**, failing the unchanged 0.5 degree / 1% gate
only at training camera 19. All retained priors and ten-frame focus screens pass.
Calibration remains blocked; training/evaluation did not start. Cumulative GPU
calibration charge is 1,056.0873 seconds; original training budgets are unchanged.

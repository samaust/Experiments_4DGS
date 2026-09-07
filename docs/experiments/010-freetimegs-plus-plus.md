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


### Current 33-camera variant after camera 5 removal

The user removed physical camera 5. The active split is 29 training cameras and
four held-out cameras, with 1,650 expected images (200 held-out). The
[retained-camera continuation](basketball-no-camera5.md) passed all retained
priors and registered all training cameras, but failed independent-window pose
stability after PINHOLE, the single radial alternative and bounded RoMa matching.
Converged final candidates disagree by up to **7.3065°** and **4.1972% of rig
diameter**, above the unchanged 0.5°/1% limits. Shared calibration and
synchronization remain unaccepted; Basketball training/evaluation did not start.
Calibration charge is 718.3131 seconds cumulatively; training allocations and
SelfCap results are unchanged. This supersedes camera 5 as the current blocker.

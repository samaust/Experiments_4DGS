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

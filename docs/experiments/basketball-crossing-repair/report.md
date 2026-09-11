# Basketball crossing repair — Plan 028

Production completed 24 endpoints (two recipes × three seeds × four policies), with 480,000 continuation updates. Frozen evaluation coverage is 8,400 metric rows.

| Recipe | Seed | Training | Lifetime | Gap motion MAE | Gap dynamic LPIPS | Video |
|---|---:|---|---|---:|---:|---|
| dense-coarse | 0 | all-times | original | 0.04737 | 0.05712 | [camera 0](../../../.local/basketball-crossing-repair/videos/freetimegs-dense-coarse-camera0-seed0/comparison.mp4) |
| dense-coarse | 0 | all-times | repaired | 0.04611 | 0.05593 | [camera 0](../../../.local/basketball-crossing-repair/videos/freetimegs-dense-coarse-camera0-seed0/comparison.mp4) |
| dense-coarse | 0 | holdout | original | 0.08516 | 0.07757 | [camera 0](../../../.local/basketball-crossing-repair/videos/freetimegs-dense-coarse-camera0-seed0/comparison.mp4) |
| dense-coarse | 0 | holdout | repaired | 0.08263 | 0.07604 | [camera 0](../../../.local/basketball-crossing-repair/videos/freetimegs-dense-coarse-camera0-seed0/comparison.mp4) |
| dense-coarse | 1 | all-times | original | 0.04771 | 0.05838 | [camera 0](../../../.local/basketball-crossing-repair/videos/freetimegs-dense-coarse-camera0-seed1/comparison.mp4) |
| dense-coarse | 1 | all-times | repaired | 0.04507 | 0.05629 | [camera 0](../../../.local/basketball-crossing-repair/videos/freetimegs-dense-coarse-camera0-seed1/comparison.mp4) |
| dense-coarse | 1 | holdout | original | 0.08411 | 0.07970 | [camera 0](../../../.local/basketball-crossing-repair/videos/freetimegs-dense-coarse-camera0-seed1/comparison.mp4) |
| dense-coarse | 1 | holdout | repaired | 0.08224 | 0.07725 | [camera 0](../../../.local/basketball-crossing-repair/videos/freetimegs-dense-coarse-camera0-seed1/comparison.mp4) |
| dense-coarse | 2 | all-times | original | 0.04639 | 0.05802 | [camera 0](../../../.local/basketball-crossing-repair/videos/freetimegs-dense-coarse-camera0-seed2/comparison.mp4) |
| dense-coarse | 2 | all-times | repaired | 0.04580 | 0.05659 | [camera 0](../../../.local/basketball-crossing-repair/videos/freetimegs-dense-coarse-camera0-seed2/comparison.mp4) |
| dense-coarse | 2 | holdout | original | 0.08239 | 0.07864 | [camera 0](../../../.local/basketball-crossing-repair/videos/freetimegs-dense-coarse-camera0-seed2/comparison.mp4) |
| dense-coarse | 2 | holdout | repaired | 0.08012 | 0.07557 | [camera 0](../../../.local/basketball-crossing-repair/videos/freetimegs-dense-coarse-camera0-seed2/comparison.mp4) |
| dense-cropped | 0 | all-times | original | 0.04698 | 0.05849 | [camera 0](../../../.local/basketball-crossing-repair/videos/freetimegs-dense-cropped-camera0-seed0/comparison.mp4) |
| dense-cropped | 0 | all-times | repaired | 0.04600 | 0.05649 | [camera 0](../../../.local/basketball-crossing-repair/videos/freetimegs-dense-cropped-camera0-seed0/comparison.mp4) |
| dense-cropped | 0 | holdout | original | 0.08514 | 0.07930 | [camera 0](../../../.local/basketball-crossing-repair/videos/freetimegs-dense-cropped-camera0-seed0/comparison.mp4) |
| dense-cropped | 0 | holdout | repaired | 0.08239 | 0.07721 | [camera 0](../../../.local/basketball-crossing-repair/videos/freetimegs-dense-cropped-camera0-seed0/comparison.mp4) |
| dense-cropped | 1 | all-times | original | 0.04560 | 0.05703 | [camera 0](../../../.local/basketball-crossing-repair/videos/freetimegs-dense-cropped-camera0-seed1/comparison.mp4) |
| dense-cropped | 1 | all-times | repaired | 0.04484 | 0.05586 | [camera 0](../../../.local/basketball-crossing-repair/videos/freetimegs-dense-cropped-camera0-seed1/comparison.mp4) |
| dense-cropped | 1 | holdout | original | 0.08459 | 0.07984 | [camera 0](../../../.local/basketball-crossing-repair/videos/freetimegs-dense-cropped-camera0-seed1/comparison.mp4) |
| dense-cropped | 1 | holdout | repaired | 0.08290 | 0.07759 | [camera 0](../../../.local/basketball-crossing-repair/videos/freetimegs-dense-cropped-camera0-seed1/comparison.mp4) |
| dense-cropped | 2 | all-times | original | 0.04758 | 0.05786 | [camera 0](../../../.local/basketball-crossing-repair/videos/freetimegs-dense-cropped-camera0-seed2/comparison.mp4) |
| dense-cropped | 2 | all-times | repaired | 0.04660 | 0.05659 | [camera 0](../../../.local/basketball-crossing-repair/videos/freetimegs-dense-cropped-camera0-seed2/comparison.mp4) |
| dense-cropped | 2 | holdout | original | 0.08593 | 0.07872 | [camera 0](../../../.local/basketball-crossing-repair/videos/freetimegs-dense-cropped-camera0-seed2/comparison.mp4) |
| dense-cropped | 2 | holdout | repaired | 0.08344 | 0.07576 | [camera 0](../../../.local/basketball-crossing-repair/videos/freetimegs-dense-cropped-camera0-seed2/comparison.mp4) |

## Assessment

The fixed repair, policy labels, paired gap effects, and endpoint resource records are captured in [results.json](results.json). Lower is better for MAE, LPIPS, and temporal difference error; higher is better for PSNR and SSIM.

| Condition | Fixed? | Evidence assessment |
|---|---|---|
| Coarse, holdout, original | Unverified | Complete endpoint, metric, and video evidence; no automated test can establish visual absence of the burst. |
| Coarse, holdout, repaired | Unverified | Complete endpoint, metric, and video evidence; frame inspection is required before calling the condition fixed. |
| Coarse, all-times, original | Unverified | Complete endpoint, metric, and video evidence; frame inspection is required before calling the condition fixed. |
| Coarse, all-times, repaired | Unverified | Complete endpoint, metric, and video evidence; frame inspection is required before calling the condition fixed. |
| Cropped, holdout, original | Unverified | Complete endpoint, metric, and video evidence; frame inspection is required before calling the condition fixed. |
| Cropped, holdout, repaired | Unverified | Complete endpoint, metric, and video evidence; frame inspection is required before calling the condition fixed. |
| Cropped, all-times, original | Unverified | Complete endpoint, metric, and video evidence; frame inspection is required before calling the condition fixed. |
| Cropped, all-times, repaired | Unverified | Complete endpoint, metric, and video evidence; frame inspection is required before calling the condition fixed. |

The 24 videos use all 50 source frames at 25 fps and six consistent panels: ground truth, the 50k parent, and arms A–D. Fixed crops accompany the videos in the artifact directory. Visual condition-fixed status must be judged from those frame sequences; aggregate scores alone are insufficient.

The diagnosis evidence and its attribution limitation are in [diagnosis.json](diagnosis.json). All endpoint reload probes passed, all-times rows retain their training-observation labels, and historical sources remain under the study artifact root.

- [Full numeric results](results.json)
- [Diagnosis evidence](diagnosis.json)
- [Video manifest](../../../.local/basketball-crossing-repair/videos/artifacts.json)
- [Production manifest](../../../.local/basketball-crossing-repair/production.json)
- [Metric manifest](../../../.local/basketball-crossing-repair/metrics/records.json)

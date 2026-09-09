# Plan 026 artifact browser

[Final report](report.md) explains the incomplete dense arm and measured sparse
results. Large local artifacts require this experiment workspace.

- [Checkpoint/render/metric index](analysis-final/artifact-index.json): all 30
  available curve results, hashes, and measured times.
- [Numerical curves](analysis-final/curves.csv) and [paired statistics](analysis-final/statistics.json).
- [Training resources](resources-final/trajectories.json) and [charged compute](analysis-final/accounting.json).
- [Final audit](final-validation.json), [reload checks](curve-render-validation.json),
  and [visual checks](visual-validation.json).
- [Dense pilot review](pilot-review.md) and [pilot evidence](pilot-evidence.json).
- [Player/court/display assessment](visual-assessment.md).
- [5,000-update PNG/video manifest](../../../.local/basketball-dense-temporal/visuals-005000-v2/artifacts.json)
  and [50,000-update PNG/video manifest](../../../.local/basketball-dense-temporal/visuals-050000/artifacts.json).

Each video shows ground truth, STG Full, and sparse FreeTimeGS for 50 source
frames at 25 fps. The dense arm is absent because its prerequisite failed.

| Held-out camera | Seed | Baseline video | Endpoint video |
| --- | --- | --- | --- |
| 0 | 0 | [5,000](../../../.local/basketball-dense-temporal/visuals-005000-v2/camera0-seed0.mp4) | [50,000](../../../.local/basketball-dense-temporal/visuals-050000/camera0-seed0.mp4) |
| 0 | 1 | [5,000](../../../.local/basketball-dense-temporal/visuals-005000-v2/camera0-seed1.mp4) | [50,000](../../../.local/basketball-dense-temporal/visuals-050000/camera0-seed1.mp4) |
| 0 | 2 | [5,000](../../../.local/basketball-dense-temporal/visuals-005000-v2/camera0-seed2.mp4) | [50,000](../../../.local/basketball-dense-temporal/visuals-050000/camera0-seed2.mp4) |
| 10 | 0 | [5,000](../../../.local/basketball-dense-temporal/visuals-005000-v2/camera10-seed0.mp4) | [50,000](../../../.local/basketball-dense-temporal/visuals-050000/camera10-seed0.mp4) |
| 10 | 1 | [5,000](../../../.local/basketball-dense-temporal/visuals-005000-v2/camera10-seed1.mp4) | [50,000](../../../.local/basketball-dense-temporal/visuals-050000/camera10-seed1.mp4) |
| 10 | 2 | [5,000](../../../.local/basketball-dense-temporal/visuals-005000-v2/camera10-seed2.mp4) | [50,000](../../../.local/basketball-dense-temporal/visuals-050000/camera10-seed2.mp4) |
| 20 | 0 | [5,000](../../../.local/basketball-dense-temporal/visuals-005000-v2/camera20-seed0.mp4) | [50,000](../../../.local/basketball-dense-temporal/visuals-050000/camera20-seed0.mp4) |
| 20 | 1 | [5,000](../../../.local/basketball-dense-temporal/visuals-005000-v2/camera20-seed1.mp4) | [50,000](../../../.local/basketball-dense-temporal/visuals-050000/camera20-seed1.mp4) |
| 20 | 2 | [5,000](../../../.local/basketball-dense-temporal/visuals-005000-v2/camera20-seed2.mp4) | [50,000](../../../.local/basketball-dense-temporal/visuals-050000/camera20-seed2.mp4) |
| 30 | 0 | [5,000](../../../.local/basketball-dense-temporal/visuals-005000-v2/camera30-seed0.mp4) | [50,000](../../../.local/basketball-dense-temporal/visuals-050000/camera30-seed0.mp4) |
| 30 | 1 | [5,000](../../../.local/basketball-dense-temporal/visuals-005000-v2/camera30-seed1.mp4) | [50,000](../../../.local/basketball-dense-temporal/visuals-050000/camera30-seed1.mp4) |
| 30 | 2 | [5,000](../../../.local/basketball-dense-temporal/visuals-005000-v2/camera30-seed2.mp4) | [50,000](../../../.local/basketball-dense-temporal/visuals-050000/camera30-seed2.mp4) |

# Experiment 004: Mango-GS sear_steak

Status: **completed and reproduced exactly**. Date: 2026-09-05.

## Purpose and reproduction

Question: can the complete released Mango scene produce a changing sequence,
and what artifacts remain relative to the source-camera images?
Checkpoint: [Mango-GS release](https://huggingface.co/htx0601/Mango-GS/tree/main/n3v/sear_steak_mango_node),
stored at `.local/weights/mango/n3v/sear_steak_mango_node/`.
The original remote download revision was not established for this earlier
download; evaluated file hashes, not an assumed current `main`, identify it:

| Component | Bytes | SHA-256 |
| --- | --- | --- |
| `point_cloud.ply` | 129,123,699 | `b89b5d2d533bbb67e031b72aac31779524a13d601f1ae2cf662dda8d673d1c14` |
| `deform.pth` | 8,082,774 | `82709ff8d270a063f33093f189814cd48115cb2dbe1a1d4af0530e81532e70b3` |
| `cfg_args` | 711 | `b02bc9e2ec7c45e7c301f02f7551ee286d82f6da48d82fcb054d4c975de00f0f` |

Source commit, MIT source-license caveat, local
CUDA patch, PyTorch3D commit, compiler and standard-GIL environment are in the
[shared record](section6-evidence.md). Environment is
`.local/envs/mango-render/bin/python`; the package snapshot is
`evidence-inventory-20260905/mango-render-installed.txt`. The prior source builds
are documented in `pretrained-validation/mango-build-patched.log` and
`mango-knn-wheel.log`; `simple-knn` needs a normal wheel, not an editable install.

The existing input `.local/data/mango/n3v/sear_steak/` contains `poses_bounds.npy`
and 21 camera folders, each with 300 PNGs. It derives from the
[Neural 3D Video capture](https://github.com/facebookresearch/Neural_3D_Video);
archive SHA-256 is
`b53d9c444ab23d468f9d5da0dcbc5ab68cb70702bb03f9664cd686e9efebc525`.
Source cam00 video is 2704×2028, 300 frames at 30 FPS. No new input preparation
was performed. Upstream calibration/scaling conventions were retained.

The checkpoint was copied, preserving the original, into
`.local/runs/evidence-mango-assets-20260905/n3v/sear_steak_mango_node/`.
Exact command, environment and logs are in `.local/runs/evidence-mango-20260905/`.
It invokes upstream `render.py` with that model, the existing source data,
`--iteration -1 --deform_type mango_node --profile_config .../configs/profiles
--video_fps 30 --video_window_mode block --quiet --load2gpu_on_the_fly`.
Complete absolute argv are in `command.json`. Fresh runs need a new model-copy
directory because upstream writes outputs beneath the model path.

## Measurements

| Observation | Value | Boundaries |
| --- | --- | --- |
| Setup effort | Reused patched extensions, calibrated images and metric weights | Prior hours/download transfer not measured |
| Full command | 228.61 s | Imports/load, 300 renders, metrics, PNGs and video encoding |
| GPU memory | 10,170 MiB peak / approximately 1,148 MiB baseline | Device-wide 200 ms sampling |
| Model-copy/output directory | 913,595,733 bytes | Includes checkpoint copy, 300 renders, 300 GTs, 300 depths and MP4 |
| Inspection/log directory | 2,131,093 bytes | Snapshot with report sheets and analysis |
| Output video | 300 frames, 30 FPS, 1360×1024 | PNGs are 1352×1014; encoder pads dimensions |
| Quantized PNG PSNR vs loader reference | Mean 30.155 dB; frame range 29.672–30.399 | Independent RGB comparison, all 300 saved pairs |
| Repeatability | 300/300 render PNGs byte-identical | Compared with earlier `.local/runs/mango/` sequence |
| Isolated load / warm rendering throughput | Not measured in this run | `--quiet` suppresses upstream timing/metric prints |

The MP4 is under `test/video_release/renders/cam00/test_cam00.mp4` in the model
copy. Encoding is performed by the upstream command. The current loader selects
camera index 0 as its test camera; this does not independently establish the
released model's training split. PNG PSNR is not a reproduced paper result.

## Visual inspection

Compare [rendered frames](../../.local/runs/evidence-mango-20260905/contact.png)
with [their source-camera references](../../.local/runs/evidence-mango-20260905/ground-truth.png)
at frames 0, 150 and 299. Stirring and body pose progress coherently. Relative to
those references, the rendered head/shoulder and moving forearm are softer,
the dog is smeared, and blinds/shelf/peripheral edges have streaked or doubled
detail. This is a within-method paired observation, not a claim that Mango is
intrinsically worse than STG on matched data.

The blinds crop has mean adjacent RGB change 0.049 on the 0–255 scale; the full
frame averages 0.142. Background changes are small in this view, but these values
include real movement/lighting and do not measure perceptual flicker. The long
sequence's final pose differs substantially from its first, so a loop will reset
visibly. Transparency/disocclusion quality is not established by this fixed-camera
sequence. The stock run supplied no interactive orbit or custom camera sweep.
No portable splaTV export was produced. Reloading the complete checkpoint from
a fresh copy reproduced every PNG exactly.

## Decision

**Defer.** The renderer is usable and repeatable, but visible edge softness and
the larger runtime/dependency cost do not yet establish a benefit for the next
experiment. Revisit after a matched physical-time/camera evaluation or a targeted
off-view test; do not use unmatched STG/Mango clips to choose a training method.

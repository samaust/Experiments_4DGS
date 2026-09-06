# Experiment 008: MoE-GS

Status: **expert training integration unresolved for both scenes**.

Audited 2026-09-06: official checkout `.local/MoE-GS`, revision
`c98aa513e1d8ea06920a4395b841993ac678477c`. Its
[recovery guide](https://github.com/cvsp-lab/MoE-GS/blob/c98aa513e1d8ea06920a4395b841993ac678477c/THIRDPARTY_RECOVERY.md)
claims project backups are needed, but the actual checkout contains modified
`polynomial` model code and three-channel weight rasterizer sources. That guide
alone is not evidence that those components are unavailable. The checkout has
router trainers; its README marks expert training scripts as coming soon.
The exact training route for its modified SH-based STG expert remains unvalidated.
No expert or router training was launched; budget consumed: zero.

A follow-up local source audit found only the `train_E3.py`, `train_E3_tech.py`
and `train_E4.py` router entry points and their launch scripts, not a standalone
modified-STG expert trainer. README Stage 1 names Ex4DGS, E-D3DGS, 4DGaussians and
STG, explicitly requiring SH feature splatting with the Ex4DGS rasterizer for
STG. `train_E4.py` loads pretrained expert paths and steps all expert optimizers;
it is not merely a drop-in initializer for four untrained experts. The released
`thirdparty/polynomial/scene/oursfull.py:362` exposes a RAdam setup with spatial,
temporal, SH and routing-feature groups, but that model method does not supply
the missing standalone expert-training loop/configuration. The specific gate is
a validated released route or matching pretrained checkpoint for this modified
expert, not absent model or rasterizer source. Do not invent a replacement
training recipe and label it the released method.

Record all four expert implementations and the router separately. Validate the
modified appearance representation expected by the STG expert; original STG Full
is not a substitute. Planned limits are 25 minutes per expert and 20 minutes for
router training per scene.

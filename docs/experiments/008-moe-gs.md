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

Record all four expert implementations and the router separately. Validate the
modified appearance representation expected by the STG expert; original STG Full
is not a substitute. Planned limits are 25 minutes per expert and 20 minutes for
router training per scene.

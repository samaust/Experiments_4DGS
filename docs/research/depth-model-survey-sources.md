# Depth model survey: source reconnaissance

Status: **planning reconnaissance; full survey pending**. Sources checked on
2026-09-30 for [plan 068](../../plans/plan_068.md). This bounded check establishes
search entry points and a few paper leads. It contains no extracted performance
tables, ranking, license clearance, or claim of comprehensive coverage.

## Starting sources

Each linked source below supports the description of its own contents. Lists
and topic pages will supply search leads; performance and license conclusions
must come from the relevant paper, official implementation, and exact checkpoint
terms.

| Source URL | Scope observed | Proposed role in the search | Verified accessibility or coverage caveat |
|---|---|---|---|
| [Ideal-111/Awesome-Foundation-Model-Based-Depth](https://github.com/Ideal-111/Awesome-Foundation-Model-Based-Depth) | Foundation models for depth estimation and completion; discriminative and generative methods; dataset links. | Start recent model-family discovery and follow linked papers' comparison tables. | Accessible; includes entries labeled 2026. Completion and sparse-input methods require separate classification. |
| [scott89/awesome-depth](https://github.com/scott89/awesome-depth) | Supervised and self-supervised monocular depth, multi-view methods, completion, datasets, and related applications. | Recover older baselines named in newer papers. | Accessible; the visible bibliography contains work from 2014–2020. No current-coverage claim inferred. |
| [hitcslj/awesome-robust-depth-estimation](https://github.com/hitcslj/awesome-robust-depth-estimation) | Adverse weather, darkness, corruptions, multimodal inputs, zero-shot depth, and cross-camera/scene methods. | Find robustness papers and benchmark leads alongside standard accuracy tables. | Accessible; Survey, Talks, and Implementations contain TODO placeholders. Some methods use inputs beyond RGB. |
| [choyingw/Awesome-Monocular-Depth](https://github.com/choyingw/Awesome-Monocular-Depth) | Monocular methods focused on work after 2020, including metric depth and high-resolution methods. | Find image-depth and detail-preserving alternatives. | Accessible; README explicitly states its last update was October 2024. |
| [AndyLiming/awesome-depth](https://github.com/AndyLiming/awesome-depth) | Linked categories for monocular, stereo, multi-view, video, omnidirectional depth, completion, fusion, and calibration. | Check whether an omitted family belongs in the main comparison or an adjacent-method appendix. | Accessible; the landing README is an index, so each linked category needs follow-up. |
| [GitHub topic: depth-prediction](https://github.com/topics/depth-prediction) | Tagged repositories including estimators, reconstruction resources, and parallax-video applications. | Discover implementations and aliases missed by paper lists. | Accessible; visible results mix original models, applications, and lists. |
| [GitHub topic: depth-estimation](https://github.com/topics/depth-estimation) | Tagged depth estimators and broader geometry/SLAM projects. | Discover current implementations and possible multi-view alternatives. | Accessible; visible results include full pipelines such as pySLAM as well as model repositories. |
| [GitHub topic: monocular-depth-estimation](https://github.com/topics/monocular-depth-estimation) | Tagged repositories including Depth Anything, MiDaS, Marigold, MoGe, and ZoeDepth. | Cross-check image-depth families and find official project links. | Accessible; only the displayed page was inspected, not all topic pagination. |
| [arXiv](https://arxiv.org/) | Searchable scholarly archive with computer-science subject browsing. | Locate original papers, dated versions, references, and comparison tables. | Accessible; arXiv explicitly states that it does not peer-review posted material. Record publication status separately. |
| [Hugging Face](https://huggingface.co/) and [depth-estimation model filter](https://huggingface.co/models?pipeline_tag=depth-estimation) | Model hosting and a depth-estimation task filter. | Find released checkpoint variants, model cards, and model-license documents. | Both pages accessible; this check did not verify the identity, completeness, or license of each listed checkpoint. |

## Initial search leads

These examples span several methods and input types. They are starting papers,
not a shortlist of winners. Original-paper abstracts were checked for the
descriptions below; numerical comparisons and release/license verification
remain work for the full survey.

| Lead | Why inspect its comparison tables | Discovery route and verified primary source |
|---|---|---|
| **MoGe / MoGe-2** | Single-image geometry with separate relative-geometry and metric-scale questions. MoGe-2 predicts a metric point map and builds on MoGe's affine-invariant representation. | Foundation-model list above; [Wang et al., MoGe-2, arXiv:2507.02546v1](https://arxiv.org/abs/2507.02546v1). |
| **Marigold** | A diffusion-model family for monocular depth and other dense prediction tasks; inspect both the original depth paper and later version. | Foundation-model list and monocular topic above; [Ke et al., journal-extension manuscript, arXiv:2505.09358v1](https://arxiv.org/abs/2505.09358v1). |
| **DepthCrafter** | Video depth using a video diffusion model; useful lead for temporal comparison protocols and long-sequence behavior. | Foundation-model list above; [Hu et al., arXiv:2409.02095v2](https://arxiv.org/abs/2409.02095v2). |
| **ZoeDepth** | Single-image metric depth with multiple training configurations; useful for tracing older baselines and distinguishing relative pretraining from metric fine-tuning. | Foundation-model list and monocular topic above; [Bhat et al., arXiv:2302.12288v1](https://arxiv.org/abs/2302.12288v1). |
| **PatchFusion** | High-resolution depth refinement using a base depth estimator; its base model and refinement must be recorded together. | choyingw list above; [Li et al., arXiv:2312.02284v1](https://arxiv.org/abs/2312.02284v1). |
| **VGGT** | Joint geometry prediction from one or several views; inspect as a separate input regime when considering multi-view alternatives. | Foundation-model list above; [Wang et al., arXiv:2503.11651v1](https://arxiv.org/abs/2503.11651v1). |

## Proposed rules for extracting comparisons

These are proposed survey rules, to be applied when the full papers are read:

1. Keep each result attached to its paper version, table number, row/checkpoint,
   dataset split, metric definition, and evaluation protocol. Check table
   footnotes and supplements before comparing rows.
2. Record metric depth versus relative depth; scale-only versus scale-and-shift
   alignment; depth versus disparity alignment; per-image versus sequence-wide
   alignment; crop, valid-pixel mask, depth range, and test resolution. Separate
   incompatible protocols rather than produce one overall score.
3. Record inputs: single RGB image, video frames, multiple views, intrinsics,
   poses, or sparse depth. Separate zero-shot evaluation from dataset-specific
   fine-tuning and mark unknown training/test overlap.
4. Distinguish results copied from an older paper from baselines rerun by the
   paper's authors. Record conflicting reported numbers instead of choosing the
   favorable one. Missing results mean unknown, not zero or failure.
5. Treat runtime and memory as comparable only when hardware, resolution, batch
   size, precision, number of frames, and inference steps are sufficiently
   specified. Record whether preprocessing and refinement are included.
6. Check code and exact checkpoint availability and licensing independently.
   A list repository's license or a paper's publication license is not evidence
   of the model weights' license. Preserve unresolved commercial/output-use
   questions explicitly.

The full survey should expand these leads by following comparison-table rows
and references, then search newer papers for each family. It should report
coverage gaps and conflicting evidence, with performance findings limited to
the protocols actually documented by the papers.

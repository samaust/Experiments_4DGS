# Plan 068 — Survey depth estimation models and published comparisons

Prepared 2026-09-30. Status: plan prepared; source reconnaissance complete;
full literature survey and report pending.

## Objective

Find depth estimation models beyond the current D0–D4 candidates and explain
what is available, how models compare in research-paper tables, and which merit
future evaluation in this project's 4DGS workflow. Produce a compact report with
traceable supporting data. Prioritize evidence about quality, practical use and
commercial permission; record uncertainty when the sources do not settle it.

This is a literature and release survey. Its work consists of searching,
reading, extracting evidence and writing. Model installation, inference,
training and GPU benchmarking belong to a subsequent experiment plan.

## Scope and reference points

Use [the workflow](../README.md) and the existing
[depth/license audit](../docs/research/vipe-alternatives.md) to establish context:
calibrated multi-camera Basketball footage, 960×540 images, moving players,
occlusions, depth boundaries and a need for physical scale. Distinguish the
current monocular scale-estimation role from potential future dense geometry
or video-depth roles; good depth benchmark results alone do not establish
better final 4DGS renders.

Keep these references in the comparison: D0 historical ViPE/UniDepth, D1
standalone UniDepth V2-L, D2 DA3METRIC-LARGE, D3 Metric3Dv2 ViT-L and D4 Depth Pro.
D0/D1 are separate implementation controls, not two independent model families.
Use exact variants: a result for another backbone or checkpoint is a separate row.

| Search category | Relevance to investigate |
| --- | --- |
| Monocular metric depth | Absolute scale, known or predicted intrinsics, generalization to unseen scenes. |
| Monocular relative depth, including diffusion methods | Detail and depth ordering; what additional information would be needed to recover metric scale. |
| Video depth | Temporal stability, dynamic objects, clip length and consistency of scale across frames. |
| Multi-view / geometric foundation models | Depth from multiple views, required camera inputs and assumptions about scene motion. |
| Efficient and high-resolution variants | Compute, memory, boundary detail and practical processing of many camera frames. |

Record stereo-only, sparse-depth-assisted and other sensor-dependent methods
when encountered, with their extra inputs. Keep them in a separate category
unless they offer an applicable RGB route. Include research-only and unreleased
models in the inventory with clear availability labels; commercial terms affect
the practical shortlist rather than hiding relevant research.

## 1. Establish the search record

Freeze the survey cutoff at **2026-09-30**. Record access dates and exact paper
versions; use versions available by the cutoff. Search recent work and follow
older baselines cited in comparison tables. Record publication/first-release
dates separately from later repository or model updates.

Start with all user-provided discovery sources:

| Source | Search use |
| --- | --- |
| [arXiv](https://arxiv.org/) | Papers, version history, references, main and supplementary evaluation tables. |
| [GitHub](https://github.com/) | Author repositories, release links, evaluation code and licenses. |
| [Hugging Face](https://huggingface.co/) | Author model cards, exact weight variants, release/access conditions and licenses. |
| [Foundation-model depth list](https://github.com/Ideal-111/Awesome-Foundation-Model-Based-Depth) | Foundation-model and generative-method leads. |
| [scott89/awesome-depth](https://github.com/scott89/awesome-depth) | Earlier methods and baseline leads. |
| [Robust-depth list](https://github.com/hitcslj/awesome-robust-depth-estimation) | Robustness and generalization leads. |
| [Awesome-Monocular-Depth](https://github.com/choyingw/Awesome-Monocular-Depth) | Monocular method families and benchmarks. |
| [AndyLiming/awesome-depth](https://github.com/AndyLiming/awesome-depth) | Additional papers and repositories. |
| [depth-prediction topic](https://github.com/topics/depth-prediction) | Additional repositories and release leads. |
| [depth-estimation topic](https://github.com/topics/depth-estimation) | Broad model and implementation discovery. |
| [monocular-depth-estimation topic](https://github.com/topics/monocular-depth-estimation) | Monocular model and implementation discovery. |

The [source reconnaissance](../docs/research/depth-model-survey-sources.md)
records accessibility, observed coverage and initial leads. Treat lists, topic
pages, stars and downloads as discovery aids. Verify performance in papers and
release/license claims in author-controlled sources.

Search combinations of “monocular metric depth”, “zero-shot depth estimation”,
“relative depth”, “diffusion depth”, “video depth temporal consistency”,
“multi-view depth dynamic scenes”, “depth boundary evaluation” and
“depth estimation benchmark comparison”. Log query, source, date, screened
results and inclusion/exclusion reason; deduplicate mirrors and renamed models.

## 2. Expand through paper comparison tables

Start from the papers for
[UniDepthV2](https://arxiv.org/abs/2502.20110),
[Depth Anything 3](https://arxiv.org/abs/2511.10647),
[Metric3Dv2](https://arxiv.org/abs/2404.15506) and
[Depth Pro](https://arxiv.org/abs/2410.02073), then add seed papers from the other
search categories. Resolve and record their precise versions before extraction.

For each relevant main or supplementary comparison table:

1. List the compared model names and exact variants, including older baselines.
2. Follow citations to each model's original paper, official code and weights.
3. Add new relevant families to the inventory and inspect their comparison tables.
4. Search for later papers or independent benchmark papers that evaluate these
   families, capturing disagreements and regressions as well as claimed gains.

Perform an initial discovery pass and two rounds of this citation expansion.
Deep-read models with relevant comparative evidence or a distinct useful
capability. If a category or leading candidate still has a material evidence
gap, do a targeted final pass and document any unresolved gap. State the number
of sources, papers and variants screened; describe the result as a dated survey,
without claiming every available model was found.

## 3. Extract comparable evidence

Save one benchmark observation per model variant, protocol and metric. Every
numeric entry needs the paper URL/version, table and page or section, row,
relevant footnotes, and the party reporting the result. Visually check PDF tables
when text extraction loses headers, symbols or alignment. Record whether a
baseline was rerun by the paper's authors or copied from earlier work.

| Evidence field | What to capture |
| --- | --- |
| Model identity | Family, version, backbone, checkpoint, parameter count, released versus paper-only model. |
| Evaluation data | Dataset/version, split, domain, training overlap where disclosed, zero-shot versus fine-tuned setting. |
| Inputs | Single image, video or multiple views; RGB, sparse depth, poses and supplied/predicted intrinsics. |
| Depth meaning | Metric or relative; camera-z depth, ray distance, disparity or inverse depth. |
| Preprocessing and protocol | Input/evaluation resolution, crop, valid mask, depth range/cap, resizing, scale or scale-and-shift alignment and its scope. |
| Accuracy | Reported AbsRel, RMSE, log error, delta thresholds or other metrics, with definitions, units and better direction. |
| Detail and motion | Published boundary, robustness and temporal metrics; qualitative observations clearly identified as such. |
| Compute | Reported hardware, latency/throughput, peak memory, precision, batch size, image/clip size, sampling steps and ensembling. Missing values stay unknown. |

Build separate comparison tables for unaligned metric depth, aligned relative
depth, video/temporal performance, multi-view geometry and efficiency. Within
each, group by compatible dataset and protocol. Two rows appearing in the same
paper are not sufficient proof of identical evaluation conditions: read the
caption, footnotes and evaluation section.

Preserve conflicting reported values with their respective sources. Avoid
merging different splits, crops, caps, intrinsics access, alignment rules or
training regimes into one ranking. Per-image ground-truth scaling cannot prove
absolute metric accuracy. Treat unspecified protocol details as a comparison
limitation. Do not average unrelated metrics into an overall score or infer
speed/VRAM on this host from a different reported setup.

## 4. Verify availability and commercial terms

For each serious candidate, inspect the official repository and exact weight
release. Record paper/code/model links, revision identifiers, release status,
access gating, environment requirements, supported inputs/outputs and any
disclosed difference between the paper model and released checkpoint.

Answer the user's four licensing questions separately:

- Does the weight license permit commercial use?
- Does the code license permit commercial use?
- What do the terms say about commercial inference and use of generated outputs?
- Is a commercial license or negotiation explicitly offered, and through which
  published contact or process?

Cite actual license text and author statements. Distinguish permission,
restriction and uncertainty; an absent weight license is unresolved. Do not
transfer a code license to weights, an arXiv publication license to a model,
or a noncommercial weight restriction automatically to all output copyrights.
Mention material dependency restrictions where documented. A generic contact
address is not evidence that commercial licensing is offered. Record contacts
without contacting authors as part of this survey.

## 5. Synthesize for the project

Explain where models perform well or poorly across comparable published
benchmarks, how consistent the evidence is across papers, and what remains
unknown for Basketball footage. Consider scale fidelity, unseen indoor scenes,
depth boundaries, moving people, occlusion, temporal consistency, known camera
intrinsics, compute and license terms. A missing temporal evaluation remains
unknown rather than becoming an assumed strength or weakness.

Produce evidence-backed shortlists for: metric scale estimation; depth detail;
video consistency; and commercially usable candidates. Allow ties and empty
categories when evidence is insufficient. Keep published measurements, author
claims and project-specific inferences visibly distinct. Recommend a small next
evaluation set with one concrete reason and one unresolved question per model.
Existing D0–D4 results and human preferences remain separate local evidence;
this survey does not change their experiment identities or selection records.

## 6. Write and verify the report

Write **`docs/research/depth-model-survey.md`** with:

1. A compact overview of the strongest findings and practical candidates.
2. An availability table, one row per relevant model variant.
3. Performance tables grouped by compatible evaluation protocol, with citations.
4. Code, weight, output-use and commercial-negotiation licensing columns.
5. Project fit, tradeoffs, unresolved questions and recommended future tests.
6. Search method, cutoff, coverage, exclusions and source references.

Keep the main report readable; store the detailed evidence under
**`docs/research/depth-model-survey-data/`** as `search-log.csv`, `models.csv`,
`benchmarks.csv` and `licenses.csv`. Use stable model/protocol/source identifiers
and document column meanings, metric directions and missing-value conventions
in that directory's README. Keep comparative tables as selected factual results
with citations, rather than reproducing full papers or substantial prose.

Verify every shortlisted candidate's identity, release links and licenses.
Recheck every reported numeric value against its source, and every ranking
against its protocol group. Review contradictions, missing evidence and the
boundary between paper results and project predictions. Check links, CSV
consistency and Markdown tables, then commit the completed report and supporting
data as a task-related milestone.

## Completion criteria

- Every specified discovery source was searched or has a documented access issue.
- The inventory distinguishes model families, variants, wrappers and availability.
- The survey extends beyond D0–D4 and covers all five search categories, including
  explicit exclusions or missing evidence where applicable.
- Numerical comparisons trace to exact paper tables and compatible protocols.
- Each shortlisted candidate has separate code, weight, output-use and commercial
  licensing dispositions supported by sources or explicitly marked unresolved.
- The report gives useful next-test candidates without presenting published
  benchmark scores as measured improvements to this project's final renders.

The present planning milestone delivers this plan and the source reconnaissance.
The report and its evidence files are the subsequent survey deliverables.

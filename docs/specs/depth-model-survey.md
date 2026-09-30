# Survey depth estimation models and compare published evidence

## Problem Statement

The project currently compares D0–D4, but the user needs a broader view of depth
estimation models before choosing further experiments. Relevant alternatives
are scattered across papers, repositories, model hubs and community lists.
Research-paper comparison tables can reveal both additional candidates and
their reported strengths, but differing datasets, alignment rules, inputs and
model variants can make an apparent ranking misleading.

The user also needs to know what is actually released and whether its code,
weights and resulting outputs can be used commercially. A repository license
alone does not answer all of these questions. The desired result is a concise,
well-supported report that explains the available choices and their relevance
to the Basketball/4DGS workflow.

## Solution

Conduct a dated literature and release survey using arXiv, GitHub, Hugging Face,
the supplied community lists and GitHub topics. Expand discovery by following
model names and citations in research-paper comparison tables. Trace results
to exact papers and variants, and compare scores only under compatible
evaluation settings.

Deliver a compact report containing a model inventory, comparable performance
tables, availability and commercial-use findings, project tradeoffs and a
small set of candidates for future testing. Preserve detailed search and
evidence records so a reader can verify every numerical comparison and
shortlist decision. Include D0–D4 as references while extending discovery to
metric, relative, video, multi-view, efficient and high-resolution methods.

## User Stories

1. As a project researcher, I want a survey beyond D0–D4, so that I can consider alternatives missing from the current experiments.
2. As a project researcher, I want all supplied repositories and topics searched, so that the discovery process uses the starting points I identified.
3. As a project researcher, I want arXiv, GitHub and Hugging Face searched together, so that papers, implementations and released weights can be connected.
4. As a project researcher, I want model names in paper comparison tables followed to their original papers, so that the survey expands beyond an initial list of familiar models.
5. As a project researcher, I want later and independent evaluations considered, so that conclusions do not rely solely on a model author's selected results.
6. As a report reader, I want a stated cutoff and exact paper versions, so that I understand the date and scope of the evidence.
7. As a report reader, I want search coverage, exclusions and unresolved gaps recorded, so that I can judge how broad the survey is.
8. As a project researcher, I want older baselines retained where they help explain newer comparisons, so that model improvements have useful reference points.
9. As a report reader, I want model families, versions, backbones and checkpoints distinguished, so that I do not attribute one variant's result to another.
10. As a report reader, I want D0 and D1 identified as implementation controls for the same model family, so that the inventory does not inflate the number of independent alternatives.
11. As a developer, I want official code and exact weight releases identified, so that I can determine which candidates could actually be evaluated.
12. As a developer, I want paper-only, gated, incomplete and released candidates labeled, so that reported performance is not mistaken for present availability.
13. As a developer, I want disclosed differences between paper models and released checkpoints recorded, so that I can assess whether published results apply to usable artifacts.
14. As a project researcher, I want metric and relative depth separated, so that depth ordering or aligned accuracy is not confused with recovery of physical scale.
15. As a project researcher, I want single-image, video and multi-view inputs distinguished, so that methods are compared with their required information visible.
16. As a developer, I want requirements for intrinsics, camera poses, stereo pairs or sparse depth recorded, so that I can assess fit with the existing RGB and calibrated-camera workflow.
17. As a report reader, I want each score tied to its paper, table, row and evaluation settings, so that I can verify the comparison directly.
18. As a project researcher, I want dataset splits, crops, depth ranges, resolutions and alignment rules recorded, so that incompatible scores are not combined into a ranking.
19. As a project researcher, I want zero-shot and fine-tuned evaluations distinguished, so that generalization claims can be assessed against the training conditions.
20. As a project researcher, I want disclosed training/test overlap recorded, so that strong results on familiar data are not assumed to transfer to unseen scenes.
21. As a report reader, I want copied baseline scores distinguished from rerun evaluations, so that I know who produced each result and under which conditions.
22. As a report reader, I want conflicting reported values preserved with their sources, so that disagreements remain visible.
23. As a project researcher, I want accuracy, boundary detail, robustness and temporal evidence considered where available, so that model selection reflects more than one quality dimension.
24. As a developer, I want runtime and memory claims accompanied by hardware and inference settings, so that I can judge their practical relevance without assuming performance on this host.
25. As a commercial evaluator, I want code licensing checked independently, so that I know whether the implementation permits commercial use.
26. As a commercial evaluator, I want exact weight licensing checked independently, so that a permissive code license is not mistaken for permission to use the model commercially.
27. As a commercial evaluator, I want commercial inference and generated-output terms explained separately, so that restrictions are neither overlooked nor automatically transferred to every output.
28. As a commercial evaluator, I want explicit commercial licensing offers and published contacts recorded, so that I can identify a possible path for otherwise restricted candidates.
29. As a commercial evaluator, I want missing or ambiguous license evidence marked unresolved, so that uncertainty is not presented as permission or prohibition.
30. As a developer, I want material dependency restrictions noted where documented, so that top-level licensing does not conceal practical obligations.
31. As a project researcher, I want conclusions related to physical scale, moving players, occlusions, depth boundaries and known cameras, so that the report supports this project's needs.
32. As a report reader, I want published measurements, author claims and project-specific inferences distinguished, so that I can assess the strength of each conclusion.
33. As a project researcher, I want separate shortlists for metric scale, detail, video consistency and commercial use, so that different needs do not disappear into one overall score.
34. As a project researcher, I want each proposed future test to have a reason and an unresolved question, so that subsequent experiments can resolve a concrete uncertainty.
35. As a report reader, I want a compact summary backed by structured evidence records, so that I can scan the findings and inspect the details when needed.
36. As a project researcher, I want ties and insufficient evidence reported honestly, so that the survey can remain useful without inventing a winner.
37. As a project owner, I want this literature survey distinguished from local measurements and human preferences, so that paper results do not overwrite the conclusions of existing experiments.

## Implementation Decisions

- **Work product:** produce a Markdown research report plus structured CSV evidence inventories for searches, model variants, benchmark observations and license findings. Document identifiers, fields, units, metric directions and missing-value conventions. These form one report package for review.
- **Research cutoff:** use 2026-09-30. Record access dates, publication and release dates, and exact paper/model/source revisions. Use versions available by the cutoff; document unavailable historical evidence rather than substituting an undated claim.
- **Reference candidates:** retain D0 historical ViPE/UniDepth, D1 standalone UniDepth V2-L, D2 DA3METRIC-LARGE, D3 Metric3Dv2 ViT-L and D4 Depth Pro. Treat D0/D1 as separate implementation controls within the same family.
- **Coverage:** search monocular metric depth, monocular relative depth including diffusion approaches, video depth, multi-view/geometric foundation models, and efficient/high-resolution variants. Record stereo, sparse-depth and other sensor-dependent methods separately unless they provide an applicable RGB route. Preserve research-only and unreleased candidates in the inventory with clear dispositions.
- **Discovery method:** use all supplied sources, an initial discovery pass and two rounds of following comparison-table rows and references. Search for later or independent evaluations. Perform a targeted final pass for a material category or candidate gap, then document unresolved gaps and screened-source counts.
- **Source authority:** use lists, topic pages, stars and downloads for discovery. Use original papers for reported evaluations and author-controlled repositories, model cards and license documents for release and licensing facts. Deduplicate wrappers, mirrors and renamed releases.
- **Benchmark record:** retain model-variant identity, dataset/version/split, evaluation protocol, metric/value/unit/direction, paper/version/table/page-or-section/row, footnotes, reporting party, and copied-versus-rerun status. Keep conflicting observations as separate source-attributed records.
- **Protocol record:** include input regime, supplied versus predicted intrinsics/poses, output meaning, image/evaluation resolution, crop, valid mask, depth limits, scaling/alignment method and scope, training regime and disclosed overlap. Distinguish camera-z depth, ray distance, inverse depth and disparity where relevant.
- **Comparison groups:** organize metric, aligned relative, temporal, multi-view and efficiency tables by compatible evaluation settings. Read captions, footnotes and evaluation sections before ranking rows, even within one paper. Unknown settings limit comparison. Per-image ground-truth scale alignment does not establish absolute metric accuracy.
- **Quality and compute:** extract reported accuracy, detail, robustness and temporal metrics with definitions. Record runtime hardware, memory, precision, batch/resolution/clip size, inference steps, refinement and ensembling when available. Qualitative observations and unspecified quantities remain labeled as such.
- **Availability:** identify official papers, implementations, checkpoints, access gates, environment requirements, supported inputs/outputs and any discrepancy between a released artifact and the evaluated paper model. Each materially different variant has its own disposition.
- **Commercial findings:** answer code use, weight use, commercial inference/output use, and explicit commercial licensing offers separately. Cite governing text; distinguish allowed, restricted and unresolved. Record a commercial contact only with the scope of the author's actual statement. Note documented material dependency terms.
- **Project synthesis:** assess scale fidelity, unseen indoor scenes, depth boundaries, moving people, occlusion, temporal consistency, calibrated inputs, compute and license constraints. Use existing workflow information as context; retain local measured results and human preferences as distinct evidence.
- **Recommendations:** produce small, justified shortlists for metric scale, depth detail, video consistency and commercial use. Give each recommended future evaluation a concrete reason and unresolved question. Allow ties or an empty shortlist when evidence is insufficient; do not manufacture an overall score across incompatible tasks.
- **Presentation:** keep the main report compact with an overview, inventory, grouped performance tables, licensing findings, project tradeoffs, next-test candidates, coverage and references. Detailed evidence belongs in the supporting records. Every numerical conclusion and licensing disposition must be traceable to an authoritative source or explicitly unresolved.

## Testing Decisions

- **Confirmed review boundary:** the user selected “Use report and source checks.” Review the completed report and its supporting evidence as one externally visible deliverable. Reuse the project's research-report and source-audit conventions; a new executable validation subsystem is not required.
- **What makes a good check:** a reader can trace a finding to the exact source, reproduce the stated comparison from compatible rows, and understand its limits. Check substantive behavior of the report: accurate facts, valid comparisons, complete requested coverage and justified recommendations. Avoid checks tied to prose layout or internal writing steps.
- **Components reviewed:** the report, search inventory, model inventory, benchmark observations and license findings. Their identifiers and citations must agree, and referenced records must exist.
- **Prior art:** the project's ViPE alternatives study already distinguishes exact model variants, native input/output conventions, code and weight permissions, and missing evidence. Its citation and license-audit approach, together with Plan 068's source reconnaissance, supplies the existing review pattern.
- **Discovery coverage:** confirm every supplied source was searched or has a documented access issue; inspect inclusion/exclusion reasons, duplicate handling, the two citation-expansion rounds, and coverage of every declared category. Confirm the inventory extends beyond D0–D4.
- **Numeric accuracy:** recheck every reported number against its exact source table, including headers, footnotes, units, better direction and variant identity. Inspect rendered PDF tables when text extraction is ambiguous. Verify that every ranking uses a compatible protocol group.
- **Adverse evidence cases:** check that incompatible alignment/crop/split/input settings are not merged, copied results are identified, contradictory numbers retain both sources, unreleased variants are not marked available, and missing runtime or quality results remain unknown.
- **Commercial findings:** recheck every shortlisted candidate's exact code and weight terms and any output-use or negotiation claim. Missing licenses must remain unresolved; a repository license, paper license or generic email address must not be promoted into an unsupported permission or commercial offer.
- **Synthesis:** verify that shortlist reasons follow from cited evidence, that missing temporal or Basketball-specific evidence is visible, and that published benchmark results are not described as locally measured render improvements.
- **Document integrity:** check Markdown tables, links, CSV readability, documented missing-value conventions and identifier consistency using ordinary document/data checks. Include a concise verification record with any remaining evidence limitations.
- **Acceptance:** the report and evidence package are complete when all source and category dispositions are present, numerical comparisons are traceable and compatible, shortlisted candidates have all four licensing dispositions, and the practical recommendations state their uncertainties. An unresolved upstream fact can be a documented finding; it must not become an unsupported positive claim.

## Out of Scope

- Installing models, downloading weights, running inference, training or performing GPU benchmarks.
- Implementing depth adapters, changing calibration or geometry contracts, adding experiment arms, or allocating runtime attempts.
- Creating an external annotation bundle, obtaining new human visual reviews, or generating final renders.
- Replacing or retroactively changing existing D0–D4 results, selection records, model pins, historical evidence or experiment issue acceptance criteria.
- Contacting authors, negotiating licenses, obtaining legal clearance, or treating a permissive top-level license as a complete dependency audit.
- A universal ranking across incompatible protocols, claims of exhaustive coverage of every model, or performance estimates for this host without measurements.
- A reusable automated evidence-checking product; the user confirmed report and source review for this research task.

## Further Notes

This specification implements the research deliverable described by **Plan 068**,
prepared on 2026-09-30 and committed locally as `70a67fc7`. The plan and initial
source reconnaissance are complete; the full literature survey, extracted
comparisons and report remain pending. The user confirmed the review boundary
before publication of this specification.

The existing workflow uses calibrated multi-camera Basketball images at 960×540.
Current monocular depth supports physical-scale estimation; potential future
dense-depth or video-depth uses should be evaluated as separate roles. Existing
scale-input provenance and historical preservation decisions continue to apply
to any later implementation, which is outside this survey.

This is a standalone research follow-up. It can proceed independently of the
existing experiment execution and qualitative-review issues. Publishing this
specification marks the survey ready for agent work; it does not mark the
research report complete.

Required discovery sources:

- [arXiv](https://arxiv.org/)
- [GitHub](https://github.com/)
- [Hugging Face](https://huggingface.co/)
- [Ideal-111/Awesome-Foundation-Model-Based-Depth](https://github.com/Ideal-111/Awesome-Foundation-Model-Based-Depth)
- [scott89/awesome-depth](https://github.com/scott89/awesome-depth)
- [hitcslj/awesome-robust-depth-estimation](https://github.com/hitcslj/awesome-robust-depth-estimation)
- [choyingw/Awesome-Monocular-Depth](https://github.com/choyingw/Awesome-Monocular-Depth)
- [AndyLiming/awesome-depth](https://github.com/AndyLiming/awesome-depth)
- [GitHub topic: depth-prediction](https://github.com/topics/depth-prediction)
- [GitHub topic: depth-estimation](https://github.com/topics/depth-estimation)
- [GitHub topic: monocular-depth-estimation](https://github.com/topics/monocular-depth-estimation)

Initial paper leads supplement the existing D0–D4 references: MoGe-2, Marigold,
DepthCrafter, ZoeDepth, PatchFusion and VGGT. These are discovery leads rather
than predetermined winners; the survey must follow and verify the underlying
comparison evidence.

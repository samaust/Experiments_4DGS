# Survey verification and reconciliation

Cutoff/access date: **2026-09-30**. Scope: Plan 068, issues #36–#43.
Review boundary: completed report, evidence records and primary sources, as
confirmed by the user. This is a documentation/research deliverable; model and
application test suites are not evidence of its factual correctness.

## Coverage and counts

The package contains six independently researched sections and four consolidated
CSV views. The section search logs contain **141 inspection steps referencing
134 distinct URL entries** after splitting semicolon-separated source fields.
URL entries are not unique papers: versions, repositories, cards and discovery
pages are included, and a logged search may screen multiple leads.

| Issue | Search steps | Numerical observations | License records |
| --- | ---: | ---: | ---: |
| #37 references/discovery | 22 | 59 | 5 |
| #38 metric | 21 | 59 | 21 |
| #39 relative/diffusion | 16 | 44 | 12 |
| #40 video | 25 | 48 | 27 |
| #41 multi-view | 36 | 45 | 24 |
| #42 efficiency/detail | 21 | 39 | 21 |
| **Total** | **141** | **294** | **110** |

Model rows include exact releases, input modes, paper-only comparison identities
and screened leads; they are not a count of independent model families. After
review corrections, there are **166 model/disposition rows and 63 identity links**.

All eleven supplied discovery entry points have substantive screens in #37:
arXiv, GitHub, Hugging Face, five community lists and three topics. Each category
records two table/reference expansion rounds, later/independent evaluation and
a targeted final pass. Logs preserve source-specific stage labels (`0`/initial,
`1`/expansion-1 and `2`/expansion-2 have the corresponding meanings). Search,
release and protocol checks are distinguished; none implies exhaustive pagination.

## Identity and observation reconciliation

`identity-links.csv` records wrappers, repeated releases, input modes, derivations,
refreshes and the disposition of every #37 cross-category inventory lead.
In particular:

- D0/D1 share UniDepth V2-L weights, while the historical wrapper remains a
  separate control without a fabricated paper score.
- DA V2 Small in #39/#42 is one exact release. Its Hypersim metric fine-tune and
  Large-hf conversion are separate artifacts. MoGe-3's #42 entry routes to #38.
- MoGe supplied/predicted FoV and UniDAC supplied/predicted cameras are different
  input conditions. MetricAnything PointMap and aerial MoGe adaptations are
  derived models, not independently invented architectures.
- Unspecified paper baselines do not inherit exact project or current-release
  identities. The review specifically corrected the #37 MoGe evaluator's
  UniDepth/Metric3D rows and #41 DA3 evaluator's MapAnything rows.
- DA3-1.1, MapAnything refreshes/Apache weights, VGGT Commercial, Pi3X and
  VGGT-Ω's reproduction release retain separate score/license dispositions.
- PatchFusion patch-count modes share an artifact; PRV2's matched-pretraining
  baselines do not inherit original PatchFusion results.

The source-observation duplicate check compares model equivalence, exact paper
version, table/row, dataset, metric and value. Repeated release records do not
create repeated experiments. Same-paper baselines copied elsewhere remain
attributed to their reporting source and are not counted as independent repeats.
No scores or conflicting values were averaged or silently dropped.

Material disagreements retained with separate source records:

| Evidence | Treatment |
| --- | --- |
| MoGe-2 original versus MoGe-3 evaluator's metric scores | Separate evaluator/protocol records; changed baseline preprocessing/checkpoint unresolved. |
| Marigold original DIODE versus later copied baseline | Preserve both; later masks/log fitting explain possible differences but do not prove full reconciliation. |
| UniDepthV2 SSI wording versus metric table labels | Alignment-unresolved group; no unaligned metric ranking. |
| DA3 DIODE Metric3Dv2 unusual delta1 | Visually confirmed source value, excluded from conclusions. |
| VDA versus independent E3D ranking | Separate frame selection, alignment and unknown checkpoint settings. |
| Apple, DA3-Large-1.1, Pi3, PRO, GenPercept license conflicts | Explicit asset-specific restrictions or unresolved disposition; no blanket commercial grant. |
| RollingDepth license template; derivative SVD/FLUX/base terms | Preserve incomplete grant and lineage qualifications. |

Screened-only leads such as FE2E, md4all, NVDS, HyDen, YOLO26, OptiGeo and
WorldMirror 2.0 have bounded dispositions rather than an implied completed deep
audit. Stereo, sparse-depth and sensor-assisted variants do not silently join
RGB-only comparisons. Remaining deployment or upstream questions are findings,
not hidden implementation tasks in this literature survey.

## Checks performed

Each section records its full numerical recheck against exact source tables,
headers, units and inference conditions. PDF tables were visually inspected
where extraction was ambiguous. Release/license review used official code,
author cards and actual license text; no model weight contents were downloaded.

Integration checks cover standard CSV parsing, matching headers, nonempty
fields, unique scoped IDs, numerical values and metric directions, benchmark
and license foreign keys, identity-link endpoints, section/consolidated equality,
local Markdown links and whitespace. These are ordinary one-off checks, not a
new validation subsystem. Parent report tables were traced back to the records:
13 numeric groups and 46 local Markdown links passed integration checks. No
duplicate source observation remained after exact-release equivalence checking.

Independent Spec review additionally spot-checked MoGe-2 known/predicted-camera
values and alignment, DA3 DTU pose conditions, PRV2 timing exclusions, Marigold
V2 detail/runtime and log-alignment code, and Apple's selected weight restriction.
The integrating agent checked MoGe-3 C.1, DA V2 Table 3, PRV2 Table 1, MoGe-2
B.4 and DA3 Table 3, and retrieved fifteen pinned code-license/model-card texts
for the main permissive shortlist. Reusing section checks avoids claiming that
independent reviewers repeated every one of the 294 observations.

## Independent review

User-approved baseline: `35074547`. Section review compared survey paths through
`697da11c`; concurrent experiment commits were excluded. The final consolidated
report receives a separate integration review against the same baseline.

### Standards

Initial review found two issues: benchmark IDs overstated checkpoint identity
in #37/#41, and two #40 AbsRel locators named the MFC column. Corrections preserve
the scores, introduce comparison-only identities and fix the two locators.
No actionable code-smell judgement applied to this documentation-only change.
All initial findings were rechecked and resolved through `5c7783c7`. Final
integration review through `c06ccade`: **pass, no remaining findings**. The
reviewer independently confirmed consolidated equality, counts, joins, identity
links and the report's qualified conclusions.

### Spec

Initial review found no actionable missing, incorrect or out-of-scope requirement
in #37–#42. Explicit unknown upstream facts were accepted as qualified findings.
Final #43 integration review through `c06ccade`: **pass, no findings**. The
reviewer confirmed all required report sections, numerical/protocol traceability,
exact shortlisted releases and four license dimensions, reconciliation, coverage
and justified future-test questions. Metric VDA remains a separate hypothesis;
MapAnything-Apache does not inherit NC or unspecified-checkpoint measurements.

Both review axes are complete with zero remaining findings. All six prerequisite
issues were closed after their correction recheck, before final consolidation
acceptance. The parent can be assessed independently after #43 is closed; this
report does not authorize or execute its proposed future experiments.

## Limits

This is a dated, bounded survey. Some exact evaluation binaries, historical
release dates, crop/mask/cap details, training overlap, complete timing boundaries,
memory measurements, dependency grants and moving-player/occlusion behavior
remain unestablished. Shortlists explain the resulting uncertainty. No paper
score is represented as a local measurement, human preference or improved 4DGS
render. No GPU, training, inference, model installation or new annotation work
was performed.

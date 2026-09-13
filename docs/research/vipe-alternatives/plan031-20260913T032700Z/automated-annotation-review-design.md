# Automated annotation and review design

Recommendation for the explicitly resumed `plan031-20260913T032700Z` run:
replace the unavailable human annotation prerequisite with a separately
identified, candidate-blind **model-assisted reference**. Use a fixed CPU
Mask R-CNN teacher, then a fresh agent/script review of every selected image,
recording the exact subset visually inspected.
Keep missing or unreliable reference information explicit. Scores against this
reference measure model-assisted agreement; they do not establish human-verified
segmentation accuracy or physical truth.

This is a design recommendation, not evidence of executed annotation, downloaded
weights, successful inference, image review, or a passing criterion. It changes
no shared implementation files. The root agent has saved the user-directed
[annotation amendment](annotation-amendment-001.json) before affected execution;
this final recommendation incorporates it. Preserve the original plan,
protocol, authorization, stopped assessment and consumed preparation evidence.

## Basis and available resources

Read: [Plan 031](../../../../plans/plan_031.md),
[protocol](../benchmark-protocol.md), [saved status](status.md),
[saved assessment](assessment.md), [annotation state](annotations.json),
[accounting](matrix-accounting.json),
[annotation validator](../../../../scripts/vipe_benchmark/annotations.py),
[selection code](../../../../scripts/vipe_benchmark/selection.py), and relevant
metric/admission code. No `prompts` directory content was read.

The completed preparation contains 232 unique annotation images, 112 reference
camera/pair associations, and 768 fixed SIFT review locations. Its single attempt
consumed 97.46733420493547 seconds. Thus 57,502.53266579506 seconds remain in the
57,600-second CPU preparation/import/scoring/report scope at this checkpoint.
All 36 GPU attempts and seven environment builds are unconsumed but assigned to
specific candidate work. They are not spare teacher allocations.

The root agent verified that the existing `stg-colmap` environment supports
`MaskRCNN_ResNet50_FPN_V2_Weights.COCO_V1`. Read-only inspection of the installed
Torchvision source confirms the official weight URL, native resize defaults
800/1333, box NMS 0.5, and the native 100-detection-per-image cap. Root reports
that the approximately 177-MB teacher checkpoint is not cached. This review
did not import the model, download the checkpoint, run inference, or inspect
Basketball RGB. Exact runtime and asset qualification remain execution work.

## Primary reference generation

Use `maskrcnn_resnet50_fpn_v2` in the existing environment, float32 CPU inference,
evaluation mode, batch size one, seed zero, and the native input transform.
Freeze the exact checkpoint, source/runtime versions, preprocessing settings,
input order and output conversion before the first teacher prediction. The
installed weight URL is
`https://download.pytorch.org/models/maskrcnn_resnet50_fpn_v2_coco-73cbd019.pth`.
Record the downloaded file's full SHA-256 and actual byte count; the filename's
short digest is not a complete provenance record. Count the transfer against
the existing 60-GiB download ceiling and its files against the 150-GiB artifact
ceiling. No new environment build or package change is required by this design.

Run one forward pass on each of the 232 frozen unique RGB inputs. Retain native
`person` and `sports ball` outputs by the checkpoint's category mapping, record
the original labels, and map only the latter to benchmark `basketball`. Use
fixed detection-score and mask-probability thresholds of 0.5. Keep native box
NMS and detection capacity unchanged; disclose capacity saturation. Restore to
the original image grid through the model's native postprocessing, then enforce
the immutable valid footprint. Do not turn a detection box into a filled mask.

For overlapping retained masks, assign a pixel to greatest mask probability,
then greatest detection score, then lower native output index. Save the native
indices, boxes, class labels, scores, binary per-instance masks and overlap
decisions, plus the derived int32 instance layer. Threshold float32 outputs
before any compact storage conversion. Full probability tensors for all COCO
classes are not required; avoid letting optional diagnostics consume the
candidate storage allocation. Teacher confidences are uncalibrated metadata,
not correctness probabilities.

Use only frozen RGB, the allowed role-bounded RGB context, validity/K metadata
and the fixed feature coordinates. Neither teacher generation nor review may
consume S0–S4 masks, detector boxes, scores, tracker identities, ensembles, or
historical candidate masks. Do not refine teacher contours with any candidate
SAM checkpoint. Similarly, do not copy M0–M2 masks into the changing-background
reference. Label generation must not depend on candidate rankings, downstream
geometry, or the accepted-map membership of a point claimed to be static.

The teacher is outside the compared segmentation configurations, which avoids
direct self-scoring. It can still share COCO training data and model-family
biases with compared systems. A fresh agent session supplies a separate review
procedure, not a statistically independent model or a human reference. Record
these limitations rather than claiming independent training evidence.

## Review that a vision agent can perform

Use a fresh agent session that receives the annotation task, frozen RGB/context,
teacher reference, schema, review budget and permitted paths. Supply no candidate
outputs, method IDs, scores or conclusions. Restrict the review task to its
explicit input manifest; never ask it to discover historical benchmark outputs.
Record the requested/available model identity and task/session IDs honestly. If
an immutable provider model snapshot is unavailable, say so rather than
inventing one. Save the image/overlay hashes and structured decisions to make
the actual review auditable.

Generate deterministic, indexed review sheets with at most four unique images
per sheet. Each RGB and associated overlay panel retains its 960×540 pixels;
use original-resolution viewing. Every image needs its own explicit review row.
A single contact-sheet-level approval is insufficient. Aim to inspect all 232
images visually within the review allowance. Record actual image IDs and crops
viewed, and distinguish `structural_only` from `visual_and_structural` review in
each row. A script can audit every image without a vision agent seeing every
image; that distinction must remain visible in both admission and the report.
Where performed, visual review consists of
an RGB-first inventory followed by inspection of the reference overlay; this
helps expose missing detections rather than merely validating shown masks.

For every image the reviewer can record:

- Clearly visible people, visible-ball presence, missed or spurious instances,
  and gross contour errors, with source-pixel coordinates for corrections or
  uncertain regions. Tiny balls require native image crops, including locations
  found in RGB but omitted by the teacher. Teacher nondetection alone never
  establishes ball/person absence.
- Player, other-person or uncertain role; visibility, occlusion, blur and tiny
  ball flags. A generic person label does not determine role. Do not infer
  hidden surfaces or create an instance for a fully occluded object.
- Shadows, displays, illumination changes and possible moving background from
  supplied role-bounded temporal RGB. Review can establish an evident changing
  region, but uncertain temporal evidence must remain unknown. A still image
  or an empty teacher mask cannot establish that all remaining pixels are static.
- For each of the 112 pairs, plausible continuations, visible births/disappearances
  and unresolved associations, using both frames and enlarged instance crops.
  Numeric teacher IDs have no temporal meaning.
- All 768 fixed feature locations using indexed crops with full-image context
  and, where needed, allowed temporal context. Retain `suitable=true`, `false`
  or `uncertain`, with an individual decision bound to each existing index.
  Being present in the accepted sparse map is not the review criterion.

The agent cannot certify every contour to two pixels from a montage, validate
invisible players/balls, guarantee missed-instance completeness, prove static
geometry from image appearance, or supply physical distance truth. Record
contour review resolution explicitly. Boundary F1 remains available as agreement
with a proxy contour; it must not be described as a verified contour-accuracy
measurement. Persist uncertain boundary polygons/masks without replacing them
with a uniform arbitrary quality threshold.

Allow one documented adjudication revision for each disputed image or pair.
Corrections can add/remove reference instances or rasterize RGB-authored visible
surface polygons; uncertain objects/contours may instead remain excluded from
the affected metric. Keep both revisions and bind the final layer hash to the
review and adjudication record. No teacher rerun, alternate threshold, candidate
feedback, or repeated improve-and-rescore loop is part of adjudication.

## Temporal and incomplete-layer handling

Predict each unique image once and reuse its immutable reference in all its
pairs. Following the frozen amendment, a deterministic per-class Hungarian
match using eligible mask IoU >=0.5 can generate association proposals, with
stable ID ties. This is only a proposal:
motion can remove overlap, especially for the ball. The reviewer must confirm
continuation/birth/disappearance or mark the association unknown. Do not convert
an unmatched proposal automatically into a true birth or disappearance. Preserve
one record for every visible reference instance, including unresolved instances,
with no duplicate endpoint IDs. Keep the existing pair grouping for statistics.

Use separate eligibility states for person, ball, roles, changing background,
static evidence, contours, temporal identity and feature suitability. Presence
needs `present`, `absent` or `unknown`; absence requires an explicit RGB review.
For dense layers use a candidate-independent known/unknown domain or an explicit
whole-layer unknown state. An all-zero changing mask with no temporal review is
unknown, not evidence of an unchanging image. Role uncertainty need not invalidate
person-union scoring; uncertain changing background need not invalidate semantic
scoring. Static scoring requires both semantic and changing-region evidence on
the same domain. Feature uncertainty must not become a suitable-feature vote.

Retain all 232 images even where a layer is unscorable. Publish known and unknown
image/pixel/instance counts by camera and branch. Freeze these domains before
candidate output inspection and use identical domains across methods. Unknown
regions cannot be selected separately for each candidate or counted as true
background/negative examples. The frozen amendment additionally allows complete
valid-grid agreement with the teacher's person/ball masks. Such a row must say
`reference_scope=whole_valid_teacher_proxy`; its zeros are teacher negatives,
not verified object absence. Report teacher-negative-frame disagreement under
that name, and reserve true negative-frame or missed-instance claims for actual
review evidence. Never merge these full-grid proxy rows with any separately
reviewed-domain rows as if they were one truth source. If a required class domain has no
support, mark its metric undefined. Keep the original raw-count pooling,
equal-camera aggregation, temporal grouping and paired bootstrap; those
intervals describe variation conditional on this imperfect fixed reference and
do not quantify teacher error or model bias.

## Minimum schema, gate and selection changes

1. Add a versioned annotation mode such as
   `candidate_blind_model_assisted/v2`. Retain the existing human validator for
   historical bundles. Add explicit teacher/agent contributor kinds, provenance,
   freeze hash/time, review coverage, per-layer eligibility and amendment hash.
   A contributor ID must never be made to pass by claiming `external_human`.
   Keep actual human person-hours zero and record automated consumption in its
   actual units.
2. Change bundle and image statuses to distinguish reviewed proxy evidence from
   human truth. Validate image membership, original RGB/K/grid/valid hashes,
   dtypes, instance metadata, every feature index and all pair records as before.
   Every uncertainty must have a disposition: corrected, accepted as proxy, or
   excluded/unknown. Replace the demand for literally zero unresolved semantic
   uncertainty with zero **undisposed** review findings; retain uncertainty counts.
3. Split engineering/model admission from per-metric reference eligibility under
   the explicit amendment. Completed model-assisted review can satisfy the new
   annotation-processing prerequisite without claiming that all layers support
   every quality score. Missing/incomplete review is still incomplete work.
   Preserve candidate runtime, scale, geometry, license, data-access and resource
   gates. The annotation amendment is not permission to call other implementation
   gaps qualified.
4. Keep the original S selection tuple, rounding, camera balancing and eligible
   candidate set where all its required fields are available from the same
   frozen candidate-independent proxy domains. Tag the selected arm
   `proxy-selected`. The frozen amendment explicitly broadens the original
   missing-person/ball S2 default to missing required ranking terms: select S2
   as an unverified baseline when the tuple is undefined. Save the exact missing
   fields; do not remove them after seeing scores or silently substitute zeros.
5. Keep the original M selection tuple only where reviewed semantic and changing
   reference layers support it. Explicitly add **M0 as a predeclared baseline
   fallback** when the automated changing/static reference cannot support the
   full tuple. Save `selection_status=unverified`, the missing fields and
   `reason=annotation-policy baseline default`. M0 is then a control choice, not
   a quality winner. If M0 itself lacks valid execution evidence, dependent arms
   remain blocked. Preserve the N selection rule and all combined depth/license
   gates; no S/D substitutions beyond documented rules.
6. Amend P31-3 prospectively to require complete model-assisted processing/review
   records for all images, explicit structural/visual review scope, eligibility,
   and the prescribed paired proxy metrics wherever supported. The saved
   original human-independent P31-3
   remains historically unmet. Propagate evidence mode into `annotations.json`,
   admission, all metric files, `finalists.json`, combined reports and the final
   criteria assessment. State that independent human quality and physical
   accuracy remain unverified.

## Bounded annotation allocation

Expand the **existing unstarted single `annotations` slot** from import/check
to teacher generation, review, adjudication and import under the explicit
annotation amendment. Cap its total end-to-end elapsed wall time at 21,600
seconds, including model load, CPU work, agent review waits and cleanup.
Charge this against the existing cumulative CPU preparation/scoring/report
allowance; it is not a conversion of unused human hours into extra GPU jobs.
The amendment separately records a 1,200-second asset-acquisition limit. Count
actual acquisition wall time in the cumulative CPU scope and explicitly record
whether it is also contained within the 21,600-second annotation limit. Do not
silently omit acquisition consumption. The phase splits below are scheduling
recommendations; they are not additional hard limits already imposed by the
saved amendment.

| Annotation phase | Maximum seconds | Fixed work allowance |
| --- | ---: | --- |
| Teacher generation and review-sheet preparation | 10,800 | One CPU teacher process, one frozen checkpoint/configuration, 232 unique image inferences; first-result qualification inside this attempt |
| Fresh candidate-blind visual review | 7,200 | One initial review per image, all 112 pair-association reviews, required object/uncertainty crops |
| Adjudication, rasterization and final import/check | 1,800 | At most one final revision per disputed image or pair; preserve unresolved-layer exclusions |
| Fixed static-feature audit | 1,800 | Exactly the existing 768 indexed locations, conveniently grouped into 48 per-image audit sheets |
| **Total annotation slot** | **21,600** | **One attempt; no additional candidate model evaluations** |

Use one teacher process and at most eight CPU threads/workers; one annotation
agent at a time is sufficient. Record teacher inference calls (maximum 232),
review item counts, actual wall time, and all phase consumption separately.
Teacher download is a single checkpoint transfer with the repository's specified
safe permission retry if applicable; it does not create another inference
attempt. No alternative checkpoint/build or GPU teacher run is allocated.

The full 21,600-second reservation leaves
35,902.53266579506 seconds (9 h 58 min 22.53 s) in the CPU cumulative scope for
aggregation and reporting, based on the saved consumption inspected here. It
uses zero of the 36 GPU jobs, zero new environment builds, and no M/N algorithm
attempts. If asset acquisition is charged separately, reserving its full 1,200
seconds additionally leaves 34,702.53266579506 seconds (9 h 38 min 22.53 s).
Reconcile against the latest ledger before dispatch; these figures
are a checkpoint calculation, not permission to reset a clock.

Use compressed/packed binary masks and compact review records so reference
artifacts do not unnecessarily consume the existing 150-GiB total. Count the
teacher checkpoint and copied visual review sheets. Preserve required provenance
and final layers; full native probability tensors are optional. Stop on the
first recorded total/resource limit and retain partial evidence. Unused
annotation time cannot fund another teacher attempt or candidate experiment.

## Verification before scored use

Use focused schema/fixture checks for candidate-derived reference rejection,
wrong image hashes/grids, missing review records, teacher nondetection versus
review-confirmed negatives, per-layer unknown propagation, pair endpoint
coverage, feature-index mismatches, changed frozen domains and unverified
fallback labeling. A fixture should demonstrate that an unknown changing layer
cannot produce a perfect static score or select M0 as a measured winner.

Before any candidate-dependent scoring, verify all 232 image review records,
112 pair records and 768 feature records (including explicit uncertainty), bind final layers/domains to the
review hash chain, and freeze the bundle. Recheck the frozen hash at aggregation.
Report paired proxy agreement, descriptive runtime/geometry results and missing
evidence separately. No conclusion should upgrade automated agreement into
human-independent accuracy, a confirmed superior segmentation method, or
production readiness.

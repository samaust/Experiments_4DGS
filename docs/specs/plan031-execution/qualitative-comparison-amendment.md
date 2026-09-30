# Qualitative comparison amendment for Plan 031

## Authority and precedence

The user requests generated results followed by a human qualitative comparison: what looks better in a frozen frame, what looks better in motion, artifacts and sharpness. The user confirmed matched frames, synchronized clips and supporting diagnostics. This amendment replaces Plan 031/protocol v1's annotation-dependent evaluation, statistical mask/temporal scoring and automatic metric-based quality/finalist selection for future comparison work. It takes precedence over those requirements in the historical plan and protocol. Historical source documents and recorded runs remain unchanged; their hashes continue to describe their original contracts.

## Generated review package

Code produces a versioned, immutable package with a manifest, a local comparison viewer, matched frame images, synchronized video clips and component diagnostics. Every artifact binds its candidate/configuration, stage, accepted input manifest, camera/frame or time range, resolution, source result, result hash and ledger outcome. Include the reference/control alongside comparable candidates. Record failed, blocked, missing and unavailable outputs explicitly; partial artifacts are labeled diagnostic and cannot count as successful model results.

Freeze the comparison camera/time selection and presentation settings before human review. Use identical scene/time/viewpoint, playback rate, output size, color handling and crop for a matched comparison; original Basketball time is 25 fps. Common zoom and crop controls apply identically to all displayed candidates. Document any unavoidable mismatch. Show full-frame views plus predetermined detail regions, and retain the complete generated selection so favorable examples cannot be cherry-picked after review. Additional examples form a separately identified revision. Clip manifests retain original frame IDs/timestamps. Sparse predicted frames are labeled sequences or slideshows; they cannot be interpolated or played as if they were continuous generated motion. Missing motion evidence is unable to judge. A package without a comparable generated candidate/control pair is a readiness inventory, not a completed qualitative comparison.

Reuse the accepted input windows and role boundaries: reconstruction 0–49; calibration fitting 50–149; selection 150–199. Freeze actual existing frame IDs/clip intervals in the package; the former 232 annotation images are not a new labeling task. Never relabel calibration diagnostics as final renders. Final rendered frames/clips belong in the package when actual authorized pipeline results exist. Component mask/depth/motion/geometry overlays support diagnosis; visual sharpness of a colorized depth map is not photorealistic render quality. Missing final renders require a specifically bounded generation stage before they can be judged; this amendment does not fabricate or authorize training/render allocations.

## Human review

One actual human reviewer is sufficient. The reviewer compares generated candidates directly; candidate outputs are intentionally visible. No external annotation files, separate blind annotator or adjudicator are required. A local form or structured record captures reviewer name/handle, date, package version/hash, compared candidate IDs, exact frame/clip references, observations and preference for each criterion. Candidate labels may be shown; a randomized anonymous A/B display is optional and its mapping must be retained.

| Criterion | What the reviewer records |
| --- | --- |
| Frozen-frame appearance | Overall plausibility, object shape/boundaries, missing or spurious content, and relevant detail at the matched time/view |
| Motion quality | Temporal coherence, flicker, jitter, ghosting, trails, popping and moving-object continuity in synchronized clips |
| Artifacts | Location/time and severity of halos, holes, floaters, duplication, smearing and other observed defects |
| Sharpness and detail | Edge clarity, fine detail, blur and oversharpening at identical zoom, when applicable to the displayed output |
| Overall preference | Preferred candidate, tie, no clear preference or unable to judge, with a short reason and tradeoffs |

For pairwise criteria use candidate A, candidate B, tie, no clear preference, or unable to judge. Multi-candidate comparisons may name preferred candidates or leave them tied. Not-applicable criteria and unavailable evidence are explicit. Numeric ratings are optional subjective opinions, not objective accuracy measurements. No forced winner or automatic tie-break by metric/ID is required. No minimum number of independent reviewers or statistical-confidence claim is imposed.

## Decisions and final assessment

Code validates and binds human review records; it never supplies or invents the judgment. A package can be ready before a human reviews it. The actual-review ticket remains open until real human observations are recorded for the declared comparison scope, including justified unable-to-judge dispositions. Missing images/clips and missing human feedback are separate states. Report display order, reviewer context and optional anonymization honestly; do not claim blinded or independent multi-reviewer evidence unless it occurred.

Freeze downstream choices from the human preferences, explicit tradeoffs and engineering feasibility. Existing runtime, scale, geometry, license and allocation gates remain eligibility checks, not perceptual-quality rankings. Ties or incomplete evidence require a recorded human choice or a blocked selection; code cannot silently revive historical metric-selected finalists. Freeze choice provenance before downstream execution. Later combined results receive a separately bound follow-up qualitative review before final conclusions.

The final report links comparable images/clips, diagnostics, original human observations, preference records, configurations, lineage, unavailable arms and resource costs. Conclusions say which reviewer preferred which result under which conditions. Annotation accuracy metrics, bootstrap significance and independent physical-depth accuracy are not required deliverables. Existing engineering measurements may be reported as diagnostics and execution costs. Subjective appearance does not establish measured physical accuracy.

## Implementation and acceptance

Implement new package/viewer and human-review request/result contracts using immutable files and existing ledger/admission boundaries. Existing annotation import and independent-scoring code remains a historical/optional path; removing the old requirement must not be implemented by weakening its human-truth validator or treating proxy data as ground truth. Bind the amendment and new comparison mode explicitly before affected execution. Preserve consumed attempts and checkpoints; use new identities/artifact directories when the old account/output is consumed, only after applicable authorization.

Acceptance requires a reproducible package of actual generated comparisons, valid real human qualitative records, frozen human-led choices where required, an honest final report and complete child issue accounting. No fabricated reviews or new experiment allocations are permitted. Tests cover matched identity/time/settings, changed hashes, absent outputs, replay/substitution, tied/unjudgeable outcomes and refusal to treat empty/synthetic forms as performed review.

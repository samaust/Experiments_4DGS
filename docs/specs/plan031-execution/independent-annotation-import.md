## Problem Statement

The accepted 232-image annotation bundle is model-assisted proxy truth. It does not supply independent semantic, temporal-identity or changing-region review. The maintainer cannot claim independently scored benchmark performance from that bundle, and no independently reviewed replacement has been supplied.

## Solution

Prepare and validate the independent human annotation import workflow, then import a supplied primary, blind independent-review and adjudication bundle against the exact accepted images. Preserve the proxy bundle and expose missing human input as a blocker until the required reviewed evidence is available.

## User Stories

1. As a research reviewer, I want proxy evidence identified explicitly, so that model outputs cannot be relabeled as independent truth.
2. As a annotator, I want the exact accepted image and role manifest, so that annotations cannot silently substitute images.
3. As a annotator, I want the prescribed 232-image membership, so that coverage is verifiable.
4. As a primary annotator, I want a stable revision and contributor attestation, so that the primary work has a traceable origin.
5. As a independent reviewer, I want a blind review workflow, so that method outputs and scores cannot influence the review.
6. As a research reviewer, I want reviewer independence verified, so that the primary and review roles cannot be conflated.
7. As a annotator, I want semantic/static and changing-region layers represented, so that metrics can judge the intended image regions.
8. As a annotator, I want instance identities and temporal associations represented, so that tracking continuity can be evaluated.
9. As a annotator, I want ignored and invalid regions declared, so that ambiguous pixels cannot become unreviewed negatives.
10. As a research reviewer, I want unresolved disagreements counted, so that incomplete adjudication remains visible.
11. As a adjudicator, I want the primary and review revisions bound, so that the decision applies to the actual reviewed layers.
12. As a research reviewer, I want final layer hashes verified, so that import cannot accept changed annotation bytes.
13. As an operator, I want missing or duplicate image records rejected, so that coverage cannot pass with substituted membership.
14. As an operator, I want invalid roles, masks or associations rejected, so that annotation defects cannot corrupt scoring.
15. As a maintainer, I want the original proxy bundle preserved, so that new truth does not rewrite historical evidence.
16. As an operator, I want import charged through the existing ledger, so that annotation work retains provenance and CPU accounting.
17. As a user, I want missing human evidence listed precisely, so that the agent can request concrete inputs without inventing them.
18. As a research reviewer, I want annotation readiness separated from metric-depth ground truth, so that semantic review does not imply physical accuracy.
19. As a maintainer, I want a validated reviewed bundle available to scoring, so that later metrics use independently reviewed truth.
20. As a maintainer, I want closure only after actual reviewed input is accepted, so that a template or proxy cannot satisfy completion.

## Implementation Decisions

- Parent: #18. Related preparation: #3 and the fifteen-arm readiness handoff. Scoring/reporting depends on this child’s accepted reviewed bundle.
- Use the existing annotation template, independent-human validator, import controller and immutable result/ledger interfaces. Keep the existing model-assisted proxy bundle and its policy/review records as history.
- The supplied bundle must match the exact accepted input manifest and prescribed image/role membership; include contributor attestations, primary revisions, blind independent reviews, adjudication records and final layer hashes.
- Validate semantic, instance, static/changing/ignored/valid layers and required temporal associations against their image and role contracts. Reject missing, duplicate, substituted or unreviewed records and unresolved adjudication.
- Use actual external human evidence. The agent may prepare templates, instructions and validation/import machinery, but may not fabricate contributor identity, independence, human review, adjudication or measurements.
- Import only after complete validation and the applicable protocol/ledger checks. A changed scientific annotation policy requires separately recorded authority; generic implementation authorization cannot alter frozen scoring definitions.
- Acceptance requires the full prescribed independently reviewed bundle imported against immutable accepted inputs, zero unresolved required disagreements, verified records and retained proxy history. Keep the issue open while human inputs are missing.

## Testing Decisions

- Use the annotation import boundary as the main seam; reuse existing independent-review and proxy/human validation fixtures.
- Test externally visible rejection of proxy-as-human substitution, missing attestations, same-person primary/review, absent blindness, changed revisions/hashes, wrong image/role membership and unresolved disagreements.
- Test malformed layers, invalid associations and duplicate records with independently defined small masks and identities.
- Check that rejected bundles cannot publish a qualified annotation result or replace historical proxy records. A complete supplied bundle must pass the full validator before scoring.

## Out of Scope

- Generating independent human truth with a model, inventing attestations, contacting or assigning contributors without authorization, or assuming human reviewers are available.
- Changing annotation selection, scientific definitions or accepted image membership without a separately approved amendment.
- Model execution, new model allocations or treating mask/identity annotation as independent physical-depth ground truth.

## Further Notes

- A request for an existing independently reviewed human bundle is pending; none has been supplied in this conversation.
- The issue is implementable at the import/validation seam but its completion requires external human evidence. The ready-for-agent label does not remove that blocker.
- Missing independent physical-depth reference evidence remains an explicit scoring/reporting limitation and must not be inferred from reviewed segmentation layers.

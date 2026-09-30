# Segmentation human review 001

The user submitted the actual segmentation review on 2026-09-30. The raw
structured record is preserved in `segmentation-submitted.json`, including its
blank reviewer name, empty examples and original observations/preferences.

The user subsequently confirmed:

- Reviewer name/handle: `samaust`.
- Frozen-frame example: `camera1-reconstruction-0`.
- “playback is not broken. It's only available for some selection and the reviewer did not notice”.

`segmentation-corrected.json` applies only that confirmed name and the exact
S2 frame-0 reference under the matching frozen-frame selection. Every observation,
preference, date, tradeoff and package binding remains unchanged. The package's
S2 media confirms that selection/frame membership. The playback clarification
is retained here separately; the originally submitted motion observation stays
untouched as historical feedback. No playback defect or viewer fix is claimed.

The corrected submission passes the actual-review validator against the existing
immutable package and its charged generation graph. `validation.json` preserves
that result and the raw record's rejection for missing reviewer identity. The
implementation agent performed these read-only checks in its isolated worktree;
root coordinates actual immutable import, live accounting and issue updates.
No human review or preference was fabricated by the validator.

## Remaining human choice

The reviewer explicitly prefers S2 for frozen-frame segmentation and says S2
seems best overall in the observation. The structured overall preference remains
`unjudgeable`. Code preserves that value and cannot turn it into an approved
finalist automatically. An explicit human overall choice is needed before a
ready downstream decision can be frozen. Motion, artifacts and sharpness also
retain their submitted unjudgeable dispositions; this record does not judge
unseen trained renders or establish measured accuracy.

## Existing playback controls

Choose a selection containing video media to use playback; a frozen-frame
selection shows still images. Continuous clips can use synchronized playback.
Sparse sequences are labeled slideshows and are excluded from the synchronized
continuous-motion control. Such sparse evidence cannot establish continuous
motion quality. Switching selections does not change the immutable package or
submitted review; new observations can be submitted as a separately bound
record after viewing the desired evidence.

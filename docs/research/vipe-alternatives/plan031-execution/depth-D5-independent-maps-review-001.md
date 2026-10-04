# D5 independent completed-map review

PASS for the completed `plan069-D5-maps-001` stage. This is a read-only CPU review, not a new model attempt or qualification.

- All 256 map records and hashes verified: 60 accepted anchors and 196 additional clip frames, exactly the planned camera/frame union. Source RGB, inference RGB, input/context identity, camera intrinsics, roles and grid metadata agree with their retained records.
- Each NPZ was streamed separately. Shapes, validity and positive finite camera-Z values passed. Published valid depth is exactly equal to both preserved raw values and native point-map Z; conversion count is zero. No point-map magnitude, focal rescaling or second geometric conversion was applied.
- Fit and selection checks passed with frozen scale `1.5308726543170366`; selection references the exact fit receipt. This establishes engineering eligibility, not physical accuracy.
- The reviewed source archive and all 123 source-file records agree across source review 004, qualification 002 and its runtime receipt. The 37 historical local-source records agree. Current files were checked except `ledger.py`, which legitimately changed after completion; historical binding is not fresh execution authorization.
- Ledger finish 692 is complete, with confirmed cleanup, no deadline exceedance and no surviving owned processes. GPU reservation was 129.622317776 seconds and peak device memory 4,842,323,968 bytes. The driver CPU duration 23.941174780 seconds has exactly one subsequent charge at event 693; together they equal total driver duration 153.563492556 seconds.
- The retained temporary directory contains only an empty CUDA cache directory. The initial review incorrectly required directory deletion; that assertion was corrected to the actual process-cleanup contract. Nothing was deleted or changed in the shared run.

The successful review took **15.760441123 seconds** of elapsed time; peak resident memory was **63,385,600 bytes**, with at most **10,886,400 bytes** of map arrays retained simultaneously. Both are within the requested 30-second / 64-MB review bounds. The immutable local evidence is `.local/D5-independent-map-review-001/review.json`; the reproducing script is alongside it. This agent did not charge or mutate the live ledger.

D5 clips and previews are separate stages. Human review and physical accuracy remain pending. This result does not complete #56 or #44; D6/D8 and final package acceptance remain required.

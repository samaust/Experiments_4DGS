# D11 actual comparison outcome — independent review

Issue: [#58](https://github.com/samaust/Experiments_4DGS/issues/58).

## Result

All five issue acceptance criteria are complete. The issue has no child issues;
its dependencies #47, #54 and #55 are closed (GitHub checked during this review).
Root may close #58 after integrating this evidence. Keep #34/#35 open: D11 is a
relative-log visual comparison arm, not an eligible metric depth choice. The
complete aggregate, human preference/metric choice and downstream renders remain
separate unfinished work.

| Acceptance criterion | Evidence reviewed | Result |
|---|---|---|
| Independent source/runtime/commercial qualification before inference | Immutable request, source review, qualification and passed admission; accepted setup/runtime records; commercial receipt permits the exact private owned-workstation scope | Passed |
| Frozen native single-step four-bit execution within bounds | Seed 2025, one step, NF4, bfloat16, timestep 0.499; supervised GPU interval includes first load/quantization, inference and completion | Passed |
| 60 anchors and four 50-frame clips | 256 unique maps = 60 anchors + 196 clip extras; matched source/D11 clips have exact 150–199 membership and normalization across each whole clip | Passed |
| Raw values, grid/source lineage and actual publication | All 256 native outputs retain unchanged values on valid pixels; 60 PNG hashes/pixels match independently calculated frame normalization; current canonical builder/renderer records match | Passed |
| Preserved attempts and approved disposition | One GPU reservation with accepted clean completion; no fallback or extra model attempt used; all acceptance outputs are actual | Passed |

## Measured costs

- Setup: **1,390.14 seconds**.
- Supervised GPU interval: **361.87 seconds**, including first load/quantization;
  worker interval: **288.33 seconds**. These are nested measurements, not additive.
- Device peak: **20,419,969,024 bytes**, below the original **22,548,578,304-byte**
  candidate ceiling.
- Clip CPU charge: **35.818860512 seconds**, one ledger charge at sequence 655.
- Preview CPU charge: **14.502096110 seconds**, including final budget verification;
  the result's **10.306017150-second** field ends before terminal accounting.
- Preview publication: **60 PNGs**, **7,443,157 retained PNG bytes**.
- Preparation review: **18.192636899 seconds**, separately charged by root at
  sequence 662. This is distinct from preview production.
- Read-only successful independent verification pass: **4.691678437 seconds**;
  recorded in the review JSON, without a ledger write by this reviewer.

Exactly one live ledger charge matches the immutable preview accounting record
and its elapsed time. Current retained D11 revisions plus frozen shared setup
overhead remain within the original whole-slot artifact ceiling. Post-completion
review uses that candidate scope; later unrelated downloads are not assigned to
historical D11. The passing producer receipt and verified producer source enforce
its original terminal no-download guard.

## Evidence

- [Actual outcome](depth-D11-outcome-001.json)
- [Independent review](depth-D11-independent-outcome-review-001.json)
- Canonical shared run: `.local/vipe-alternatives/plan031-20260913T032700Z`
- Native maps: `jobs/plan069-D11-maps-001/result.json`
- Matched clips: `jobs/plan069-D11-clips-001/result.json`
- Corrected anchors: `jobs/plan069-D11-anchor-previews-002/result.json`
- Preview accounting: `jobs/plan069-D11-anchor-previews-002/cpu-accounting.json`

This verification read existing artifacts only. It performed no model inference,
rendering, GPU use, canonical writes or live ledger mutation. Invalid prediction
pixels remain NaN; the preserved native files retain the original full outputs.
No human quality preference or physical accuracy claim is made.

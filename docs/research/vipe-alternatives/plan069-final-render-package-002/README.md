# D8 final-render review package 002 (#34)

The live package is `final-render/review-package-002/` under the run root
(`.local/vipe-alternatives/plan031-20260913T032700Z`): `package.json` (sha256
`06ed9aa22bd9501d2e70a688e1c3f381375d5df973189c45491bd90a9b51778d`), 24 H.264
clips and `index.html`. `package.json` here is a byte copy for the record.

- Candidates: the real held-out reference video, plus QF-B (M0/N0), QF-M1,
  QF-M2, QF-N1 and QF-N2. All use S2 segmentation and D8 depth and are trained
  for 5,000 steps.
- Clips: held-out cameras 0, 10, 20 and 30 (never trained on), frames 0–49 at
  25 fps, encoded from the exact published PNGs.
- Every arm's render result is bound to a cleaned, complete ledger finish
  (production DO grant at ledger 1043; finishes 1046–1103).
- Package 001 is a superseded four-arm build made while QF-N2 was refused by the
  artifact cap.

Review: open `index.html`, compare the motion (M0/M1/M2) and neighbor
(N0/N1/N2) sets, and export the review JSON. Import it with
`scripts/final_render_review.py import`. Research outputs only (licence
decision 2026-10-05).

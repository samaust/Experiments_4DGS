# Independent revision 002 frozen-frame acceptance

All 480 previews passed: D0, D1, D2, D3, D4, D5, D7 and D11, 60 exact context anchors each.

`check.py` imports no producer modules. It hashes bound evidence and independently reconstructs every decoded PNG pixel from one immutable NPZ at a time, checks 960×540 RGB and float32/bool contracts, metric 0–20 m legend/red overflow/magenta invalid handling, and relative normalization/direction. `bindings.py` links every NPZ to completed generation records and finds exactly one existing CPU publication charge per candidate. Both scripts are read only outside this report directory; no model imports, network, GPU or ledger mutation occurred.

Measured review: 10.296493575000 seconds total; each candidate below 1.5 seconds and 70 MiB peak RSS. Each invocation has a 60-second deadline. Root must charge this review once using `summary.json`; the reviewer has made no shared ledger writes.

Receipts retain exact hashes and source paths. These checks accept publication integrity, not physical accuracy or visual quality. Human review remains pending. D7 remains geometry ineligible because its earlier scale check failed; D11 remains relative only. No issues were closed.

Branch `plan069-preview-review`; integration owner cherry-picks the accompanying commit after its source freeze permits. No production code changed.

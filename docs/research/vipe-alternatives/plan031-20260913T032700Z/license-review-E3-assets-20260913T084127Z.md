# SAM3 acquired-asset license review

Reviewed 2026-09-13 by Codex independent subagent `/root/geometry_scoring`. Only the three newly verified SAM3 asset subjects were reviewed; no installed runtime or historical asset closure is claimed.

| Exact asset subject | Commercial permission | Non-AGPL open-source preference |
| --- | --- | --- |
| SAM3 source | Meta grant verified subject to conditions; full compound source coverage unverified | Restricted by custom SAM License |
| SAM3 checkpoint repository asset | Primary `sam3.pt` Meta grant verified subject to conditions; ancillary tokenizer coverage unverified | Restricted by custom SAM License |
| BPE vocabulary | Unverified; exact upstream grant not established | Unverified |

The two exact local SAM Licenses are substantively identical (November 19, 2025; final newline differs). Their definition expressly includes trained weights. Section 1(a) provides a royalty-free grant covering commercial use, subject to license conditions, authority/acceptance, redistribution, privacy/trade/end-use restrictions and other obligations. No separate additional-commercial threshold or blanket noncommercial clause appears in these pinned texts. This does not establish a particular user’s eligibility or compliance. Section 1(b)(iv) restricts reverse engineering/decompilation; the custom license does not satisfy the frozen open-source preference. The source README and explicit pyproject LICENSE reference contradict the pyproject MIT classifier.

The tokenizer explicitly acknowledges copied components from VE/open_clip/OpenAI CLIP. A top-level Meta-rights grant does not independently establish those upstream rights or the separately admitted BPE vocabulary’s rights. The conservative compound-subject statuses preserve those gaps while separately identifying the definite primary source/model grant. No AGPL, noncommercial restriction or research ineligibility is inferred from missing notices.

Evidence: [exact subjects](../../../../.local/vipe-alternatives/plan031-20260913T032700Z/license-review-E3-assets-20260913T084127Z/asset-subjects.json), [dated review and per-subject notice hashes](../../../../.local/vipe-alternatives/plan031-20260913T032700Z/license-review-E3-assets-20260913T084127Z/asset-review.json), [validation](../../../../.local/vipe-alternatives/plan031-20260913T032700Z/license-review-E3-assets-20260913T084127Z/validation.json), [timing receipt](../../../../.local/vipe-alternatives/plan031-20260913T032700Z/license-review-E3-assets-20260913T084127Z/receipt.json). This is local documentary evidence, not legal advice or a runtime qualification. No ledger events were written.

# Candidate015 poll020 timing attestation

Main attests that poll020 on exec session handle 13761 was issued only after the independent PASS for poll019 was received and after `candidate015-postadmit-poll019-review-001.md` had been created. The exact tool-call sequence in the Main conversation transcript establishes this ordering; the poll020 raw tool receipt itself does not contain a pre-call clock sample.

The independent poll019 review artifact has mtime `2026-09-25T11:13:39.646206576Z`. The poll020 event therefore uses `2026-09-25T11:13:38Z` as a conservative outward lower anchor (one second before the review mtime), and `2026-09-25T11:14:56Z` as an upper bound one second after its saved post-call clock of `11:14:55Z`. The exact poll020 tool return, reported wall duration, and post-call clock are in `candidate015-postadmit-poll-020-raw.json`.

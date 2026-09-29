# S1 calibration recovery 004 preparation

Status: `S1-calibration-recovery-004` is a separate proposed one-attempt identity. Its authorization remains `additional_attempt_approved=false` and stage `REVIEW`. This review grants no GPU attempt. Recoveries 001, 002, and 003 are consumed.

## Failure diagnosis and source correction

The approved 003 attempt exited at calibration camera 0, frame 50, before publishing its first row, with `ValueError: progress byte capacity` at the 256 KiB produced-row limit. The failed frame retained 42 detection assignments. The frozen S1 request's nine required asset records serialize to 233,173 bytes, and the backend copied those records into every row's metadata. A CPU regression reproduces the exception using the frozen request and the observed detection cardinality. With the source correction, S1 rows retain `assets_sha256` and omit the repeated `assets` mapping; the full verified asset records remain in the frozen request. New 004 produced and qualified rows verify that compact hash against the request's exact S1 asset subset. The CPU regression now fits the unchanged 256 KiB row bound. The failed production row was never written, so its exact encoded size cannot be recovered; the regression reconstructs the observed cardinality rather than claiming byte identity.

## Frozen binding and limits

The live ledger has exactly 467 events, 363,162 bytes, SHA-256 `d958d128e3b8c7a7263e0e07ba6d91e3c7ec5ae7ba855935895673fc69418f96`, byte-identical to the immutable 003 post-dispatch snapshot. The terminal 003 failure at sequence 466 has hash `1d514977186ff88758192a8f4d4861f31c4c5ba01a57a1e96d8a7385497fc284`, confirmed cleanup, no surviving PIDs, and 25.151324003 GPU seconds charged. Cumulative GPU allocation is 4,412.83312326588 seconds over 33 attempts, with no seconds reserved. The 004 validator requires that exact consumed prefix, the 001–003 authorization chain, and the cleaned-up 003 lifecycle. It rejects prior redispatch, changed consumption, an unrelated ledger append, and another identity.

The proposed 004 document retains the original calibration request hash, S1 inputs and annotations, semantic amendment, configuration, E1 runtime and assets, baseline correction, 3,600-second attempt limit, 93,600-second cumulative GPU limit, and at most 30 seconds of cleanup reserve. It permits no reconstruction, setup, or downloads. The 15-second monitoring recovery window remains capped by the original work deadline. Each resource reading expires after one second, and a late reading never certifies safety. The ordinary S1 supervisor poll is still 100 milliseconds; the bounded recovery window is an exceptional monitoring gap, not a 100-millisecond sampling guarantee. The 003 attempt observed two recovered gaps of 2.084126931 and 1.935207914 seconds.

## CPU and host qualification

The sandbox CPU capture encountered `PermissionError: [Errno 1] Operation not permitted` when creating an AF_UNIX datagram socket. The one host retry passed 270 tests and 1,028 subtests, zero failures, errors or skips, in 224.457290475 seconds under its 240-second cap. The receipt, outer execution record and validation wrapper passed against the same current 78-file source set. The focused 004 binding test used temporary synthetic approval only; it did not alter the live ledger and did not authorize execution. The read-only host gate checked the exact ledger, E1 interpreter and imports, assets, source qualification, both request bounds, a 0.794-second storage sample and no GPU compute PIDs. It returned NO-GO only because approval remains at `REVIEW` and live binding is withheld. A fresh read-only host gate must run immediately before any dispatch.

## Proposed authorization and dispatch

Proposed authorization: approve exactly one GPU calibration attempt for `S1-calibration-recovery-004`, using the prepared authorization, unchanged scientific inputs and limits, current source qualification, and intact consumed 467-event ledger. This does not authorize redispatch of 001, 002, or 003, a consumption reset, reconstruction, new setup, or downloads.

Upon explicit approval, record that approval in `docs/research/vipe-alternatives/plan031-20260913T032700Z/s1-calibration-recovery-authorization-004.json` by changing `additional_attempt_approved` to `true`, stage to `DO`, and authorization text to the exact user approval. Then run the read-only host gate:

```bash
bash scripts/run_s1_calibration_recovery_004.sh --check
```

Only if the gate reports GO, the proposed single dispatch command is:

```bash
bash scripts/run_s1_calibration_recovery_004.sh --run
```

No 004 GPU attempt has launched.

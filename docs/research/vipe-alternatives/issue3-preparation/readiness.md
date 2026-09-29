# Plan 031 component preparation — issue #3

Preparation parent: `4301c55905e7a77b671be2ed1781fc1df83655b2` on `main`, with a clean starting checkout. Nine isolated worktrees began at that commit. S1 was integrated first; the remaining lane changes were integrated serially. The preparation used CPU fixtures and read-only historical evidence. It dispatched no download, setup, component, inference, or GPU job.

At the start of preparation, the live ledger held 467 events (363,162 bytes), SHA-256 `d958d128e3b8c7a7263e0e07ba6d91e3c7ec5ae7ba855935895673fc69418f96`. S1 calibration recovery 004 was at `REVIEW`, with `additional_attempt_approved=false`; recoveries 001–003 were consumed. Those facts must be rechecked before any later serial action. The frozen study, protocol, and current Plan 031 hashes are `6fbb6e55dedf444766c75e946c3d5099426839e0df158706d98d28b635353e8e`, `6d32683e3d351f8f19afffa11fe5664c5a15515f84a2b9380f86a39a757072f5`, and `5b2c3eec431337e720cad0dae60738b4040045d25815a790f8534e79eaa6dcd8`.

## Fifteen-arm readiness matrix

Each lane record gives the full result hashes, source/model/runtime pins, CPU checks, blockers, and next serial dependency. “Verified” means existing engineering evidence was checked; it does not mean independently scored benchmark success.

| Arm | Preparation state | Evidence and next gate |
| --- | --- | --- |
| S1 | Calibration recovery 004 proposed at REVIEW; reconstruction unresolved | [S1](s1.md): compact 42-detection progress row fits 256 KiB, asset-hash binding passes, 001–003 consumed. Frozen `AGENTS.md` preservation mismatch blocks full source-bound admission qualification. No 004 approval or attempt. |
| S2 | Recorded calibration and reconstruction verified | [S2/S4](s2s4.md): 510 and 840 outputs; shared E2 assets and pair reset checked. Duplicate successor emissions now fail and reset state. Later scoring needs independent annotations. |
| S3 | Recorded calibration and reconstruction recovery verified | [S3](s3.md): 510 and 840 outputs; prompt, merge, pair state, and memory evidence checked. Later scoring needs independent annotations. |
| S4 | Recorded calibration and reconstruction verified | [S2/S4](s2s4.md): 510 and 840 outputs; E2 assets, RT-DETR semantics, and independent SAM 2 pair contexts checked. Later scoring needs independent annotations. |
| M0 | Recorded result verified | [M0–M2](m0m2.md): 1,350 role-bounded rows; pair union checked. Independent motion truth remains absent. |
| M1 | Recorded result verified | [M0–M2](m0m2.md): 1,350 role-bounded rows; nine-frame context and pair union checked. Independent motion truth remains absent. |
| M2 | Recorded result verified | [M0–M2](m0m2.md): 1,350 role-bounded rows; MOG2 cold starts and shadow/foreground exclusion checked. Independent motion truth remains absent. |
| N0 | Recorded result verified | [N0–N2](n0n2.md): 30 references and three neighbors each; hand-calculated count order and ties pass. |
| N1 | Recorded result verified | [N0–N2](n0n2.md): 30 references and three neighbors each; hand-calculated Jaccard order and ties pass. |
| N2 | Recorded result verified | [N0–N2](n0n2.md): 30 references and three neighbors each; full score tuple, reranking, ties, and explicit fewer-than-three failure pass. |
| D0 | Recorded fit and check verified | [D0/D1](d0d1.md): immutable sample/K inputs and both scale receipts pass. Later physical-accuracy scoring remains separate. |
| D1 | Later recorded fit and check verified | [D0/D1](d0d1.md): completed receipts supersede the older blocked matrix entry; immutable sample/K and scale provenance checked. Later combined-arm gate remains separate. |
| D2 | CPU adapter prepared; model result pending | [D2](d2.md): DA3 conversion/validity fixtures pass. E5 exact source/asset verification and serial setup qualification precede frame-100 fit and frame-175 check. |
| D3 | CPU adapter prepared; model result pending | [D3](d3.md): Metric3D resize/focal/dependency fixtures pass; lower-clamp diagnostic corrected. E6 exact source/asset and serial runtime qualification precede fit/check. |
| D4 | CPU adapter prepared; model result pending | [D4](d4.md): Depth Pro supplied-focal/inverse-depth fixtures pass. E7 exact source/asset and serial runtime qualification precede fit/check. |

## Integration and limits

The component request/result boundary remains the integration seam. The S2/S4 duplicate-successor guard and D3 lower-clamp evidence correction are candidate-scoped; no frozen scientific setting was changed. N0–N2 gained hand-calculated fixtures without changing its public result fields. CPU tests were serialized under `/tmp/issue3-cpu-test.lock`, keeping test processes below the eight-worker limit. The host has one GPU; preparation used none.

Integrated checks: 62 affected backend, execution, neighbor, and motion tests passed; Python compilation and the S1 collected-test parser passed. A CPU-only full repository `unittest discover` run in its required process group ran 1,002 tests: 988 passed, 5 skipped, and 9 errors. Three errors are the S1 frozen `AGENTS.md` preservation mismatch described below. The other six are outside this issue's changed paths: missing `matplotlib` (one), `pytest` (three import errors), and `plyfile` (one) in the selected test interpreter, plus an existing Basketball v6 deadline fixture raising `TimeoutError` where its test expects `AssertionError`. No issue #3 fixture failed. The full-suite log is local at `/tmp/issue3-fullsuite-003.log`; no dependencies were installed or benchmark environments changed to make this broad run pass.

Central review found one shared scale seam gap: `vipe_benchmark.scale.evaluate` checks the frozen fit's candidate and scale-protocol hashes but does not independently bind it to the immutable input-manifest hash. The four existing D0/D1 requests and receipts were separately verified against the same manifest. A later shared-interface change needs its own contract decision and validation; it was not folded into a candidate lane.

S1's historical baseline pins `AGENTS.md` at 4,485 bytes, SHA-256 `3d09a19b0bf8e4bfcf7c25f5b001a769f2cce372a425fc1dd1a14fc299ef620f`; the live tracked file is 4,873 bytes, SHA-256 `21c986e57de9b8c4f6d0eb9cf15596b3f005c79706285da23be947944d930ab8`. This preservation failure must be resolved without rewriting prior evidence before treating any fresh integrated-source S1 qualification or refreshed REVIEW proposal as valid. The proposed calibration attempt remains unapproved, and S1 reconstruction remains a separate unresolved branch. The [integrated CPU capture](s1-integrated-capture.md) records the exact remaining failure.

The saved 232-image annotation bundle remains model-assisted proxy truth without independent semantic, temporal-identity, or changing-region review. Physical-depth accuracy and final comparative benchmark claims remain unverified. Future E5–E7 setup, depth fit/check, S1 authorization, scoring, and reporting must follow Plan 031's serial admission, exclusive GPU, evidence, and approval gates.

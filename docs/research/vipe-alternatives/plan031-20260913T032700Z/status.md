# Current: approved memory diagnostic and conditional full run

The user approved the [two-stage memory repair plan](sam3-memory-diagnostic-plan-001.md): one 10-minute/48-pair diagnostic and, only after validation, one 90-minute reconstruction. [331 CPU tests pass](implementation-validation-011.json). Both new GPU attempts remain unused. Next: commit the validated instrumentation, then dispatch the bounded diagnostic. The existing 22-GiB and cumulative resource ceilings remain unchanged; unrelated work stays stopped. Earlier sections are historical.

# Current stop: recovery002 reached the device-memory ceiling

The approved S3 reconstruction ran for **124.829 seconds** and exported **82/840 outputs** before the supervisor stopped it at **23.468 GiB**, above the unchanged **22 GiB** limit. [Assessment006](assessment-006.md), [corrected output/cleanup evidence](s3-reconstruction-recovery-results-002-corrected.json), and [accounting006](matrix-accounting-006.json) are authoritative. Cleanup is confirmed; no worker or GPU process remains active. The attempt is consumed, and no further attempt is allocated.

The OpenCV/native-helper repair in `2661c92` passed 325 CPU tests and the actual first pair; all 85 recorded native helpers completed successfully. The current blocker is reconstruction device-memory use. Partial arrays/masks are preserved, with no complete result manifest and no downstream promotion. No Codex denial or missing allow rule caused this stop. A bounded memory diagnosis and new explicit model-attempt allocation are required before further execution. Other stopped work remains stopped.

Current totals: 6 GPU attempts / 789.192 seconds; 7 setup attempts / 4264.035 seconds; CPU preparation 10307.919 seconds. Earlier sections are historical checkpoints.

# Current: recovery002 running; first pair qualified

`S3-reconstruction-recovery-002` passed [first-pair qualification](s3-reconstruction-recovery-first-pair-002.json), including successful confined native helpers. The single 5,400-second reservation is active; reconstruction is progressing toward 840 outputs. Implementation commit `2661c92` is bound to validation010. No final result or cleanup is claimed yet. Other stopped work remains stopped. Earlier sections are historical.

# Current: recovery002 authorized after OpenCV-path repair

The user approved another run. [Repair002](native-helper-repair-002.md) passes [325 CPU tests and the actual OpenCV import lifecycle](implementation-validation-010.json). [Authorization002](s3-reconstruction-recovery-authorization-002.json) binds the original and recovery001 failures and grants exactly one additional S3 reconstruction attempt of at most 90 minutes. No new GPU attempt has started. Next: commit the validated repair and dispatch recovery002. Other stopped work remains stopped. Earlier sections are historical.

# Current stop: additional S3 reconstruction attempt consumed

The user-authorized recovery failed after **17.421 seconds** with `ValueError: unadmitted native helper environment override: LD_LIBRARY_PATH`, before exporting any pair. [Results and verified cleanup](s3-reconstruction-recovery-results-001.json), [assessment005](assessment-005.md), and [accounting005](matrix-accounting-005.json) are authoritative for this stop. No worker/helper/GPU process remains active. No Codex denial or missing allow rule caused this failure.

The repair is committed as `9a9d0f7`; [322 CPU tests passed](implementation-validation-009.json), but the real OpenCV import lifecycle was not covered. Source review identifies its later `LD_LIBRARY_PATH` mutation as the likely cause. A targeted library-path/import-order repair and a new explicit reconstruction attempt allocation are required before another model run. The granted additional attempt is consumed; unused time cannot fund another attempt. Original failures, all 510 S3 calibration results, E1/E3 qualification, and historical consumption remain preserved. Other stopped work remains stopped; the full benchmark is incomplete.

Current totals: five GPU attempts / 664.363 seconds; seven setup attempts / 4264.035 seconds; CPU preparation 9725.919 seconds. Earlier sections below are historical checkpoints.

# Current: S3 reconstruction recovery authorized and repaired

The user authorized exactly one additional S3 reconstruction attempt, capped at 90 minutes, after native-helper isolation repair. [Repair](native-helper-repair-001.md) passes [322 CPU tests and host confinement fixtures](implementation-validation-009.json). [Authorization](s3-reconstruction-recovery-authorization-001.json) preserves the original failure and all cumulative limits. The additional attempt is not yet dispatched; no model ran during repair. Next: commit the validated milestone, then dispatch the single recovery automatically. Other stopped work remains stopped. Earlier status sections below are historical.

# Plan 031 status

## E1 setup recovered successfully

After the reported upstream reset, the user explicitly instructed “retry”.
[The new authorization](e1-recovery-authorization-002.json) grants exactly one
fresh `E1-setup-recovery-002` attempt, binding the cleaned-up first recovery
failure. Network recovery is unverified; this setup is the authorized retry.
[All 310 CPU fixtures pass](e1-recovery-validation-002.json). Cumulative setup
time remaining is 53,778.642 seconds; existing download, storage and runtime
limits remain enforced. Other stopped jobs retain their state.

[Recovery 002 completed](e1-recovery-results-002.json) in 442.676 seconds with
confirmed process cleanup and no remaining active jobs. The pinned CUDA 12.4
toolkit, correlation extension and Grounding DINO extension built successfully;
all eight required import entries passed. Setup retained Python 3.11,
PyTorch 2.5.1+cu124, torchvision 0.20.1+cu124 and NumPy 1.26.4, with the resolved
dependency lock and full environment/source inventory saved. No model
constructors or forwards ran; first-forward qualification remains pending.

`setup_result_record(..., 'E1')` verifies and resolves recovery 002 while retaining
the original E1 and recovery 001 failures. S1 model jobs were not dispatched by
this setup-only request. Cumulative setup usage is 4,264.035 seconds across seven
original/recovery attempts; total recorded downloads are 19,343,753,718 bytes and
peak run storage is 39,927,513,088 bytes. The implementation checkpoint is
`95db77d` (310 passing CPU fixtures). The E1-specific request is complete;
the full benchmark remains incomplete. Earlier sections below are historical.

## E1 recovery stopped

The user explicitly requested “Reset E1 allocation. Fix E1 failure and retry.”
[Authorization](e1-recovery-authorization-001.json) restores one E1 setup attempt
as `E1-setup-recovery-001`, preserving the original failure and all charges.
[Validation](e1-recovery-validation-001.json) passes all 309 CPU fixtures,
including proxy shutdown, AOT compatibility and independent recovery accounting.
The remaining cumulative setup allowance is 54,034.287 seconds before dispatch.
The [retry failed](E1-setup-recovery-001-failure.json) after 255.645 seconds during
base-package installation: upstream receive raised `ConnectionResetError:
[Errno 104] Connection reset by peer`. The proxy then closed its listener and
UV reported connection refusal. The original `ENOTCONN` shutdown defect did not
recur. No native build, import qualification or model forward was reached.
All process cleanup is confirmed; no jobs remain active. The new attempt is
consumed, and cumulative setup consumption is now 3,821.358 seconds across six
attempts. The validated recovery implementation is committed as `ee48aa1`.

The host command was approved; this is not a confirmed Codex sandbox denial and
no missing allow rule was reported. AGENTS.md's outside-sandbox network-failure
rule requires stopping affected work pending network resolution and explicit
authorization for another attempt. E1 remains unqualified and S1 remains blocked.
Other stopped work retains its state. Earlier paragraphs below are historical.

SAM3 access is **restored**, its pinned assets and exact E3 environment are verified, and **all 510 S3 calibration images completed**. The original S3 reconstruction attempt then failed on the benchmark's own subprocess isolation guard during Triton CUDA setup. [Assessment004](assessment-004.md), [failure details](S3-reconstruction-failure.json) and [accounting004](matrix-accounting-004.json) record the current stop. No model/setup job or subagent remains active; all process cleanup is confirmed. The run is incomplete.

Preparation and the single annotation pass are complete. All 232 images received independent visual and structural review; the labels remain model-assisted proxies. Roles, changing-region truth, verified negatives and temporal identity truth remain unverified. See [review results](automated-review-results.md), [annotation milestone evidence](annotation-milestone-validation.json), and [completed bundle record](annotations-002.json).

The execution implementation is committed as `7e80be5`, after 204 passing benchmark tests. [S0 calibration and reconstruction](baseline-segmentation-results.json) completed all 510 and 840 outputs, respectively, in 506.489 GPU-job seconds across two attempts, recorded in `67f2dfe`. Both passed their result checks and confirmed process cleanup. Peak total device memory was 6.0 GiB. [E1 setup failed](E1-setup-failure.json) after 207.021 seconds because the local download proxy mishandled a disconnected socket during half-close. Its single allocation is consumed and cleanup is confirmed; S1 cannot run under this allocation. No sandbox denial was found: the later connection refusal followed the proxy thread's recorded local exception. A focused fix and validation precede the six unconsumed builds. E0/E8 were inventoried without rebuilding; a separate full-file inventory preserves their original qualification records. The ledger retains preparation, annotation, acquisition, inventory and failed setup consumption; no historical allocation was reset.

The historical [first stopped assessment](assessment.md) and [active progress assessment](assessment-002.md) are retained as prior evidence. [Assessment003](assessment-003.md) records the current network stop without treating engineering checks as benchmark completion. The formal aggregation/report remains unstarted. [Earlier resume authorization](resume-001.json) did not authorize restarting consumed attempts or bypassing this later failure.

The [proxy close fix](proxy-close-race-review.md) passes 21 focused fixtures. The [exact source review](actual-e1-source-review.md) also identified S1/AOT directory, constructor and memory-grid incompatibilities; [constrained adapter fixes](actual-e1-compatibility-implementation.md) pass 53 focused fixtures. The exact implementation bytes used by S0 and the failed E1 attempt are [archived](implementation-source-archive-003.json), preserving their original hashes while later jobs use a newly validated version. No E1 operation is replayed.

[Eight exact license reviews](license-review-registration-001.json) are registered against the preserved E0/E8 inventories. Their [scope and limitations](license-review-20260913T053005Z.md) retain missing weight grants, native-library uncertainty and separate proprietary platform terms. These preference findings do not change research eligibility.

The [execution repairs and gated-download integration](execution-repair-results.md) passed [254 benchmark tests](implementation-validation-004.json) and are committed as `6cebada`. This validation includes immutable copies of all 60 source/test files and records the exact implementation used by E2.

[E2 setup failed](E2-setup-failure.json) after 767.690 seconds during source extraction: four ordinary SAM2 YAML aliases were rejected by the extractor's blanket symlink guard. The SAM2 checkpoint and RT-DETR assets remain preserved, along with the archive and partial source output. Cleanup is confirmed, with no native imports or model forwards. E2's sole build is consumed; S2 and S4 calibration/reconstruction slots are explicitly blocked without consuming GPU attempts. This is a local implementation failure, with no recorded access denial.

The [source extraction repair](source-extraction-repair.md) preflights exact archive membership, accepts only safe relative aliases to regular members, and records original link text and target provenance. [Validation005](implementation-validation-005.json) passes all 274 benchmark tests and preserves immutable copies of its 61 source/test files; the milestone is committed as `487595f`. E1/E2 are not replayed.

[E3 setup failed](E3-setup-failure.json) after 13.575 seconds: Hugging Face returned HTTP 403 Forbidden for the pinned SAM3 `config.json`, using the existing local credential. The outside-sandbox controller was approved; no Codex denial occurred. No duplicate allow rule is needed, and one cannot repair this upstream failure. SAM3 acquisition is stopped, its sole setup allocation is consumed, S3 branches are blocked, and process cleanup is confirmed. No model ran and no asset terms were accepted. The affected work cannot resume without resolving access and any exhausted allocation; unaffected work continues.

The [second repair milestone](execution-repair-results-002.md) passes [288 benchmark tests](implementation-validation-006.json). It integrates the SAM2 postprocessing guard, corrects D0/D1 uncertainty metadata, records actual processed camera K, and fixes accounting-cache cadence for later workers. [E4's original loaded implementation](active-E4-implementation-preservation.json) remains preserved as validation005. E4 was not restarted; its native import qualification was never reached.

Cumulative consumption is 6,735.913 CPU preparation seconds, 3,099.948 setup seconds across four failed attempts, and 506.489 GPU seconds across two completed attempts. [E4 failed](E4-setup-failure.json) after 2,111.662 seconds on `ConnectionResetError: [Errno 104] Connection reset by peer`. The host invocation was already approved; this is not a confirmed Codex denial and no missing allow rule was reported. AGENTS.md requires stopping affected work after this outside-sandbox failure. Shared network setup E5–E7 is stopped pending resolution and explicit resume.

All 53 slots are accounted for: four complete (preparation, annotation check, two S0 branches), four failed setups, 42 blocked slots and three skipped repeats. E5–E7, motion, neighbors, depth, geometry, staged aggregation and reporting have no consumed attempts. Unstarted slots may reopen on an authorized resume; E1–E4 may not. The [E4 source review](actual-e4-source-review.md) exceeded its internal 600-second cap by 17.570 seconds, fully recorded with its stop. Its separate [asset-only license review](license-review-E4-assets-20260913T065749Z.md) charged 236 seconds within its cap and remains unregistered as a whole runtime assessment. The latest validated source milestone is `94ff9ea`; all original output hashes and allocations are retained.

Frozen SHA-256: plan031 `27f3f284886f1af7e19602d0b21a2494ac1c5cbab1878b8e73b25874d43db74b`; study `6fbb6e55dedf444766c75e946c3d5099426839e0df158706d98d28b635353e8e`; protocol `6d32683e3d351f8f19afffa11fe5664c5a15515f84a2b9380f86a39a757072f5`.

## SAM3 access recovery

[Download verification](sam3-download-verification-001.json) records all 12 successful transfers, totaling 3,517,542,701 received bytes, including a small openly recorded redundant fetch of original sidecars. The 3,450,062,241-byte `sam3.pt` matches pinned SHA-256 `9999e2341ceef5e136daa386eecb55cb414446a00ac2b55eb2dfd2f7c3cf8c9e`. Acquisition took 103.377 seconds, used the existing credential, accepted no terms, and performed zero environment builds or model forwards. Original failures and partial files remain intact.

[Recovery review](sam3-recovery-review-001.md) and [actual source review](actual-e3-source-review.md) were completed within their separate 240- and 480-second bounds. The implementation preserves native detector-only checkpoint selection, observes missing/unused keys, checks serial/perflib state, and qualifies bundled lazy Triton imports. Prepared source archives are extracted into a separate editable tree; verified checkpoint bytes are reused. The new setup attempt, if dispatched, shares the original 57,600-second setup cap and all storage/download/device limits.

The independent [SAM3 asset license review](license-review-E3-assets-20260913T084127Z.md) retains conditional primary source/weight grants and unresolved ancillary/BPE rights; it is not a whole-runtime assessment. It exceeded its internal 300-second cap by 2.543001 seconds, stopped, and conservatively charged 303 seconds. This joins the earlier recorded E4 review overrun; overall budget-integrity criterion P31-5 is not met.

[Validation008](implementation-validation-008.json) passes 305 tests and retains Triton, TorchInductor and CUDA kernel caches under each monitored attempt directory. Installed Triton source confirmed that its default cache location would otherwise be outside the tracked run. E3 setup remains bound to validation007; the two original unstarted S3 branches are [reopened](resume-003.json) for validation008 dispatch, with no extra GPU allocations.

## Current stop after SAM3 reconstruction

The approved host command was `.local/envs/stg-colmap/bin/python scripts/basketball_vipe_benchmark.py --run-id plan031-20260913T032700Z stage --job S3-reconstruction --validation docs/research/vipe-alternatives/plan031-20260913T032700Z/implementation-validation-008.json`. It failed after 11.236 seconds with `PermissionError: standalone model worker subprocesses are prohibited` at `scripts/vipe_benchmark/isolation.py:36`, when native Triton requested `/sbin/ldconfig -p`. This is a confirmed application-level denial, not a Codex approval/sandbox denial. No missing Codex allow rule was reported; adding one would not change this Python guard. No pair rows or first-pair qualification were exported.

[The bounded Triton review](triton-subprocess-isolation-review-001.md) completed in 199.956 of 240 seconds and records all required helper families, checked inputs/toolchains and child-filesystem limitations. It performed no native compilation or model probe. The failed reconstruction attempt remains consumed; a new attempt requires explicit authorization under Plan 031, plus a validated isolation repair. No automatic retry or guard relaxation was made.

Current totals: four GPU attempts / 646.942 seconds, five setup attempts / 3,565.713 seconds, and 7,996.919 CPU preparation seconds. All 54 original/amended identities are accounted: six complete, five failed, 40 blocked, three skipped. The latest source commit is `cb55d37` and the latest implementation validation is 008 (305 tests). Earlier status paragraphs and assessments describe historical checkpoints; assessment004 is authoritative for the current stop.

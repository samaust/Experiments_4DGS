# Independent review — corrected candidate010 session proof

**Verdict: PASS for the saved, corrected `session-bound/v2` pre-admission proof evidence only.** The proof binds exact byte and SHA-256 records for driver, identity request, four ordered tool events and listed authority files. Event001 now has the correct digest for its unchanged original tool output. No admission artifact exists at the recorded path or at this review's read-only path check. This review does **not** authorize `ADMIT`, another session send/poll, identity admission, test, diagnostic payload or aggregate; fresh admission gates and separate independent clearance remain.

| Check | Finding |
| --- | --- |
| Proof and referenced bytes | [Session proof](../plan031-progress-20260922/main-session-proof-049-diagnostic-010.json) is `plan049-session-proof/v2`, mode `session-bound/v2`, diagnostic index 10 and handle **87565**. All **10** referenced files (driver, identity, four events, authorization, correction, Plan054 and evidence amendment) match the proof's exact byte lengths and SHA-256 values. The correction receipt's reviewed correction-report hash and corrected event hash also match current bytes. `cross_namespace_kernel_verified: false` is explicit, not a fabricated kernel-correlation claim. |
| Events and original returns | Ordinals **0–3** have roles `start`, `readiness`, `pre_admission`, `at_admission` and tools `exec_command`, then three `write_stdin` calls. All four saved results carry original handle **87565**; the three `write_stdin` arguments use that same handle. Their result objects match the first-party original Main returns supplied for prior independent reviews. No result has a terminal/error field. UTC start/return stamps are ordered within and across events. |
| Exact start/readiness | Event001's sent `chars` parses as `plan049-main-start-frame/v1` with handle 87565 and **the full exact event000**. Its output starts with the exact PTY echo of that frame, with terminal LF rendered as CRLF, followed by one readiness line and CRLF. The readiness line equals the proof's string byte-for-byte, and its SHA-256 is `cf979f23912f88f7a471005285d0a443d2b4afc7a372d3a9f2d574d47f222b98`. The line names the same identity and admission paths bound by the proof; the identity file is exactly **38,845 bytes** with the expected SHA-256. |
| Corrected digest and polls | Event001's exact **2,336 UTF-8 output bytes** hash to `4780a8b1d5dc604f7b58b3456c4bdab0c37629c097fcd87dfed90b51e0193921`, now equal to its `output_sha256`. Its current file hash `5a3e41343d649c577592f6155f12154c353321e76c02a9b4f31fac6306e53e9e` is the previously reviewed one-field byte-substitution checkpoint. The receipt preserves old file hash `0210f36fc11d052ddf337ed747404098986f81246c1b1dcc886ada3758e758d2` and wrong digest without changing the original result. Events002 and 003 send empty `chars`, receive empty outputs and have correct empty-output hashes. |
| Admission boundary | The proof's `admission_handoff` is a **prospective** exact `ADMIT\n` for handle 87565. The referenced `launch-admission-049-diagnostic-010.json` path is absent as a file and as a symlink. Neither proof construction nor this review sends that text or validates a diagnostic/test result. |

The saved nested tool-return wall values are **1.001101165** seconds for event000, **1.000977204** for event001, **5.001497478** for event002 and **5.001611786** for event003. They are per-call wall returns, not CPU time or total session duration. Candidate010 remains a live B/H ownership charge, while diagnostic006 and candidate009 retain separate unresolved native H charges. Candidate010 and old-session CPU, memory and complete wall use remain unknown.

## Exact file hashes

| Input | SHA-256 |
| --- | --- |
| [Proof](../plan031-progress-20260922/main-session-proof-049-diagnostic-010.json) | `43173ba91680d1dc5b2e371a827566a7a464e17f6e71e22bd09649c15e6891d8` |
| [Event000](../plan031-progress-20260922/main-session-049-diagnostic-010-event-000.json) | `9c0a454ecfc84f4ff95f159bb8a6e0c92f0d42a360ff91f738fe19511e5e24f6` |
| [Corrected event001](../plan031-progress-20260922/main-session-049-diagnostic-010-event-001.json) | `5a3e41343d649c577592f6155f12154c353321e76c02a9b4f31fac6306e53e9e` |
| [Event002](../plan031-progress-20260922/main-session-049-diagnostic-010-event-002.json) | `1194d27ab7be408b4195607eae81bf95e3e36c481b6d5b02c4792b8d70d8bbb2` |
| [Event003](../plan031-progress-20260922/main-session-049-diagnostic-010-event-003.json) | `2d5bece0b496f037920cfe6ec6ff8f8d481d9fa53523ebd411e6e203f7b893a2` |
| [Identity request](../plan031-progress-20260922/launch-identity-049-diagnostic-010.json) | `c451dac9ecf0aae9fdeac6935ab7c1fff59edaea84dcb2f94782c284a772f6e7` |
| [Correction receipt](candidate010-event-correction-receipt-001.json) | `58c7a87f7e8efeba6b7fe2676fefa839b39443ea9f897457ba795b83ef48e67f` |
| [Correction review](candidate010-event-correction-review-001.md) | `6cd9ed55833d4187b8ebca7db73ac8759bf5fae4327f9b4c66948095138b430e` |
| [Authorization](../plan031-progress-20260922/authorization-049-session-proof-001.md) | `6ee2d0f899c6ee20de96415079d9aa07900b51f2321ef37d20af5e7e171bd755` |
| [Plan049 Correction008](../plan031-progress-20260922/plan049-correction-008.md) | `e68129133349fbbecc25e725025c0cda833c7ab149aaacad0ff05ead4737cf91` |
| [Plan054](../../../plans/plan_054.md) | `91d0ac7191d944b8cf2175b74c74aff3d70d4dba4a530431f223cb8aab2df62d` |
| [Evidence amendment](../plan031-session-proof-wrapper-20260923/correction-008-trust-amendment-001-proposal.md) | `9a27dbb60afcf358409364987e0b74d219431e4b5a83652ac9c607f658426d84` |

Checks were read-only standard-library JSON/SHA-256 comparisons and a filesystem existence check; no project validator or test was run. No target process/session was contacted, polled, sent to, signaled, admitted or launched by this reviewer. Individual review tool commands reported about 0.2 seconds of wall time; total reviewer wall, CPU and memory use were not measured. No `prompts` content was read.

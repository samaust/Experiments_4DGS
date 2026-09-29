# Independent review — candidate010 event001 hash correction proposal

**Verdict: PASS for the proposed one-field evidentiary correction, not for admission.** Event001's stored full `write_stdin` result matches the first-party original Main return supplied for this review, but its derived `output_sha256` is wrong. SHA-256 of the exact **2,336 UTF-8 bytes** in `result.output` is `4780a8b1d5dc604f7b58b3456c4bdab0c37629c097fcd87dfed90b51e0193921`; the stored field is `15bcbf380b27e9ddcf3cb863495f7936daad2e0990acb01dd19b3205b48912ca`. The old event001 file hash is `0210f36fc11d052ddf337ed747404098986f81246c1b1dcc886ada3758e758d2`. Replacing that **single field value** while preserving every original result and other event field is a valid repair to prospectively revalidate the saved evidence. A direct same-length byte substitution would give event001 file SHA-256 `5a3e41343d649c577592f6155f12154c353321e76c02a9b4f31fac6306e53e9e`; this is an expected byte-preserving checkpoint, not a claim the correction has been made.

| Chain check | Finding |
| --- | --- |
| Event000→001 | Event001 `arguments.session_id` and returned `session_id` are both **87565**. Its `chars` parses as `plan049-main-start-frame/v1` with that handle and the **entire exact event000** as `event`. The result output begins with precisely that sent frame's PTY echo, changing only terminal LF to CRLF, followed by one readiness JSON line ending CRLF. No terminal/error result is recorded. |
| Readiness identity | The readiness line names `launch-admission-049-diagnostic-010.json` as awaiting Main admission and `launch-identity-049-diagnostic-010.json` as the identity request. The identity file exists with exactly **38,845 bytes** and SHA-256 `c451dac9ecf0aae9fdeac6935ab7c1fff59edaea84dcb2f94782c284a772f6e7`, matching the line. The admission path was absent in the read-only path check. The identity remains a driver request, not an admitted session proof. |
| Events002–003 | Both original Main `write_stdin` returns supplied in the task match the saved result objects: chunks `5cd5e0` and `6c6d3d`, returned handle **87565**, zero original tokens and empty output. Their `chars` are empty, roles are `pre_admission` and `at_admission`, ordinals are 2 and 3, and their empty-output SHA-256 fields correctly equal `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`. Event UTC order is 000→001→002→003. These are the two required live polls, not `ADMIT`. |
| Readback receipt | The separate hash-readback return records a synchronous `exec_command` with exit code **0** and output reporting the old event file hash, wrong stored digest, correct digest, 2,336 bytes and session ID 87565. Its `started_utc` is **null** with status “not captured”; the unmeasured `2026-09-25T05:59:00Z` remains explicitly labeled `invalid_initial_started_utc`. The receipt therefore does not fabricate a start time or session interaction. I recomputed its substantive digest independently from saved bytes. |

The proposal's account of a quoting failure is plausible: URL encoding leaves apostrophes literal, which can break a shell single-quoted dynamic command. This review relies on the directly recomputed digest and original result comparison, not on the proposed cause. The corrected workflow must record the old file hash and wrong digest in a separate correction receipt, change only event001's digest, re-read the resulting file, verify full result equality with Main's original return and all four event hashes/order/handles, and use a fixed non-interpolating hash readback for later returns. Do not rewrite event000 or the original tool results, invent the missing readback start time, or treat the old invalid event001 as already passing.

**No admission clearance:** Candidate010 remains a live B/H charge. The repair proposal authorizes no session contact, poll, signal, `ADMIT`, identity admission, test, diagnostic payload or aggregate. Independent review of the completed corrected session-bound proof and fresh admission gates is still required before any of those later actions.

## Exact input hashes

| Input | SHA-256 |
| --- | --- |
| [Correction proposal](candidate010-event-correction-001-proposal.md) | `d3c6f651c920094a26e5a7403bd9154693aa74b2a468538c3d7c1f50b00c854d` |
| [Event000](../plan031-progress-20260922/main-session-049-diagnostic-010-event-000.json) | `9c0a454ecfc84f4ff95f159bb8a6e0c92f0d42a360ff91f738fe19511e5e24f6` |
| [Event001, before correction](../plan031-progress-20260922/main-session-049-diagnostic-010-event-001.json) | `0210f36fc11d052ddf337ed747404098986f81246c1b1dcc886ada3758e758d2` |
| [Event002](../plan031-progress-20260922/main-session-049-diagnostic-010-event-002.json) | `1194d27ab7be408b4195607eae81bf95e3e36c481b6d5b02c4792b8d70d8bbb2` |
| [Event003](../plan031-progress-20260922/main-session-049-diagnostic-010-event-003.json) | `2d5bece0b496f037920cfe6ec6ff8f8d481d9fa53523ebd411e6e203f7b893a2` |
| [Identity request](../plan031-progress-20260922/launch-identity-049-diagnostic-010.json) | `c451dac9ecf0aae9fdeac6935ab7c1fff59edaea84dcb2f94782c284a772f6e7` |
| [Hash-readback return](candidate010-hash-readback-return-001.json) | `c099a8bef526b8793e00cd05de87be053a3f76872c96df7229600cf1adcee1b1` |
| [Earlier start-proof review](start-proof-review-001.md) | `3b907bcf2d2fff989b3894f233bab6d7ce0e625aa1f20f9b279795d252b2590a` |
| [Plan049](../../../plans/plan_049.md) | `89d1f634ad2407b02558ff9c030d4a4f12f8f4ab010c93e2cf532876564afe7e` |
| [Plan054](../../../plans/plan_054.md) | `91d0ac7191d944b8cf2175b74c74aff3d70d4dba4a530431f223cb8aab2df62d` |
| [Plan055](../../../plans/plan_055.md) | `18506f655e7a2c95492fa88a038c869a4c993fa06d3ba628725158eaea77242f` |
| [Plan056](../../../plans/plan_056.md) | `b757b31e867b199f874ab55165717bbe26ef992b5a0d8ebc18060e05afcbf8b1` |

The saved nested `write_stdin` wall-return values are **1.000977204**, **5.001497478** and **5.001611786** seconds for events001–003; the separate hash-readback result reports **0.000008685** seconds. These are tool-return wall measures, not CPU time or complete session duration. Gaps, candidate010 CPU/memory and the two old native sessions' resource use were not measured and remain unknown. This review used only file reads, standard-library JSON/SHA-256 and path checks plus `sha256sum`; no project import, target process/session interaction, test, launch, admission or source edit occurred. Individual reviewer command returns were about 0.2 seconds; total reviewer wall, CPU and memory use were not measured.

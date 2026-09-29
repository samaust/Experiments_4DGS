# Candidate015 pre-admission session-proof review 001

**Verdict: PASS for the exact saved `plan049-session-proof/v2` session-bound proof only.** This review clears treating the Candidate015 pre-admission proof as valid evidence for the registered Main tool handle 13761. It does not clear another poll, `ADMIT\n`, creation or use of an admission file, or a workload/test. Those require their independent current gates.

The reviewed proof is `docs/resolve-blocker/plan031-progress-20260922/main-session-proof-049-diagnostic-015.json`: 3,680 bytes, SHA-256 `3f15bb02b9ba3cf9c09cf2fffd3e461f3e23322e4455e2de9fb66b4d31677b82`. I invoked the frozen `session_proof()` validator in a read-only `python3 -B` process with the exact proof file record and its bound driver, identity-request, admission path, and reason. It accepted the proof and returned four events and handle 13761. I also independently checked the file bytes and raw receipts.

| Bound record | Bytes | SHA-256 |
| --- | ---: | --- |
| driver `launch-049-exec.py` | 29,818 | `bdf68e0eaef6648d4097c5f819527fff94573bacc202176309c5832a915f59b8` |
| identity request `launch-identity-049-diagnostic-015.json` | 38,932 | `de106cf3fe58052a74befb3407b7cc3b1b72f8ac801b188975227a367adaf42a` |
| event 000 `main-session-049-diagnostic-015-event-000.json` | 1,952 | `8764ac0b65a7f7964cd72c60710d551f62bc1e457a3fae973f36e9662bdfb5a1` |
| event 001 `main-session-049-diagnostic-015-event-001.json` | 5,030 | `886ba3e9507e65b702859d33cfaa934dfeb8bbe62c840d882e84b8a8f5468bf3` |
| event 002 `main-session-049-diagnostic-015-event-002.json` | 628 | `0e2f621fb4e6e0f5791841089ef317a1f34816fe6967c6d9d8d368f65045392d` |
| event 003 `main-session-049-diagnostic-015-event-003.json` | 626 | `8c580f1cbae1364638772bc321701ac398faefbea55fedbfe1d35f1bdda04b32` |
| user authorization | 1,572 | `6ee2d0f899c6ee20de96415079d9aa07900b51f2321ef37d20af5e7e171bd755` |
| correction | 17,149 | `e68129133349fbbecc25e725025c0cda833c7ab149aaacad0ff05ead4737cf91` |
| Plan054 | 3,689 | `91d0ac7191d944b8cf2175b74c74aff3d70d4dba4a530431f223cb8aab2df62d` |
| evidence amendment | 16,729 | `9a27dbb60afcf358409364987e0b74d219431e4b5a83652ac9c607f658426d84` |

The four canonical events have ordinals 0–3, roles `start`, `readiness`, `pre_admission`, and `at_admission`, and the required `exec_command`/`write_stdin` tool sequence. Each event's exact arguments and result equal its saved raw Main return (`candidate015-main-exec-start-001.json`, `candidate015-start-frame-send-001.json`, `candidate015-poll-002-raw.json`, `candidate015-poll-003-raw.json`; SHA-256 respectively `cac7aab4f7132183ab3844437bcd2833fab7a2564a7598bd97e96c8728a1e742`, `c01f31016facba316d9723f1c086677cade38ca8f6843bc523aa8ae17bd1aaaf`, `8452ad7f0d7c1d42cd9ffcf740a799af4ccf6a062ab431b78e41fe27c16ab43a`, `31ab0de952852bff050778995cee1aa9a1b92ea97aa2d4acf90c2011166ea8ba`). Every raw return supplies the same live session handle 13761 and has no exit code or error. Output hashes match the exact UTF-8 output; both mandatory polls used empty `chars` and returned empty output with the empty-string digest.

The send `chars` exactly equal the 1,828-byte `candidate015-start-frame-002.json` (SHA-256 `b66119dc56b73bfde011a79d01ff742a54b0faf781429fe7feed116b47e95912`): one JSON `plan049-main-start-frame/v1` object embedding the entire canonical event 000, followed by one LF. The readiness return is precisely that frame's PTY echo plus one `awaiting_main_admission` line. The latter matches the proof's admission path and identity-request file record, and its 424 UTF-8 bytes hash to `b3f3241522db9125372321ebd3c2c0ffe0cc84ef73d0fefd3b619cc28ac8836a`. The identity request itself has `plan049-prospective-identity/v1`, kind `diagnostic`, index 15, and the bound byte count and hash. Any PID inside that request is not used as Main tool-session identity.

UTC intervals are ordered and nonoverlapping: 10:09:10–10:09:16, 10:16:48–10:16:51, 10:20:22–10:20:30, and 10:23:14–10:23:22 on 2026-09-25. These are conservative outward bounds from the saved clock evidence, not claims of exact internal instants. The proof itself records `cross_namespace_kernel_verified: false`; this review does not infer cross-namespace kernel visibility or live-session state after the fourth saved return. The `admission_handoff` field specifies prospective `ADMIT\n` bytes and is not evidence that they were sent.

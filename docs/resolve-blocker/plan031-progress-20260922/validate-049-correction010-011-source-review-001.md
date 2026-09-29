# Independent Correction010+011 source review

Reviewer: `/root/blocker_review`. Date: 2026-09-23 UTC. This review used source, saved artifacts and standalone standard-library byte/AST inspection only. No project import, test, probe, runtime launch, session contact, source edit, production ledger/API access, GPU/model work or git mutation occurred. The two new review artifacts are the only writes.

**Plan readiness=true. Source launch readiness=true, narrowly for Main's next fresh diagnostic003 with these exact inspected hashes and the existing admission controls. Blocking static findings: none. Runtime acceptance=false/pending. Aggregate clearance is not supplied by this report.** This is the distinct source recheck required by Correction010 stage3 and Correction011. Diagnostic002 remains failed; its socket-creation retry establishes permission for that operation, not protocol or timing success.

## Authority and exact evidence

Paths below are relative to this report's directory unless stated otherwise. SHA-256 binds the reviewed bytes, not future edits.

| Evidence | SHA-256 |
| --- | --- |
| [Correction010](plan049-correction-010.md) | `ac9a4d3f392ad60dfa308622d25f0fe8c7dc07d0dab7139b8275be96050f9d6a` |
| [Correction011 / D49-2](plan049-correction-011.md) | `bdc431bc354e0c8cb11c0515d7ed1ebea4e529abf2f3ae9e65b9e280f1fb558e` |
| [Independent diagnostic002 report](validate-049-diagnostic002-report-001.md) | `0b086d431123eed3fa64a2f84a78aaa4396478b0bd7d1fc72ba69c214e4c310c` |
| [Independent Correction010 plan review](validate-049-correction010-plan-review-001.md) | `0d2c09ba43946e5b46bb213868d21123180f46b4e2396ce15c67b69ddb2732c2` |
| [Refreshed010 manifest](implement-049-correction010-artifact-manifest-002.json) | `bee4807246b6711e263dc1648ca6b3111f7e30ee437d508bef960bcf0f704fbe` |
| [011 manifest](implement-049-correction011-artifact-manifest-001.json) | `18947d9420391db384eb91ddce318662819a6d67c276b462709b00b47e624727` |
| [Combined009-to-final source diff](implement-049-correction010-combined-correction011-diff-002.patch) | `33578f13adad45b6930a6264dead9f5a62cf0fcb483de52d23a9c9d66f62ba17` |
| [Final source/method/declaration map](implement-049-correction011-after-ast-001.json) | `58cfd70ed4243f84fb9147d323d60437a03c09d4c3046022beef52185c48ede5` |
| [D49-2 exact assertion delta](implement-049-correction011-D49-2-assertion-delta-001.json) | `d0c9589fc5d5868525765ad879ef051346c83a17c32cf97ce218a1c4d6e8131a` |
| [Independent static audit](validate-049-correction010-011-static-audit-001.json) | `ba9dcd415dfee66028bab67df0d8c259b9c0c98a284190e40f3b4ecc63bcc7b5` |

The independent audit rehashed all256 distinct file records in the final two manifests: no byte-count/hash errors or conflicting records. The audit contains all78 exact current source records. Independently enumerated membership matches; only the following six members changed from the pre010 snapshot. The driver is separately bound.

| Repository-relative source | Final SHA-256 |
| --- | --- |
| `scripts/vipe_benchmark/s1_helper_session.py` | `04bdb09881519795217cc22c3e21f5662e4886e886f7a008de54f615ecca5ba7` |
| `scripts/vipe_benchmark/s1_validation_contract.py` | `7f9ec0b2938966216d00caaa22c2f8fe770207bf2c75fd7798e7fc1da5806d6b` |
| `scripts/vipe_benchmark/supervisor.py` | `444c47ae4d17f21ebd7f1045c2eaf21b9f749c31a3f9dfb9960ebcd6942739f7` |
| `tests/test_vipe_benchmark_s1_helper_fixtures.py` | `db17586a88f4e5cfbe88f902ce2cf5abede514868fb4aa97442fe0a211f892f9` |
| `tests/test_vipe_benchmark_s1_recovery.py` | `acf65b86b42ae2720bee17977ada9fe06a33f74ace2c01c7ef7cff09f95db5c7` |
| `tests/test_vipe_benchmark_supervisor.py` | `c85688d12fb3a64b1fe73a199fc56e1ef38288fb5a86d47471bec6dcb466f7e9` |
| `docs/resolve-blocker/plan031-progress-20260922/launch-049-exec.py` | `b858d3a3787537ed3f58c6167066740c5f5de885379e3591162edc5572d298b0` |

All72 other source members remain byte-identical, including `s1_evidence`, progress, runner/capture, clock, generic files and backend/runtime sources. All77 Python source members plus the driver parsed and compiled to memory without execution. All622 class-method normalized ASTs and ordered assertions were recomputed from current files and exactly match the final map. The249 collected methods,1028 ordered typed callbacks and59 literal declaration entries match009. This uses the already reviewed discovery contract; it is not a fresh runtime discovery receipt.

## Preservation and proof mechanics

Compared with009, ordered prior assertion sequences have exactly two removals, both in `HelperSessionTests.test_progress_closed_inventory_and_faults`, kind=deadline: `assertFalse(result['scan_complete'])` and `assertEqual(result['counts']['produced_lower_bound'],0)`. These are precisely D49-2. Every other prior assertion retains order and multiplicity. Independently replacing only the new deadline branch body with its pre011 body reconstructs the whole original method AST exactly.

The real public `e.reconcile_rows(..., deadline=0)` is still called. The replacement expects the exact original-work-deadline TimeoutError. Five scoped spies cover `_reconcile_rows`, input loading, candidate inventory, produced-row validation and qualification; each fails with AssertionError on entry and must have zero calls. The ordered suffix must be empty. The real public entry, operation/before gates, clock and memo cleanup are not replaced. No returned-result fabrication or contradictory-success expectation remains in this callback. Every other branch is unchanged.

The runtime start contract accepts only exact `require_escalated`, not default/omitted/alternate modes. It requires exact kind-specific justification `Run the reviewed Plan049 CPU-only <kind> after the exact AF_UNIX datagram socket retry succeeded.` and a list of exact strings `['exec', absolute_original_interpreter, '-B', fixed_R_driver]` as prefix_rule. The key set is exact; shell `/bin/bash`, login=False, repository workdir, tty=True, yield1000, positive exact-int max_output_tokens and canonical shlex-joined exec command remain enforced. The negative fixture's former invalid permission now becomes `use_default`; prior assertions/callback identities remain, with additional invalid justification/prefix cases inside the existing method.

Driver, contract and recovery fixture bind addenda001–011. Correction008 remains the specifically selected trust amendment (`addenda[7]`), never the last arbitrary addendum. Canonical command proof from009, actual same-session start/readiness/event/ADMIT correlation, session liveness checks, fresh source and authority hashes, source inventory, output identity, command/environment/stdin and admission binding remain. This does not elevate the deliberately session-bound008 proof into an independent cross-namespace `/proc` attestation. No new session-correlation bypass was found.

The ownership helper evaluates the intended local output/dispatch/ancestry/wrapper failures before the expensive complete graph validation. Every successful path still performs the full no-timeout launch, source-membership and fresh-byte validation before registry acceptance. The eight mutation fixtures project their canonical graph and dependent hashes/readiness transcript instead of being masked by an unrelated temp-path/hash failure; original target-specific regex assertions remain. This changes rejection order, not successful admission authority.

Original W/C and equality-is-late gates remain. The one-audit spawn change removes a duplicate pre-dispatch audit but leaves the actual common creation audit and post-audit/observer deadline immediately before the syscall. The supervisor post-installation gate changes its message only; the `>= run_deadline` predicate remains. The2s/1s scenario cutoffs,42 scenarios, six scripts and510/340/170 full obligations remain. No time/attempt cap is added or inferred; existing ≤8 charge,150GiB artifact and64MiB memo limits remain.

## Finding recovery and remaining observations

| Finding | Source conclusion and remaining runtime evidence |
| --- | --- |
| AF_UNIX EPERM | Exact fixed escalated launch contract is implemented. Socket creation succeeded in Main's authorized retry; full protocol remains unproved. |
| Eight ownership controls | Local predicates are reachable before unrelated graph rejection, canonical projections and positive baseline retained. Need collected results to establish each expected rejection. |
| Secondary JSON count | Exclusive-write interception now matches only `scenario-pure-secondary-secondary.json`; it no longer also matches the primary file. Original expected1 remains. |
| L08 | Duplicate audit removed; actual spawn-return PID/time now observed before existing .45 hold. Original .06/.12/.2 cutoffs and retained lower-bound assertions remain. Whether spawn reaches that boundary in time is still unproved. |
| L25/L26 and Plan046 | Actual reserve-descriptor predecessor is observed, one real creation audit checked, immediate-worker-launch error attribution repaired. Original .15/.3/.5 and boundary comparisons remain; runtime reachability remains unproved. |
| L24 | Actual disposable register/command/Ledger.reserve and captured clock replace the fabricated seq/hash fixture. Negative reservation uses actual sequence+1. No production ledger access is introduced. |
| L35 | Existing child inserts the absolute tests path for its fixture import using the original interpreter and process topology. Original2s assertion remains; bootstrap repair is not proof of timing. |
| L36 | State is initialized before fallible native creation; actual handle acquisition, startup primary, secondary failures, cleanup and persistent outcome are retained on failure. Session attributes used by this recovery are initialized before native creation. Original acquisition/state/timing assertions remain; actual acquisition is still unproved. |
| Closed inventory | D49-2 resolves the explicit assertion/entry-gate contradiction, exactly as authorized above. |
| Full-completion interpreter | Fixture preparation binds the real invoked spelling to its resolved trusted target, asserts original argv/provenance and manifest equality, then narrowly adapts only that spelling to the production guarded no-follow reader on the bound target. Re-resolution and bytes equality are checked with deadline gates. An arbitrary symlink alias is explicitly rejected. The actual runtime validator and all other evidence reads remain active; production `s1_evidence` is unchanged. This is an authorized fixture seam, not evidence that arbitrary production interpreter symlinks are supported. |
| P-family final outcome | Actual catch/final state, original and secondary failures, cleanup/ownership/reference/pointer and clock evidence are appended after finalization; the outer record uses them, or an explicit startup/preparation failure fallback. No success result is manufactured. Collection must demonstrate that these records persist on the relevant real failures. |

No inspected correction relaxes a prior timing expectation, substitutes a late reply, drops a collected control, bypasses the runtime guard wholesale, or changes scientific/backend behavior. Static repairs do not establish that these findings now pass. In particular, earlier diagnostic002 timing causality remains uncertain; removing duplicate work is not a measured latency result.

## Narrow next action

Main may prepare **fresh diagnostic003**, subject to actual vacancy/high-water, storage/resource, source-freshness and ownership reconciliation checks, and submit the exact escalated tool arguments. A new proof and live session are required;002 proof/admission may not be reused. Follow the existing pre-admission/at-admission polling, exact ADMIT, final wait/reap and permission-failure rules. Review diagnostic003's actual receipt/logs/outcomes before deciding the next stage.

The next unchanged collected supervisor diagnostic is justified specifically to resolve L08/L25/L26/L35/L36 startup/acquisition/timing, ownership-mutation reachability, escalated socket protocol, full-completion fixture qualification and durable P-family outcomes that byte inspection cannot establish. It is not a blanket assumption that all defects were environmental. A runtime failure stays a failure and requires its concrete evidence to be reviewed; no criterion relaxation follows from this readiness.

B1–B3 remain runtime-unproved. B4's static preservation and launch-contract aspects are supported for the bound bytes, but actual process ownership/resource reconciliation still depends on the next runtime records. Whole-tree CPU use for this review is unknown; no CPU total is invented. No operational time ceiling is applicable under the already authorized Plan049 state, and this report allocates no new resources or scope.

# Plan049 Correction015 source-scope addendum014 — independent plan review 002

**Verdict: NEEDS_REVISION for proposal SHA-256 `3ecb14bdb08223980be9df0b83e6ee3c26e89b10106b4385a6a74e17b1661d89`. No source-edit or runtime clearance.** I checked the corrected proposal independently against Plan049, Correction015, addenda011/013, audit002 and its independent review, review001 of addendum014, and current selected source. It resolves review001's three stated wording defects, but its path-domain/pre-edit patch gate still excludes another selected runtime command argument.

## Review001 corrections verified

- The addendum013 SHA-256 in “Inputs considered” now matches the observed bytes: `14398e0974258104018a366f5d9a9d653e69c9efb894baefe73b498542b1c78c`.
- The proposal now distinguishes an `attempt_root_path` exactly equal to the reserved output root, `attempt_path` strictly beneath it, and fixed reviewed `repository_path` values that exclude attempt-owned output. This accounts for the generated driver-to-capture output-directory argument and the intended repository entries, assuming every selected path slot is actually covered.
- A command/environment ceiling failure proved before reservation now makes no reservation or child and creates no fictitious unresolved child charge. Only uncertain append/readback or OS create outcomes retain the conservative unresolved charge. That matches addendum013 §4.
- The whole-ledger requirement now partitions existing events into disjoint enumerated classes, counts each once, and requires a concrete maximum ≤8,388,608 bytes. It preserves the 8 MiB cap and asks the later audit to bound each event kind, all coexisting failure/recovery branches and serialized field sizes. The proposed 16,384-byte executable/argv and 1,048,576-byte/4,096-entry full-environment ceilings are finite fail-closed upper bounds; they do not themselves establish that selected commands, operating-system limits or the journal fit.

## Remaining blocking path edge

`tests/test_vipe_benchmark_supervisor.py:18-33` is in the selected nine-suite aggregate. `SupervisorTests.setUp` creates `self.root` using default `tempfile.TemporaryDirectory()` without `dir=`, and `command(code)` passes `str(self.root/'output')` as an argv element to the real `run_worker → supervise → create_owned_process → Popen` path (`supervisor.py:445-447`). This generated output path is neither equal to the exact attempt output root, proven strictly beneath that root, nor a fixed reviewed repository module/test/selector/`sys.path` entry. Its directory is chosen at runtime by the default temporary-directory mechanism. Multiple existing selected `SupervisorTests` methods call `run_worker`; this is not merely L35's marker/release case.

Addendum014 §1 provides a counterfactual pre-edit patch-review exception only for L35's default `TemporaryDirectory()` at `tests/test_vipe_benchmark_supervisor.py:1657`. Under the corrected three-domain rule, a revised source audit cannot PASS while this additional selected command path is outside every domain. Narrowly revise the plan so the pre-edit exact-patch proposal/audit enumerates **every** selected runtime-created path slot, including `SupervisorTests.command`, and either (a) proves an explicitly authorized bounded domain and trusted root for each, or (b) reviews exact within-nine-path patches that relocate those paths beneath the verified attempt root. Keep source bytes unchanged until that independent audit and user/Main gates pass. The later exact-source review must then check the actual edited bytes, command rendering and preserved fixture semantics/deadlines.

## Remaining gate interpretation

The new host-limit sentence correctly requires checking each actual encoded argument/environment string and combined argv/environment length, including OS framing. Its final “limit ... smaller than the proposed ceilings” phrase should be applied to the relevant combined API limit, while individual strings are checked against their own per-string limit. A total 1,048,576-byte environment ceiling does not imply any one environment value is valid at that size. The later audit must use the selected host/API limits and reject an actual invocation that violates them; the numeric ceilings are upper bounds, not a promise that all inputs below them are OS-admissible. This is an implementation/audit check and does not resolve the path blocker.

The proposal otherwise keeps addendum013's independent template render comparison before reservation and OS creation, immutable complete environment handoff, final post-edit `-m` hashes, descriptor-bearing durable reservation/readback and uncertainty rules as future source obligations. It preserves the nine editable paths, 78 source members, 249 methods, 1,028 callbacks, original assertions/deadlines/cleanup precedence, addenda006/011 exact same-handle wait and owner rules, CPU-only serial work, `B+max(1,H)≤8`, 150 GiB artifacts, 64 MiB memo and the unchanged 8 MiB ledger cap. The stated sequence remains independent plan review, explicit user authorization, Main adoption, revised independent static closure with exact proposed patch and numeric full-ledger proof, then source edit, exact-source review and fresh preflight before any separately authorized diagnostic. The existing audit002 remains FAIL; this review does not certify any prospective source or runtime result.

## Exact reviewed inputs

All paths are repository-relative; hashes were independently recomputed from observed bytes.

| Input | SHA-256 |
| --- | --- |
| `docs/resolve-blocker/plan031-progress-20260922/plan049-correction-015-source-scope-addendum-014.md` | `3ecb14bdb08223980be9df0b83e6ee3c26e89b10106b4385a6a74e17b1661d89` |
| `docs/resolve-blocker/plan031-progress-20260922/plan049-correction-015-source-scope-addendum-014-independent-review-001.md` | `902aa0480b9aa4b7cb855715c13e0a17622c31865b555001ab8e9603714b0678` |
| `plans/plan_049.md` | `89d1f634ad2407b02558ff9c030d4a4f12f8f4ab010c93e2cf532876564afe7e` |
| `docs/resolve-blocker/plan031-progress-20260922/plan049-correction-015.md` | `a3242ed06131aa9ca00bc05180805c8d5bf5ea8d965919b92054154f10a00bab` |
| `docs/resolve-blocker/plan031-progress-20260922/plan049-correction-015-source-scope-addendum-011.md` | `18e0d807a074fdb11817251b459db54ea3b0725161222da824b86c5ebfe52d65` |
| `docs/resolve-blocker/plan031-progress-20260922/plan049-correction-015-source-scope-addendum-013.md` | `14398e0974258104018a366f5d9a9d653e69c9efb894baefe73b498542b1c78c` |
| `docs/resolve-blocker/plan031-progress-20260922/plan049-correction-015-transitive-source-closure-audit-002.md` | `bff30fce1eedaf7300ee7a43f9597ca7a4e47fc97230ad8914892de318707963` |
| `docs/resolve-blocker/plan031-progress-20260922/plan049-correction-015-transitive-source-closure-audit-002-independent-review.md` | `9d2b900e856e9ff00d0b0257b782adc18dc7a00a21e944914ce5b2a62ccb40b2` |
| `docs/resolve-blocker/plan031-progress-20260922/launch-049-exec.py` | `be9cdd762b866204eb77aa58e18ca8ed4e48b68df625313fda52610caa90bc1e` |
| `tests/test_vipe_benchmark_supervisor.py` | `c1f74f4fb121afb6a7639043a61fff81775b41e6de23ab3a66bfa039f7917188` |
| `scripts/vipe_benchmark/supervisor.py` | `2d04eea77a507392feda918c4003bd9ec599fe8d9325cb1e9feafdba143257ad` |
| `scripts/vipe_benchmark/s1_helper_session.py` | `c3326fe0c738e0180b42289f03c52ff8586e9eef86fd242dc3ea3a013a72e106` |
| `AGENTS.md` | `3d09a19b0bf8e4bfcf7c25f5b001a769f2cce372a425fc1dd1a14fc299ef620f` |

Activity was static document/source reading and hashing plus this review-artifact write. No project import/execution, test, fixture, pidfd or live-process operation, diagnostic, admission, aggregate, launch, or prompt access occurred. CPU, wall time, process-tree use, runtime/native behavior, and the finite whole-ledger maximum were not measured and remain unknown. **No implementation or runtime clearance is granted.**

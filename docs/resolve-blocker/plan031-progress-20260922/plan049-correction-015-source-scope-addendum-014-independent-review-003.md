# Plan049 Correction015 source-scope addendum014 — independent plan review 003

**Verdict: NEEDS_REVISION for the exact proposal SHA-256 `f29c7c742dbac278c5b78292650514fcc5bfa7a3c023f1256020e9e49e08730a`. No source-edit or runtime clearance.** I independently compared the frozen proposal with Plan049, Correction015, addenda011/013, audit002 and its independent review, and addendum014 reviews001/002. The earlier path-domain and authority defects are repaired, but one pre-edit evidence requirement asks for bytes that only exist at runtime.

## Resolved findings

The controlling addendum013 hash is exact. The proposal separates `attempt_root_path`, `attempt_path`, fixed `repository_path`, and provenance-bound `fixture_temp_path`; it explicitly covers the capture output root, L35 marker/release, `SupervisorTests.command`'s `self.root/'output'`, nested worker repository paths, direct scripts and other selected temporary-derived slots. The fixture domain captures the random path actually returned by a retained `TemporaryDirectory` object, binds its callsite/object and canonical base, and rejects a merely nearby host-temp path. The revised pre-edit audit no longer assumes a source relocation patch. Each selected dynamic source still needs independent audit proof and a pre-create renderer; this plan review does not certify such proof.

The 16,384-byte executable/argv ceiling and 1,048,576-byte/4,096-entry complete-environment ceiling are finite, fail-closed input bounds. Definite pre-reservation rejection creates no child or new reservation; uncertain append/readback or create outcomes retain the prescribed charge. The plan still requires individual and combined OS argument/environment limits to be checked, immutable complete environment handoff, exact post-edit `-m` hashes, independent render comparison at both create boundaries, and a descriptor-bearing durable reservation. Its event arithmetic counts disjoint event classes once, includes coexisting failure/recovery branches and serialized framing, and requires a concrete whole-ledger maximum ≤8,388,608 before source editing. No numeric result or implementation is claimed here.

## Blocking pre-edit/runtime evidence conflict

Section 5 requires the revised independent static closure audit **before any source edit**. Section 4 says that same source-closure artifact “must disclose the **actual canonical-render byte sizes**.” Selected slots include paths returned later by `TemporaryDirectory()` with a random suffix (`tests/test_vipe_benchmark_supervisor.py:18-33,1657-1666`). Their exact rendered argv/inline-program bytes and lengths do not exist at the pre-edit audit. Addendum013 deliberately separates a static, source-bound template/slot proof from a runtime comparison of the concrete rendered command before reservation and OS creation. Requiring actual runtime-render sizes in the pre-edit artifact recreates the circularity the amendment is meant to resolve.

Revise §4 to require the pre-edit audit to disclose exact template/static-field sizes, finite maximum encoded lengths for every dynamic slot and command, and the numeric worst-case event/whole-ledger proof. Require each later command-authority record and reservation to carry the **actual** canonical-render size/hash for that invocation, verified against the independently rendered bytes before reservation and immediately before the OS create. The exact-source review can then check that the implementation enforces those bounds and preserves the planned input/failure rules. A dynamic rendered size cannot be reported as a historical fact before its owner object and path exist.

The proposal otherwise preserves the nine editable paths, 78 source members, 249 methods, 1,028 callbacks, CPU-only serial work, `B+max(1,H)≤8`, 150 GiB artifact, 64 MiB memo and unchanged 8 MiB ledger caps, all original assertions/behavioral deadlines and cleanup precedence, and addenda006/011's same-handle wait/owner replay rules. Its sequence remains independent plan review, explicit user authorization and Main adoption of the exact hash, revised independently reviewed static closure and numeric cap proof, source edit, distinct exact-source review, and fresh preflight before any separately authorized diagnostic. This review grants none of those later clearances.

## Exact reviewed inputs

All paths are repository-relative; SHA-256 values were independently recomputed from observed bytes.

| Input | SHA-256 |
| --- | --- |
| `docs/resolve-blocker/plan031-progress-20260922/plan049-correction-015-source-scope-addendum-014.md` | `f29c7c742dbac278c5b78292650514fcc5bfa7a3c023f1256020e9e49e08730a` |
| `docs/resolve-blocker/plan031-progress-20260922/plan049-correction-015-source-scope-addendum-014-independent-review-001.md` | `902aa0480b9aa4b7cb855715c13e0a17622c31865b555001ab8e9603714b0678` |
| `docs/resolve-blocker/plan031-progress-20260922/plan049-correction-015-source-scope-addendum-014-independent-review-002.md` | `6a77c10d1407509e5e142fa1ce63d161d9bf556f7a7495fabf5a0a3dc24cc783` |
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

Activity was static document/source reading and hashing plus this review-artifact write. No project import/execution, test, fixture, pidfd or live-process operation, diagnostic, admission, aggregate, launch, or prompt access occurred. CPU, wall time, process-tree use, runtime/native behavior, and the finite whole-ledger maximum were not measured and remain unknown. **No source or runtime clearance is granted.**

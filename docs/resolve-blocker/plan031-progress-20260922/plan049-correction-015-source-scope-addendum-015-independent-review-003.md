# Plan049 Correction015 source-scope addendum015 — independent plan review 003

**Verdict: NEEDS_REVISION for exact proposal SHA-256 `ed733c7a9c7adf04841c2bfd59a6b8be72a31b8ca0b054d32db84001f74707de`. No source-edit or runtime clearance.** I reviewed the current proposal against Plan049, Correction015, addenda001/011/013/014, addendum015 reviews001/002, audit003 and its independent review, and the selected driver/capture source. The prior first-mutation and OS-limit ambiguity is resolved. The remaining path taxonomy still misclassifies fixed authorities outside `R` and conflates readable historical proposals with adopted launch authority.

## Blocking findings

1. **Fixed authorities outside `R` need a valid domain.** The proposal says `AGENTS.md` and `plans/plan_049.md` are canonical `repository_path` slots. Addendum014's `repository_path` definition covers fixed project modules, test files, direct-script selectors and `sys.path` entries; neither document is in that class. Addendum015 does not explicitly extend that definition. Give these two exact, hash-bound documents a closed external-authority domain or narrowly amend `repository_path` to include only the two named files with their exact expected hashes. Keep their authority role distinct from executable/module path slots, attempt output and run evidence.
2. **Separate the readable Table 1 set from the adopted authority chain.** Table 1 includes addenda004/005 and 007–010/012, which the earlier source-scope chain treats as historical rejected or superseded proposals rather than adopted authority records. The current driver authority list at `launch-049-exec.py:228-231` includes Corrections001–015 and addenda001–003/006, not all Table 1 entries. The table may be a closed *read-only comparison-file* allowlist, but calling it the “complete current direct-`R` authority set used by the selected launch path” could cause rejected proposals to be admitted as operative authority. Name the two roles and give the adopted ordered path/hash/byte chain a separate exact rule; unused historical entries must never satisfy an adopted-record requirement. State how addenda011, 013, 014 and this addendum015 enter the chain after their respective approval/Main adoption and exact-source review.

## Review002 findings checked

I independently rehashed every explicit SHA-256 row in Table 1; each matches the observed file bytes. The current proposal's own row is necessarily external to its bytes, and this review binds it to `ed733c7a9c7adf04841c2bfd59a6b8be72a31b8ca0b054d32db84001f74707de`. Its runtime adoption record must use that exact value rather than a self-derived hash or placeholder. The table now has explicit basenames and no wildcard expansion. The current-attempt evidence grammar lists exact candidate-index families for identity, admission, note, driver logs/start, ledger/lock, session proof/events and Main start/terminal; the revised audit must still verify each actual writer/reader and event ordinal. Evidence, authority and `R/status.md` names are disjoint in the stated grammar, and evidence vacancy applies only at creation/reservation; later readback verifies the exact existing file.

Section 4 now explicitly supersedes addendum001's sidecar-first wording for read-only prechecks. The driver obtains fresh high-water/index data by read-only enumeration/parsing in `R` and host limits from in-process read-only OS interfaces; no helper process is authorized. It performs no mutation, child creation or admission until the exclusive sidecar bootstrap is created, fsynced and read back as the first filesystem mutation. A failed precheck creates no sidecar, keeps the exact H charge and requires Main's exact returned-handle retirement. This is a coherent prospective sequence; the later static audit and source review must prove its safe handoff and implementation.

Section 2 now compares each actual encoded `key=value\0` and argv string with the per-string limit, and the combined rendered vector plus overhead with the combined host limit. The 16,384-byte command and 1,048,576-byte/4,096-entry environment ceilings remain independent policy limits; the observed 131,072-byte Linux per-string limit does not automatically reject all environments below the aggregate ceiling. Missing/unsupported host metadata fails closed. No host admission or runtime check was performed for this review.

Binding each candidate's exact `d(index)` and recomputing the projected bootstrap/whole-ledger size per attempt avoids an arbitrary operational attempt-count cap. The 16,384-digit Main-session-handle ceiling is a finite ledger field bound with exact-handle retention on rejection; the future audit must verify exact transport, parse and serialization up to any accepted width or fail closed on unsupported forms. Section 3 remains a valid **future** gate: full event schemas, finite labels/identities, source-derived creator counts, one-shot operation-key multiplicities and coexisting failure branches must yield one numeric nonoverlapping whole-ledger maximum ≤8,388,608 bytes. Neither audit003 nor this proposal provides that number, so source closure remains FAIL.

The proposal otherwise preserves nine editable paths, 78 source members, 249 methods, 1,028 callbacks, all original assertions/behavioral deadlines/error precedence, CPU-only serial work, `B+max(1,H)≤8`, 150 GiB artifacts, 64 MiB memo, no operational duration cap and the existing 8 MiB ledger limit. It keeps the required independent plan review → explicit user authorization/Main adoption → independently reviewed read-only static closure and numeric proof → source edit → distinct exact-source review/fresh preflight → separately authorized diagnostic sequence. No later gate is passed by this review.

## Exact reviewed inputs

All paths are repository-relative; hashes below and every explicit Table 1 row were independently recomputed from observed bytes.

| Input | SHA-256 |
| --- | --- |
| `docs/resolve-blocker/plan031-progress-20260922/plan049-correction-015-source-scope-addendum-015.md` | `ed733c7a9c7adf04841c2bfd59a6b8be72a31b8ca0b054d32db84001f74707de` |
| `docs/resolve-blocker/plan031-progress-20260922/plan049-correction-015-source-scope-addendum-015-independent-review-001.md` | `8321dba158e3f14a3fbed12ee3492ca8f1f852693b61046d5247b990e1f060bc` |
| `docs/resolve-blocker/plan031-progress-20260922/plan049-correction-015-source-scope-addendum-015-independent-review-002.md` | `d16b489a753f9917c5eb8ed063194a36f7df07295a60cde059e39d0cbfaa3903` |
| `plans/plan_049.md` | `89d1f634ad2407b02558ff9c030d4a4f12f8f4ab010c93e2cf532876564afe7e` |
| `docs/resolve-blocker/plan031-progress-20260922/plan049-correction-015.md` | `a3242ed06131aa9ca00bc05180805c8d5bf5ea8d965919b92054154f10a00bab` |
| `docs/resolve-blocker/plan031-progress-20260922/plan049-correction-015-source-scope-addendum-001.md` | `f08fad270dcea9596d1a4c45a41d13f2f5675f7d51fe464699a1ec4046f0b45e` |
| `docs/resolve-blocker/plan031-progress-20260922/plan049-correction-015-source-scope-addendum-011.md` | `18e0d807a074fdb11817251b459db54ea3b0725161222da824b86c5ebfe52d65` |
| `docs/resolve-blocker/plan031-progress-20260922/plan049-correction-015-source-scope-addendum-013.md` | `14398e0974258104018a366f5d9a9d653e69c9efb894baefe73b498542b1c78c` |
| `docs/resolve-blocker/plan031-progress-20260922/plan049-correction-015-source-scope-addendum-014.md` | `0d630af7c3da1274efc78fb30d859212d3cedbf851bbeabc814d0865ccb82ea1` |
| `docs/resolve-blocker/plan031-progress-20260922/plan049-correction-015-transitive-source-closure-audit-003.md` | `7b691be6e86b999171fee345e1a2d76ef13cb101f8a98148c3ba8f15a3bbdfdc` |
| `docs/resolve-blocker/plan031-progress-20260922/plan049-correction-015-transitive-source-closure-audit-003-independent-review.md` | `fbc1d1a89b24684deca7a6711a03d75e58fa329d92007cc6c161f1c57eba17d7` |
| `docs/resolve-blocker/plan031-progress-20260922/launch-049-exec.py` | `be9cdd762b866204eb77aa58e18ca8ed4e48b68df625313fda52610caa90bc1e` |
| `docs/resolve-blocker/plan031-progress-20260922/implementation-dispatch-049.json` | `d7177d2dae0d553321863481af72647f210557087c54c3b802c8317f572937be` |
| `docs/resolve-blocker/plan031-progress-20260922/implementation-status-049.md` | `7a3085aed5b7bfcd5ace290d91d875feb738da0764319c8acde894647fb4f0e0` |
| `docs/resolve-blocker/plan031-progress-20260922/authorization-049.md` | `9ba97b6487d459eea268c1e0d0bac5000a1d5601162ec490ddb2533ec4efc31f` |
| `docs/resolve-blocker/plan031-progress-20260922/authorization-049-ancestor-process-001.md` | `734fc8fc67f2cc7f60ead6eba279b797abff47bbf32602cf5106e07ef540605d` |
| `AGENTS.md` | `3d09a19b0bf8e4bfcf7c25f5b001a769f2cce372a425fc1dd1a14fc299ef620f` |

Activity was static document/source reading and hashing plus this review-artifact write only. No project import/execution, test, fixture, pidfd or live-process operation, diagnostic, admission, aggregate, launch or prompt access occurred. CPU, wall time, process-tree use, runtime/native behavior and the numeric whole-ledger maximum were not measured and remain unknown. **No source or runtime clearance is granted.**

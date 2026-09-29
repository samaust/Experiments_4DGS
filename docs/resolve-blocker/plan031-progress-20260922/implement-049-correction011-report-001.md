# Plan049 correction011 implementation — D49-2 static handoff

Implemented the explicitly authorized deadline callback correction. No remaining source-level contradiction is identified in this callback. **Independent source recheck and runtime acceptance remain pending; launch readiness is not claimed.** No test/project import, probe, launch, session contact, admission or commit occurred.

The real public `e.reconcile_rows(output, fixture['request'], deadline=0)` remains. It now must raise message-specific `TimeoutError('progress original work deadline')`. Scoped fail-fast spies observe `_reconcile_rows`, `e.input_loader`, `p.candidate_inventory`, `e.produced_row`, `e.qualify_row`; any entry raises AssertionError, not the expected timeout. Each spy count must be0 and ordered suffix must be empty. Actual `reconcile_rows`, `operation`, `before`, clock and local memo cleanup remain intact.

Exactly the two authorized returned-result assertions were removed. The D49-2 artifact saves old/new normalized method/branch ASTs and full source context. Replacing only the new deadline body with the old one reconstructs the entire original method AST exactly, proving every other branch/assertion remains unchanged. The literal kind=deadline declaration, exact typed callback ID, ordering, fixture/output/request, numerical dimensions and literal deadline0 remain.

Mechanically extended the three existing driver/contract/recovery-fixture addenda lists from001–010 through011 under correction011's authority-bookkeeping scope. No permission/proof/transport/production behavior changed. Correction008 remains the named session-proof trust amendment; require_escalated-only mode and exact justification/prefix remain.

Static compile/AST and scoped diff checks pass. Exact78 source membership,622 class methods,249 collected methods,1028 typed callbacks and literal declarations/order remain. Ordered assertion preservation has exactly the D49-2 two-expression removal; all prior exceptions remain historical. Other than the one callback and three mechanical list extensions, correction010 source bytes remain unchanged. The full final snapshots and map retain every correction010 edit for distinct review.

Correction010's closed-inventory authorization blocker is resolved in source. Its remaining timing/acquisition/bootstrap/full-completion/P-outcome claims are still source-inspected only and must be assessed by the independent reviewer, then exercised through Main's authorized collected execution. No new source-level blocker was discovered in this narrow edit; this is not evidence that all runtime findings pass. Diagnostic001/002 history remains unchanged.

Current supervisor test SHA-256: `c85688d12fb3a64b1fe73a199fc56e1ef38288fb5a86d47471bec6dcb466f7e9`.
D49-2 delta SHA-256: `d0c9589fc5d5868525765ad879ef051346c83a17c32cf97ce218a1c4d6e8131a`.

Measured snapshot-to-report interval: 124.301875 wall seconds, from 2026-09-23T17:36:51.959418+00:00 / monotonic 78373.602512907 to 2026-09-23T17:38:56.261291+00:00 / monotonic 78497.904387762. Earlier inspection overhead and whole-tree CPU time unknown. No operational ceiling.

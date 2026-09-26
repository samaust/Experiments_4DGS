# S1 recovery — iteration 19 PLAN

PLAN019 under [Plan058](../../../plans/plan_058.md) continues Review018 R18-1 from the committed Plan057 measured milestone (commit `343d067`, [assessment046](assessment-046-implement.json)): (a) launch the unchanged whole aggregate on the committed source as the first IMPLEMENT exec and retain the measured result; (b) implement F1.2 work-deadline extension through the named compound operations; (c) implement F5.3 P06 original-primary preservation and F5.4 bounded child boundary traces through already-permitted seams; (d) re-verify with one focused diagnostic and, if the launch inequalities allow, one final aggregate on the updated source.

Fresh allocation:7200 wall seconds,6000 source/test cutoff,1200 handoff reserve; at most4 focused120-second and2 whole-aggregate300-second launches; existing42 scenarios and6direct scripts only; B+max(1,H)≤8; zero GPU/model/production work; no old allocation transfer. The Plan057 allocation was closed at its budget with the whole aggregate unlaunched (launch inequality failed); this plan's first exec is that aggregate on the committed `343d067` source.

Deferred (recorded continuation, not dropped): F3 callback-relevance rework and F4 state/provenance/parser/cancellation coverage rework go to iteration20; then Plan049 owned-environment strict acceptance.

Environment record unchanged: this harness has no Codex PTY session tools, so the Plan049 owned-root launch and its 14 owned-root cases are environment-blocked; no session-proof evidence is synthesized; no owned-path assertion weakened. Validation uses the unchanged timeout-mode capture; the milestone gate covers all non-owned cases and strict zero-error acceptance remains the later owned-environment gate.

Source baseline advances from `21e3d9e` to committed `343d067` (stages F1.1 clock ordering, s1_progress primitives fast path, contracts direct static comparison); IMPLEMENT recomputes the78-member contract source manifest as the Plan058 baseline. S1-1/S1-4 narrowly met; S1-2/S1-3 unmet. Main owns status/git; no GPU/model/production work.

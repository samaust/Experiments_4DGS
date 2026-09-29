# Plan049 correction007 — stop on unresolved session/process identity

Prepared 2026-09-23 UTC. This append-only correction records a runtime admission blocker and a conditional recovery requirement. **It does not authorize admission, source changes, a new observer/process/topology, or weaker identity proof.** Plan049 and corrections001–006 remain unchanged. Main owns jobs, stop/cleanup, status, subsequent dispatch and acceptance.

## Observed blocker and attempted launch

Main prepared diagnostic049-001 at `2026-09-23T14:04:40.596695+00:00`, monotonic `65642.2397888`, in [main launch record](main-launch-attempt-start-001.json). Its command is:

```text
exec /home/auss/git_repos/samaust/Experiments_4DGS/.local/envs/stg-colmap/bin/python -B /home/auss/git_repos/samaust/Experiments_4DGS/docs/resolve-blocker/plan031-progress-20260922/launch-049-exec.py diagnostic 1 'Plan049 correction006 complete collected controls'
```

Main reports the sole driver is waiting for admission in tool session **68521**. The saved [identity request](launch-identity-049-diagnostic-001.json) reports root boot ID `83359f83-d706-4b7b-8873-f5933bd41054`, PID **2**, PPID **1**, PGID **1**, start ticks **6564892**, and one matching thread. Its namespace-visible ancestor is PID1/start_ticks6564891, terminating at PPID0. Main reports a separate inspection shell sees PID **2** with start ticks **6572909**. These are different process identities; matching the numeric PID does not establish the driver identity. Different per-exec PID namespace views are the reported explanation. Namespace identifiers and a trusted translation have not been independently established here.

The session handle and second-shell comparison above are explicitly inherited from Main's handoff; the planner inspected the identity file but did not repeat the process inspection or contact the waiting session. Main must preserve its actual tool command/start/session outputs and exact comparison, including any inspection command/error, in durable execution evidence. The preparation record's `state: prepared; no driver process launched yet` is historical, not the current session state.

The inspected driver publishes the prospective identity then reads its existing stdin, requiring exactly `ADMIT\n` before reading an admission and execing capture. The reported wait is **pre-admission**, not a completed focused check, a passing capture or a receipt. Preserve this attempted driver launch and all elapsed time; do not erase it because capture has not started. Do not infer final exit, no live process, cleanup success or fresh capacity from the absence of a capture receipt. Main must record the terminal tool outcome and retirement separately.

## Capability investigation and decision

The currently exposed `exec_command` schema returns an opaque `session_id`, output and completion metadata. Its input does not select an existing session or PID namespace. `write_stdin` routes bytes/polls to a session handle; it does not return host PID, namespace inode, pidfd, process ancestry or a trusted session-to-kernel mapping. The available-tool catalog exposed no process-identity attestation or namespace-join tool. An official OpenAI documentation search/open did not establish such a supported capability in this environment; this is a bounded negative finding, not proof that no host implementation could provide one. The fetched [official model guidance](https://developers.openai.com/api/docs/guides/latest-model) supplies no attestation relied upon here.

**No verified current mechanism meets the unchanged independent Main admission requirement. Do not admit.** The driver's own identity file plus its stdout/session association is self-report and transport correlation, not an independent kernel identity observation. A challenge/nonce echoed by that same driver does not fix that distinction. Neither a repeated PID number, a guessed host PID, a different process's `/proc/2`, namespace-local PID1, nor an admission copied from the driver may substitute for the missing proof. The waiting stdin accepts admission text, not arbitrary shell inspection; do not send shell commands or `ADMIT` to experiment.

This investigation found a platform-capability/evidence blocker, not a demonstrated approval-review rejection. No new permission-failing command was executed by Plan; no missing allow rule is established. A scoped allow rule alone cannot manufacture a session/PID mapping. Do not repeatedly retry through different tools, namespace-enter, inspect unrelated host processes or change execution configuration to evade a restriction. Any genuinely required access operation still follows AGENTS.md's one-safe-escalated-retry and stop policy.

## Conditional recovery option and authorization boundary

Preferred recovery preserves the existing process topology and proof: the platform/host supplies a **trusted association of the exact live tool session to its kernel process and PID namespace**, or a supported independently authenticated observation channel in that namespace. It must originate outside the driver being admitted. Before relying on it, independently verify the mechanism and bind:

1. Session68521 (or a separately recorded fresh session), tool command/start and lifetime to the actual root; boot ID plus PID namespace identity/translation, PID/start ticks/PGID, stable thread identities and full terminated ancestry.
2. Exact current driver/plan/addenda/dispatch/status/authorization/source hashes, output paths and no-timeout command; any namespace translation must preserve source and descriptor provenance and not merely equate local PID numbers.
3. All task-owned threads, wrappers and descendants with live `B+max(1,H)≤8`, plus retained unresolved ownership and definitive retirement. The platform attestation must make clear which namespace boundaries limit visibility; it cannot silently exclude owned work outside the visible tree.
4. Fresh before/after observations and failure on stale, missing, ambiguous or substituted identity; the distinct validator independently accepts the evidence before Main sends admission.

This is a required capability specification, **not an implemented or verified solution**. If satisfying it requires a host/tool change, new observer/helper/process, namespace entry, different execution topology, broader inspection access, or trusting driver self-report instead of independent observation, stop dependent execution and obtain explicit authorization for a concrete revised design first. Such a design needs a new append-only plan, exact scope/proof changes and independent validation; generic “continue” cannot establish missing platform facts. Main should request the trusted host capability. If an alternative becomes technically supportable, prepare its concrete design within authorized planning before requesting the specific scope/proof amendment; do not ask the user to approve a fabricated identity match.

Until then Main keeps admission blocked and handles the existing driver through its known session channel under the owned-job stop policy, saving actual termination/cleanup evidence. A current waiter cannot be assumed retired and PID2 in another session must not be signaled as though it were the waiter. This planner performs no stop/write to the session; Main owns that action.

## Preserved invariants and evidence

Retain all Plan049 no-operational-timeout/no-attempt-ceiling authorization, original W/C and equality-is-late semantics, exact78 sources/249 methods/1028 callbacks, 42 scenarios/six scripts/full510/340/170 guards, unchanged scientific scope, ≤64MiB call-local memo, 150GiB storage cap, one active subagent and all prohibitions. No GPU/device/model/production/real-ledger/setup/download/scientific work, no prompts, no source edits or launch by Plan. B1–B3 are not accepted and B4 remains unverified; correction006's static readiness did not establish platform runtime admission.

| Inspected evidence | SHA-256 |
| --- | --- |
| `main-launch-attempt-start-001.json` | `83db2e0355e2a9e8a29faa792bff2a1f3d746ab1aa07eb3d731b601bad161849` |
| `launch-identity-049-diagnostic-001.json` | `081e0e8f285ebc606c7fcf530f91588a4dfd94d4bdeeda0c67e42c0456929991` |
| `launch-049-exec.py` | `ccdcdfadbcc45a4b740d1ec9352e3cfba17a9f8ed3ccebb814183322134d24b7` |
| `validate-049-correction006-report-001.md` | `ee3dea5fc1f9a1327c4c19a942f856517c02320447f7d8a1f2c66922e2859bfc` |

Planning's first observed UTC was `2026-09-23 14:09:57 UTC`, after initial commentary; precise earlier start is unknown. Main records full stage/handoff elapsed in its duration journal. There is no operational ceiling under Plan049; no duration or capability is assumed free or zero.

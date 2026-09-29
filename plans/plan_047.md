# Plan 047 — Complete deadline-safe, independently owned S1 progress

Implement Review017 R17-1 as one cohesive CPU milestone. Close R17-F1–F8 and retain R17-E1 explicitly: enforce the original work deadline at each expensive operation, anchor the actual invocation independently, finish acknowledged authority/recovery and finite mutation coverage, and preserve complete original failure evidence. This advances R9-4 and prerequisites for S1-2/S1-3; it preserves S1-1/S1-4. It does not complete the main objective, production admission, calibration or full R9-5.

The authoritative [objective](../docs/continuous-improvement/plan031-s1-recovery-20260919/objective.md), [Review017](../docs/continuous-improvement/plan031-s1-recovery-20260919/review-017.md), [assessment041](../docs/continuous-improvement/plan031-s1-recovery-20260919/assessment-041-review.json), full [review observations017](../docs/continuous-improvement/plan031-s1-recovery-20260919/s1-recovery-review-observations-017.json), [Plan046](plan_046.md), completed handoff016, limitations016 and remaining-gates016 bind the baseline. C denotes that run directory. The machine-readable tables and exact callback IDs in [plan observations017](../docs/continuous-improvement/plan031-s1-recovery-20260919/s1-recovery-plan-observations-017.json) are normative components of this plan, not execution evidence.

Read AGENTS.md and `/home/auss/.codex/skills/continuous-improvement-loop/SKILL.md`. Never read `prompts`. Main owns status, dispatch, staging and commits. One fresh sequential Astra IMPLEMENT agent must complete its artifacts and final response without delegation; main waits for full completion before inspection/next dispatch.

## 1. Baseline, preservation and allowed changes

HEAD is `ebf9d9ad39c25b5732fadefcdc36cb71e0bde613`. Start from the uncommitted/unaccepted Plan045+046 partial: 78 current source members and both immutable ten-source sets `s1-recovery-partial-source-015` and `-016`. Current source matches -016. Plan046's final aggregate has 237 methods, 526 callbacks, one failed method/six failed subtests, zero errors/skips/discovery errors, 220.76279841200449 inner / 220.89489405300992 outer seconds. All 42 scenarios, six direct scripts and full synthetic controllers passed narrowly. There is no passing current aggregate or Plan045/046 commit.

Plan046 consumed three focused/two aggregate launches and 2554.3126572030014 seconds through complete handoff; its source/test end was 2076.076476647999 seconds. Its allocation is closed; unused time grants no attempt or transfer. Preserve the initial absent-`python` command and missing preceding clock sample. Historical strict acceptance of Plans041/043/044/045/046 remains false permanently. Preserve earlier P31-5, L31, outer-completion, thread/CPU and whitespace exceptions. Do not overwrite old failed/successful receipts, stderr, audits or partial source copies.

Preserve all current methods and assertions and all 526 logical cases with only the six explicit declaration changes in §3. Review's 461 committed test-method assertion maps cover a broader file set than the collected 237. Preserve the historical reported 840 versus independently counted 836 assertion calls +2 bare asserts =838 in test methods (891+5=896 across all class methods); do not fabricate reconciliation.

Allowed implementation files: `scripts/vipe_benchmark/{s1_progress,s1_evidence,stages,s1_recovery,s1_cpu_helper,s1_helper_session,supervisor}.py`, existing `tests/test_vipe_benchmark_{supervisor,s1_helper_fixtures,s1_recovery}.py`, and a new C iteration017 exec driver. A minimal `scripts/basketball_vipe_worker.py` change may carry the original deadline/context/reference through existing calls. Put shared bounded I/O/counter/parser helpers in `s1_progress.py`, avoiding edits to unrelated generic APIs. New pure methods belong in existing `HelperSessionTests`; the existing barrier method is strengthened as described below. Necessary observation plumbing in existing full-controller and scenario helpers preserves their assertions and scenarios.

Capture, runner, validation contract/cache/discovery/order, s1_clock, native scientific configuration and backends remain byte-identical. Preserve boxes, phrases, scores, thresholds, weights, preprocessing, SAM refinement, tracking and verified S0 token-score assignment. No admission/ledger-policy change, new production path, extra observer/thread/process/helper, model forward, GPU or standalone probe is authorized.

## 2. New allocation and launch protocol

**Plan047-R17-1** is a fresh development-stage allocation under the continuous-improvement-loop skill's standing approval. Main compares the saved plan against original ceilings, records its dispatch and approved scope, then dispatches IMPLEMENT without a routine budget question when it fits. This never transfers an old allocation or supplies live authorization.

The first IMPLEMENT shell command uses available `python3` standard library to take UTC and monotonic readings before any repository inspection and exclusively saves `iteration-017-timing-start.json`. All inspection/editing/preparation, failed commands, tool/permission waiting, launches, cleanup, audits and full handoff count toward **5400 wall seconds**. Source/test work ends by **4800 seconds**, leaving **600 seconds** for complete evidence/handoff. A first-command exception is recorded honestly, never repaired by a retrospective clock.

| Resource | New plan-specific ceiling |
| --- | --- |
| Focused collected invocations | At most 3; unchanged HelperSessionTests selector; complete outer timeout 120 seconds each. |
| Full aggregates | At most 2; unchanged complete outer timeout 300 seconds each; reserve one for final current-source acceptance. |
| Existing real scenarios | Exactly L01–L36 and P01–P06, serial: each 2 execution +1 safety-cleanup seconds; 126 seconds combined within tighter outer timeout. Zero new real-child scenarios. |
| Existing direct scripts | All six serial; 10 execution +2 cleanup seconds each; 72 combined within aggregate. |
| CPU ownership | B + max(1,H) <=8, every actual task-owned thread included. |
| GPU/device/model/production | Zero invocations, probes, evaluations, production controllers, dry runs, ledger APIs/writes or production job directories. |
| Setup/download/smoke/scientific/profiling/standalone probes | Zero. New pure cases run only inside allocated collection. |

Read time after all durable launch preparation and immediately before exec. Focused fit requires elapsed+120+300<4800; nonfinal aggregate elapsed+300+300<4800; final aggregate elapsed+300<4800. Equality cannot launch. A second aggregate requires a recorded source change or concrete invalidating concern; no unchanged passing timing rerun. Any post-pass source change invalidates acceptance and needs an available justified aggregate. Historical 220.9-second timing is not a guarantee of fit. Attempts and time are separate: every launched invocation consumes a slot even on early failure/timeout; an unlaunched note retires its index only. No index/output reuse or omitted failed work.

Use normal task-scoped escalated datagram validation from the outset, based on the resolved old EPERM and standing permission evidence. No new permission blocker or missing allow rule is known. Any new suspected sandbox/permission failure follows AGENTS.md: one safe exact-operation escalated retry if not already escalated, after checking partial effects; then stop affected work on denial/unavailability/failure and report exact command/error and definite versus suspected denial. No socket/configuration substitution or repeated retry.

Fresh `C/s1-recovery-launch-017-exec.py` uses shell `exec` then Python `execve` into unchanged capture. Capture runs `.local/envs/stg-colmap/bin/python -B -m vipe_benchmark.s1_validation_capture <absolute new directory> --timeout 120|300`, with `--diagnostic` only for focused. Child argv remains `.local/envs/stg-colmap/bin/python -B -`; exact stdin comes from unchanged contract, including final newline. All OMP/OPENBLAS/MKL/NUMEXPR/OPENCV thread variables equal `1`, VIPE_CPU_VALIDATION=1 and PYTHONPATH points to repository scripts before imports. Unset S1_HELPER_DIAGNOSTIC/S1_RECEIPT_DIAGNOSTIC before capture; its normal diagnostic option alone chooses focus.

Use vacant diagnostic017 indices001..003 and aggregate017 indices001..002; retired unlaunched notes get higher vacant indices without extra launched slots. Before each exec exclusively create, flush/fsync/close, exact-readback and hash note, exec-start record and paired driver logs. Bind plan047, actual main `implementation-dispatch-017.json`, current IMPLEMENT status, prospective source snapshot, driver identity, command/env/stdin, output paths, full root/ancestry identity, stage/current clocks, consumed/remaining slots and reason. Count index retirement separately from launch. No note/readback failure may launch. Preserve actual tool start response, session ID or explicit synchronous-no-session state, polls and actual terminal tool completion from the first invocation. Capture's child exit and outer tool exit are distinct. Exact tool command must visibly `exec` the recorded driver; completion audit correlates tool command/start/result, driver exec-start and capture PID lifetime.

## 3. Exact prospective callback and AST amendment

The sole authorized old declaration changes are hash/write/readback 5→3, reverify/pre_input 5→4 and reuse 7→5 in `ReservationClockTests.test_real_segment_publication_barriers`. The three 5→3 cases remove persisted raw requalification and cleanup raw requalification after W; reverify and pre_input remove cleanup raw requalification; reuse removes another persisted guard plus cleanup after reuse reaches W. These implement the no-new-expensive-work-at-W requirement of Plans035/036/045/046. They do not weaken a semantic predicate. Positive=6, reuse_positive=8, qualification=2, runtime=2 and envelope_qualification=3 remain exact.

The old method AST SHA-256 is `b0a3c15cb392aab79fe0d7cfd3d5669cfb8cbdaf0263a9bf07181b6c9ed8d062`; current source and both partial snapshots agree. Before editing save per-method source records, normalized full ASTs, ordered assertion expression ASTs, literal declarations and typed callback IDs. After editing save corresponding maps, six one-to-one migrations, unchanged callback identities/order and additive assertions. Every old assertion expression remains present, including the exact `loads.count(50)==case['first_loads']` comparison and all later byte/guard assertions. No lower bounds, removal, skipped case, swallowed exception or restored late raw work can satisfy this plan. If additional old assertion/declaration changes prove necessary, stop that alteration and report it for a later concrete plan; this plan authorizes none implicitly.

Add start/completion observations for raw reads, guards and publication in the same existing method. Every production raw-operation start is strictly <W, with immediate post-operation check. Preserve one adapter call; no next input except unchanged positive controls; no result.json; one produced row; real produced/semantic verification; immutable first/raw bytes; original primary and previous acknowledged reference. The existing assertions after the former failed count must actually execute and pass. Label retrospective test inspection after leaving the production clock patch distinctly; it cannot become production qualification authority.

Exact full typed IDs, including unchanged controls, are in the table at the end and plan observations. All new declarations are explicit literal lists under the unchanged contract, with the exact additional method/parameter/callback table in §8; no dynamically generated SUBTEST_CASES at runtime.

## 4. Per-operation W enforcement and durability

Use the captured original work deadline W, never a phase-relative replacement. Thread it through every raw read/serialization/hash/guard/publication entry from stages, first_record/reconcile_first/preserve_failure, accept_result/prepare_terminal_evidence, publish_segment_row/accepted_progress, Publisher and context preparation. Check before and immediately after each fallible expensive operation, including inside real multi-artifact guards. A guard returning at W cannot start serialization or publish. A metadata read returning at W cannot start a raw guard. Optional legacy non-recovery calls retain their API behavior; recovery calls must supply W explicitly.

Refactor `write_exclusive(path,raw,deadline=...)` around an unbuffered descriptor or deadline-aware sink so no hidden buffered bulk flush occurs during close. Independently gate write (each partial-write iteration), explicit flush, file fsync, normal close and readback; always close already-open OS descriptors even after W or error. On late close, retirement is the sole permitted operation: do not flush user buffers, finalize an archive, fsync, hash, reopen, read back or promote. The cleanup close is recorded separately and cannot confer durability. An already-started syscall may return late; retain bytes/uncertainty and stop subsequent work. Do not claim OS preemption.

Separate each array, PNG and diagnostic-array serialization. Extend local array_file/png_file deadline plumbing; for NPZ use a sink that checks W on write/seek/flush and between archive members, so ZipFile exception finalization cannot perform new writes after W. For PNG, pre/post-check the one existing encoder/write operation and independently gate subsequent file hash; preserve scientific bytes/settings. Check again between NPY and PNG, before NPZ compression, after compression before hash, before produced-row serialization, after persisted row read before produced_row, before/after qualify_row, before/after first/runtime guard and each reuse guard. Structural validation preceding serialization also carries W when it reads raw evidence.

First-result reuse and failure cleanup must recheck W before each stage, not only branch entry. If W expires, retain already accepted compact metadata and diagnostic primary; never reconstruct passed evidence, reserialize predictions or invoke verify_first/qualify_row/load_array/RGBLoader to create new authority. Durable metadata-only failure diagnostics may use the existing cleanup allowance with no raw inspection; record unavailable when that allowance cannot publish. Do not replace the original exception with cleanup errors.

Preserve publication order, checking W before/after each named step: candidate serialization → exclusive checkpoint temp open/write/flush/fsync/close/readback → no-replace generation install → directory fsync → generation reopen/hash → head serialize/temp open/write/flush/fsync/close/readback → atomic head replace → directory fsync → exact head and generation readback → completion<W → notice → owner retain+matching ack before min(W,completion+0.5). Equality is late. Immutable collision passes only exact bound bytes; an in-flight late install or visible file is unacknowledged, not accepted. No new raw operation is allowed after freeze/cancel; bounded recovery may read only previously acknowledged metadata without promotion.

Keep original limits: checkpoint1MiB/depth12/65536 primitive nodes/510 rows/4096 unique refs; context, each head and composite reference8KiB; notice/ack4KiB; one outstanding generation per producer; 1024 generations/producer and2048 total/2GiB committed checkpoint bytes; dedicated tree2057 entries; current+previous bodies per producer <=4MiB plus one bounded merged snapshot/two pending notices; 32 diagnostic messages/1024 UTF-8 bytes each/2048-byte paths, separate first primary plus saturating uint64 drops and first/last observations. Worker uses1020 row generations plus at most4 coalesced state generations. Fixed abstract addresses<=96 bytes; requested socket buffers16KiB, Linux doubling recorded<=32KiB. Owner turn cancellation+census first, <=one notice+one ack and4KiB each; monitor Wire64KiB frame/16KiB combined per tick, one work/sample request outstanding. No new transport or sender/receiver.

## 5. Independently anchored ownership and a persistent registry

Implement one invocation-scoped registry in `s1_helper_session.py`, initialized once in the existing runner process/test fixture before child creation, shared by its owner threads and every existing predispatch call (Owner helper spawn, supervisor worker Popen, direct-script fixture spawn and sentinel/descendant spawn). Caller omission of `retained` cannot reset it. It is keyed by `(boot_id,pid,start_ticks)` with PGID, creation parent/event, thread IDs, classification and retirement state. All calls to owned_workload use it, including the existing controller observations. Child identity registration immediately follows spawn/PID ownership publication before other fallible work; ambiguous identities block further creation. A known PID without full identity stays conservatively unresolved, not silently excluded.

**Chosen launch authority:** use live kernel process/descriptor relationships and fixed main dispatch017 as the independent anchor, not env locator/digest, signatures invented by the same note writer, or another wrapper process. The existing runner's stdin is the unchanged capture-created `<directory>/stdin.py`; obtain it from `/proc/<runner>/fd/0`, fstat it and compare canonical path/device/inode/size/hash to exact contract stdin. Independently require runner's `/proc` cmdline `python -B -`, interpreter identity, cwd and immediate parent capture identity; capture's cmdline must exactly be the unchanged capture command for that descriptor-derived directory and allowed timeout/diagnostic mode. The root is this capture parent, whose PID/start/PGID survive driver exec. Match its live stdout/stderr descriptor identities to exclusive driver logs, and exact exec-start/note paths derived from the independently obtained directory/index. Pin root/runner/full ancestors and expected source records in memory before mutation cases. Descendant callers resolve against this pinned registry; they cannot designate a new root by supplying an environment value.

Read the actual `C/implementation-dispatch-017.json` at the fixed repository path authorized by this plan, plus its exact main-owned IMPLEMENT status snapshot and plan047 record. Main dispatch states allocation, allowed driver/path/index scheme and membership rule; mutable working source hashes are bound per invocation, never to stale Plan016 source hashes. Recompute membership from unchanged contract's explicit files plus BOTH `scripts/vipe_benchmark/*.py` and `tests/test_vipe_benchmark_*.py` globs using standard-library AST/data inspection. Match exact ordered current records, no hardcoded78 or validation013 baseline. Include driver and main dispatch/status separately as launch bindings. Reject stale plan/status/dispatch, swapped source set, duplicate/missing entries and altered bytes. Env locator+digest may name the already independently determined note only; changing both cannot authorize the live runner as root or another directory/dispatch. Do not import production ledger APIs.

This is executable with unchanged capture/runner/contract: they already create stdin, preserve descriptors/env and launch the runner directly. No pass_fds, extra process, watchdog or observer is needed. Kernel identity and fixed command/descriptor invariants reject the narrowed-note attack before fixture/helper creation; actual tool start/completion correlation supplies the later independent audit. The tool result is not falsely claimed available before launch. Same-user arbitrary memory/source/tool-evidence compromise is outside this validation trust model; do not claim cryptographic isolation from it. If the required proc evidence is unavailable, stop dispatch and follow the exact permission rule rather than weakening the anchor.

Record the complete root ancestry through PID1 with its observed PPID0 termination (or an explicitly recorded equivalent process-namespace termination). Require every link, full identity, pre-existence/start relation, no cycles, no omitted endpoint and the same terminal marker during validation. An empty/truncated list cannot certify exclusions. Shell `exec` means no retained shell wrapper; independently attest this from actual tool command, process chain and descriptors. Any separately retained task-created wrapper must have creation proof, be registered and charged; unverifiable wrappers reject. Proven pre-existing control ancestors are recorded raw and excluded only with that evidence, never by process name.

Before recursive enumeration seed the root set with every live retained detached identity, then recursively include descendants of all these roots. Reparenting does not erase ownership. Keep unresolved records charged at their last measured count (at least one thread), block new creation and do not claim acceptance until resolved. Retire only on matching wait/absence/full-identity evidence; PID reuse is not retirement proof. Enumerate every process's actual tasks and deduplicate full thread identities, with before/after process identity checks. Include capture, runner, owner, two helpers, worker, direct scripts, native support, fixture sentinel and detached grandchildren. Let B=non-wrapper owned threads and H=retained task-created wrapper threads; record measured B+H, reserve max(0,1-H), charge B+max(1,H)<=8. A measured wrapper occupies the conservative slot; additional wrapper threads consume more. Before spawning require charge+new child's minimum<=8 and recheck after creation. Unknown thread growth/enumeration failure/charge>8 prevents new work. Existing layout estimates are not measurements.

Observe ordinary, worker-active and maximum lifetimes in existing L18/L31/L35, all P cases and all six direct scripts while alive, using existing owner/fixture code only. Retain unresolved work across cases and block the next launch if retirement cannot be established. Nine old negative ownership cases remain; the exact additional cases exercise paired forged env/note, capture omission, ancestor truncation, detached grandchildren, registry reuse at every predispatch path and wrapped thread charge.

## 6. Authority, strict parsing, state and cold recovery

Preserve real produced→qualified ordering: immutable produced-row bytes, real structural produced_row success, timely produced seal/fsync/owner ack, then semantic qualify_row on the same version and timely qualified upgrade/ack. Semantic failure after produced ack retains produced=1/qualified=0, including first=True on the real first identity. No arbitrary filename/count/guard stub confers authority. Reconcile may reuse only exact externally acknowledged worker checkpoint/version/row/source indices/qualification and source-bound guard/context; Consumer compares against pinned worker identity and latest acknowledged state. Define interleaving conservatively: stale worker reference after newer worker ack is rejected/stop; a new reconcile attempt cannot silently relabel it latest. A uniquely trusted worker seal survives discovered conflicting variants as a lower bound plus sticky conflict; two incompatible trusted authorities are integrity failure. No unique trusted version means no usable fallback credit.

Unsealed fallback closes a bounded anchored inventory before credit. Preserve original limits: depth4, entries4096, candidate rows2048, variants4/identity, admitted identities510, inventory sources2048, aggregate candidate metadata32MiB, each row256KiB, canonical path2048 UTF-8 bytes. Result.json is read exactly once per retained snapshot, via anchored no-follow regular descriptor with before/after identity/size/timestamps and path-entry identity readback; parsed supplied object must equal those exact bytes under strict types. Source references include the result record. Closure and final recheck compare visited directory identity/membership and every retained result/row byte; add/remove/rename/parent/descriptor/content replacement invalidates closure. Reject symlink leaf/components, traversal/normalization, hardlink candidate aliases, foreign roots and nonregular candidates before credit. Source refs may legitimately refer to admitted raw assets outside output; verify them against request/guard rules, not a blanket output-root rule.

Use a strict bounded result decoder with duplicate-key and nonfinite rejection before equality. **Result-specific limits:**32MiB raw bytes (existing), depth64 and at most1048576 primitive nodes/tokens, lexical budget before container materialization; enforce256KiB/row and2048 result candidates after parse. These new finite parser ceilings must admit the unchanged full original510-row fixture and are separate from checkpoint depth12/nodes65536; do not incorrectly apply the1MiB checkpoint limit to result.json. Test its full fixture with real guards. Reject bool-for-number/null/type/schema/binding substitutions at every nested object before equality/indexing; result parsing cannot collapse duplicate keys. Exact scalar string bounds and nullable alternatives remain enforced.

Define coverage transitions centrally and reuse them in Publisher/Consumer/reconcile/recover: worker sealed stays sealed; reconcile incomplete may become closed only after successful closure; closed/incomplete may become conflict or overflow; conflict remains conflict; overflow remains overflow; either bad state combined with the other remains stop-required with both diagnostic reasons (coverage conflict takes precedence, never healthy). Fresh publication within the same context cannot clear either failure. Accepted counts remain historical immutable observations; fallback-only snapshot invalidated by observed mutation is frozen integrity-failed/unusable for current healthy progress, while separately acknowledged worker authority remains usable. Expose the distinction; never silently subtract historical accepted rows or keep invalidated fallback rows healthy. Unknown totals remain strings `unknown`; complete totals require real all510/340-fit/170-selection acceptance and no uncertainty. Keep first primary separately,32-message bound, saturating dropped counter and first/last failure observations so truncation does not clear sticky state. Add required `diagnostics` to checkpoint `s1-verified-progress/v2`: exactly `{dropped,first,last,primary}`; dropped is uint64 saturated, first/last/primary are null before any failure or exact `{error_class,message,phase,observed}` with UTF-8 bounds128/1024/96 and finite original-clock observed time. Preserve existing `errors` list and all old error assertions. First and primary never change once nonnull; last is monotone by observed time, dropped never decreases. No failure may disappear solely because the list is full. Current checkpoint consumers reject v1/mixed shapes; historical v1 evidence remains immutable.

A single summary_adapter preserves independently acknowledged rows/counts/first/runtime/acceptance and unknown totals. Runtime keys are exactly initial-runtime.json, partial-runtime.json and final. Every status envelope is exactly `{status,value}`: verified→valid immutable record; unverified→null. Ordinary unverified non-null values reject even when independent progress exists. Same verified values are idempotent, conflicts fail; ordinary metadata cannot invent independent authority, clear errors or replace unknown totals with zero. Preserve full first/runtime/complete guard fixtures.

Retain accepted provenance in the bounded lifecycle-owned immutable snapshot and composite reference: per producer exact accepted checkpoint AND exact accepted head record, previous accepted checkpoint/head where present, plus at most one intended successor notice descriptor. The intended successor becomes trusted only after owner validates actual sender credentials/full producer/request binding and exact next sequence/previous reference, before its fallible metadata reads; arbitrary on-disk head or caller dict cannot supply it. This uses existing notice, at most two pending descriptors and the existing8KiB compact limit; it adds no message/process or generation. Version the compact reference as `s1-progress-reference/v2`, with required exact `provenance`; reject v1/mixed shapes in current recovery while preserving all historical v1 evidence. Context/head/notice/ack schemas stay unchanged; checkpoint diagnostics are versioned explicitly below. Snapshot/ref schema additions are exact and source-bound; all producers/readers validate their nested types. No change to ready/control envelope or validation contract.

Cold recovery opens only named context, at most two current head paths and at most four externally trusted checkpoint bodies (current+previous per producer); no directory/history/raw scan. Head exact accepted hash plus accepted body exact hash permits verified accepted lower bounds. A structurally valid contiguous unacknowledged successor can be treated as optional only when matching independently retained credentialed successor provenance; never promote it. Missing/truncated optional successor body/head with that provenance may preserve verified older authority, newest unavailable and scan_complete=false. Missing/truncated/changed accepted checkpoint or accepted head without qualifying successor provenance is integrity failure or explicit uncertainty/stop; absence does not prove optionality. Valid-but-regressed head, foreign context, source/authority conflict or changed accepted bytes is integrity-failed/stop. No known provenance means uncertain/stop. Do not turn uncertainty into healthy fallback because counts happen to match. Existing accepted-head corruption count assertion stays and gains integrity_status/stop_required/scan_complete assertions.

Before dequeue, after credentials, before/after each fallible context/old-checkpoint/head/new-checkpoint/worker-authority read, before retention and before/after ack send/receipt, check original deadline and cancellation/freeze. Freeze pointer before poison/reap; late read/send returns cannot advance cache or manufacture an ack. A send failure restores old snapshot; if send may have become visible but deadline/cancel wins, preserve explicit uncertainty rather than asserting acknowledged success. Read only bounded metadata on the owner. Loss before ack retains prior pointer; loss after completed matching timely ack retains new pointer independently of ordinary helper response. No replacement helper or fake terminal receipt.

## 7. Original failures and the six existing P scenarios

Each P case still executes its actual failed supervise path and reaches its named boundary. Persist a bounded record containing exact original exception class/text/kind/stop_required, primary phase and first occurrence, full relevant finish outcome (including error, cleanup/stop/deadline/publication fields, terminal_receipt=null, reference, counts and surviving ownership), ordered secondary errors and the original work/safety cutoffs. Store real guard-entry/completion, row/version hashes, write/flush/fsync/close/readback, notice, owner-retention and ack events with monotonically ordered indices and original-clock times. Include source references and boundary attainment, not just exception class or method collection. Use bounded event traces with explicit overflow invalidating evidence; reference large existing documents rather than unbounded copying.

| Case | Required evidence under unchanged scenario allocation |
| --- | --- |
| P01 | Mixed fit/selection real segment-row hook, real structural and semantic guard, timely durable ack, then W. Tripwires reject every late raw load/hash/serialization/reconcile/first/runtime/accept call. Actual failure retains exact nonzero lower bounds and unknown totals, same original primary. |
| P02 | Closed small inventory and real guard/ack then next-row block to original W; same sampler/helpers; failure retains prior pointer. Unclosed inventory variant remains pure and credits no fallback. |
| P03 | Existing work helper killed after ack/before ordinary response; actual transport/poison/reap and supervisor primary preserved; named metadata cold recovery, no raw rescan/replacement. |
| P04 | Preserve and label the existing two-row reconciliation/final-sample-loss fixture honestly. It does not establish510-row acceptance. Add the single pure full-completion/final-sample integration below; both evidence records are required. |
| P05 | Ack generation1; actual second publication reaches head install/readback fault; save persisted bytes and original supervisor failure; retain generation1, classifying optional-newer versus accepted damage via provenance. |
| P06 | Ack generation1; hold actual owner read for2; original timeout freezes old pointer and supervisor returns uncertainty/stop with null receipt. Record this production-cutoff outcome first. Release only in existing1-second safety interval; late return cannot advance pointer. Save later retirement separately. |

The new pure `HelperSessionTests.test_progress_plan047_complete_final_sample` uses ONE full existing synthetic510-row numerical fixture shared by its two literal cases, not510 fixtures per mutation. Execute real active binding, accept_result/validate_result, accepted_progress and real publish/Consumer ack with the existing inline consumer (no extra thread/child); retain510/340/170 counts, exact accepted result, first/runtime and acceptance records. Use a test-only synchronous Session facade implementing ready/resume/await_ready/set_worker/submit/tick/requests/close/ownership and carrying the real progress_cache; inject it through existing HelperLifecycle.session_factory and the existing pure Popen/retirement seams with no real spawn. Its work submit executes the real session_operation synchronously; tick returns the actual result and monotonic completion/dispatch observations in the existing role tuple shape. Its sample submit executes the pure sampler. Run unchanged monitored_call and supervise, including their real exception/freeze/finish paths. The facade only replaces transport/process creation, not acceptance or guards. At the final-sample boundary: successful control returns, fault case injects sampler failure ONLY AFTER that same operation's genuine acceptance/progress ack. Save request/session/reservation/result/checkpoint correlation and actual SupervisionFailure/finish outcome, final sample phase, null terminal receipt and surviving complete accepted progress. Do not stub accept/reconcile, return `[None,None]`, synthesize sealed rows or turn independent successful controller evidence into fault evidence. Keep existing real synthetic controller checks unchanged. This establishes correlated accepted completion and subsequent failure within a collected pure case, not real native worker traversal.

Use nested finally retirement: worker kill/wait and helper/owner cleanup are attempted under original safety cutoff even if observation/assertion/earlier retirement fails. No next scenario/direct script with known live or unresolved owned work. Save primary and cleanup failures separately. A no-PID/no-handle state alone is not cleanup evidence. Do not describe eventual safety retirement as a met production cutoff or full R9-5.

## 8. Finite collected tables and exact relevance

The following table definitions and literal machine table in plan observations fix all new method names, parameter dictionaries and typed IDs prospectively. Each new method is under `test_vipe_benchmark_supervisor.HelperSessionTests`; each declaration is a literal list copied into SUBTEST_CASES. Each case records the actual source check/function reached, expected and observed result, boundaries/counter values, fixture hash and preserved pointer; exception text alone is insufficient relevance. Do not add new real processes for mutation cases. Keep all existing cases, including miniature-limit path controls, but exact limit acceptance comes from the cases below with production constants unchanged.

Deadline table: for each operation listed below run `when=before,equal,after` using an injected clock advanced by the immediately preceding REAL operation, never by bypassing the operation under test. Before permits that operation; equal/after forbids its start, preserves partial bytes and retires descriptors. Complete operations/guards use one small real valid numerical fixture. Publication fault rows additionally inject the concrete I/O/transport error at the named operation, retaining prior ack and original stage. No whole-publish/guard success stub qualifies.

Capacity table: each row has exact `value=limit-1,limit,limit+1`. Assert exact endpoint behavior at the actual production counter/parser/validator, including preallocation/open rejection; secondary semantic validation is separately asserted, so hitting the numeric endpoint is not falsely equated with valid scientific membership. For fixed complete membership510,509 is valid incomplete and510 real exact ordered membership;511 rejects. Production constants are not patched. Create actual modest metadata payloads/entries where practical; for2GiB storage and combined-generation/tree/retention budgets call the factored production preallocation accounting routine at its real numeric limit, then trace that same routine from real tiny publication. This avoids allocating2GiB without replacing the documented limit by one. For depth/string/node/parser-byte limits supply actual payloads with exact measured UTF-8 length/depth/node count; use multibyte endpoint strings and inert metadata padding. Capacity cases do not run raw guards510 times.

Nested table: each named nested object has missing key, extra key and wrong-container mutations from one valid document, with explicit missing field named in observations. Scalar/binding cases cover bool/int, signed/overflow/nonfinite times, closed enum, null alternatives, identity/order/indices, boot/source/context/request/reservation and credential binding. Each enclosing entrypoint must exercise its nested validator; directly testing `integer` alone does not prove protocol validation.

Alias/inventory table supplies concrete leaf/component symlinks, hardlinks, normalized/traversal paths, foreign roots, nonregular and replaced descriptors, and mutation at closure and after provisional publication. State/authority and recovery tables distinguish semantic failure after produced ack, stale/future/self-issued worker authority, interleaving, sticky failures, accepted metadata damage and optional-newer provenance. Cancellation table selects every named fallible stage and before/after cancellation, asserting no subsequent read, retain or ack and frozen pointer equality.

The exact expanded finite lists, constants, expected behavior and source targets follow in generated appendices and observations. Their new counts are prospective only. Record an AST/declaration preparation map before the first launch and reject missing/extra/renamed/unmapped cases rather than using loose totals.

## 9. Acceptance, evidence and complete handoff

| Gate | Required new evidence | Mapping |
| --- | --- | --- |
| A47-1 | Kernel/dispatch anchored actual capture root, full terminated ancestry, persistent detached registry at every predispatch, exact live B+max(1,H)<=8, all ownership negatives and six direct-script lifetimes. | F2/F3; preserves S1-4, S1-2/S1-3 prerequisite. |
| A47-2 | Real produced-before-qualified seals/acks, semantic-failure and interleaving controls, closed exact bounded inventory/aliases/result parser and strict authority/state tables. | F4/F5/F6; preserves S1-1, S1-3 prerequisite. |
| A47-3 | Every W/I/O/raw guard boundary, strict nested schemas/nulls, exact limits, cancellation, durable publication and accepted/provisional recovery provenance with bounded retained state. | F1/F4/F5/F6; S1-2/S1-3 prerequisite. |
| A47-4 | All six actual P primary outcomes and ordered evidence, unchanged small P04 plus correlated pure real-complete/final-sample case, original P06 cutoff distinct from safety retirement, no late promotion/fake receipt. | F1/F7; S1-3 prerequisite. |
| A47-5 | Final complete current-source aggregate with exact preserved/migrated/additional methods/callbacks/assertions, all42 scenarios/six scripts, zero failure/error/skip/discovery error, source before/after equal and actual outer exit0/no timeout<=300s. | F8; preserves S1-1/S1-4. |
| A47-6 | First/all clocks, prospective launch and actual outer completion, limits/cleanup, old failures/partial sources/frozen38/raw ledger, corrected exact event selection and actual status lineage. | F3/F8/E1; preserves S1-4. |

Technical milestone requires A47-1..5; strict Plan047 requires all six. Known failures are not met; unsupported evidence is unverified. None passing alone promotes historical acceptance. Even all six passing leaves S1-2/S1-3 not met pending admission/live recovery. All old/current scientific fixtures remain; suite order is s1_semantics,s1_recovery,backends,contracts,component_recovery,execution,budgets,supervisor,review_annotations. Require exact source-glob membership and actual outer tool completion in addition to receipt/execution files. A fresh standard-library file/AST/git-byte audit is allowed; do not execute stale audit scripts or import production modules for audit.

Before the4800 cutoff finish all source/tests. Exclusively save next vacant implementation successors: `s1-recovery-baseline-correction-015.json`, `s1-recovery-validation-016.json`, `s1-recovery-audit-017.json` (further independent passes use new suffixes), `s1-recovery-implementation-review-015.md`, `assessment-043-implement.json`, and iteration017 preparation/method-baseline/launch/tool/permission/process/deadline/protocol/capacity/recovery/scenario/limitations/remaining-gates/timing/handoff/completion records. Confirm vacancy; increment occupied successors, never replace old artifacts. Preserve final changed-source copies in new partial-source017 if incomplete. Handoff binds exact final sources, before/after assertion maps and six migration IDs, each case/relevance record, all consumed attempts/output/outer results, cleanup uncertainty, acceptance/criteria and elapsed through full handoff readback. Main owns subsequent status transitions and validated task-only local commits with separate escalated git add/commit and staged diff inspection; no push/amend/history rewrite. A commit is a checkpoint, and active loop proceeds to fresh Review when no stop applies.

Preserve correction014's31-transition prefix; actual review017+plan017 makes33 and actual future implement017 makes34. Current PLAN status is1330 bytes, SHA256 `41ee794a141118ae5a5a80b0d70490365e7c1cc8364e6b8e5833233aa9018dc3`. Main's eventual IMPLEMENT status gets its own recorded bytes/hash; do not use current PLAN or old Plan046 status as launch admission. Retain unavailable historical snapshots with provenance, never reconstruct them. There is no Plan045/046 commit/postcommit transition.

Preserve frozen38 and raw ledger447 events/332437 bytes, SHA256 `2a0f66e38911b0ed029eb9dd0cf4bbd5da4a3b67abb577fbfe9ad67e6a888990`, head `00cab019d73b6a3205f676b54cfb2f745f492fa5cca5c69b4567087cea62172b`:30 historical GPU reservations,4374.044265462899 consumed seconds,0 reserved,no active job/recovery event. Read bytes only. **Correct new indexing:** select records by exact `event['sequence'] in (250,255,256)`, verify job/event/hash and store full records. Old validation015/audit016 `original_events` selected249/254/255 by line; preserve that old error and explicitly link correction, never rewrite old records or ledger. Sequence250 is cleaned failed S1-calibration,255 cleaned failed S1-reconstruction,256 skipped R-S.

## 10. Later gates retained in full

Full R9-5 and remaining R9-3 remain: structured primary and ordered secondary failures, continuously monitored cleanup/publication/finalization, C/2+C/4+C/4, conservative charged cutoff and timely durable acknowledgment, first/native/receipt/finish/ack order and actual loss-path results. Preserve remaining native/runtime/referenced-evidence matrices, actual zero-detection/oversized-box execution, real ordered510-row worker traversal and340/170 split, first/later failure progression, synchronized admission/registration/reservation and contenders, complete dependency/cache/PID/PGID/controller-death lifecycle matrices. Pure progress completion is not evidence these later gates passed.

Production admission must bind semantic amendment, current successful validation, original cleaned-up failure, E1 qualification/assets, one calibration attempt and original resources. Later calibration remains one reservation-consuming attempt capped3600 GPU seconds, effective min(3600,93600-gpu_elapsed-gpu_reserved)>0 with min(30,effective_seconds/4) cleanup inside. Historical balance89225.9557345371 seconds is not live authorization. Original exclusive device use,22GiB device memory,eight CPU workers,150GiB artifacts,60GiB downloads,57600-second setup and applicable CPU preparation/import/scoring/report ceilings remain scoped and unchanged. This CPU development allocation does not reset/consume an unrelated scientific allocation. Reconstruction needs separate later authorization after calibration review.

## Appendix A. Exact legacy typed callback migrations

The full prefix is repeated so identity comparison requires no abbreviation.

| Case | Old typed callback ID | New typed callback ID |
| --- | --- | --- |
| positive | `test_vipe_benchmark_s1_recovery.ReservationClockTests.test_real_segment_publication_barriers::[["first_loads","int",6],["kind","str","positive"]]` | `test_vipe_benchmark_s1_recovery.ReservationClockTests.test_real_segment_publication_barriers::[["first_loads","int",6],["kind","str","positive"]]` |
| reuse_positive | `test_vipe_benchmark_s1_recovery.ReservationClockTests.test_real_segment_publication_barriers::[["first_loads","int",8],["kind","str","reuse_positive"]]` | `test_vipe_benchmark_s1_recovery.ReservationClockTests.test_real_segment_publication_barriers::[["first_loads","int",8],["kind","str","reuse_positive"]]` |
| qualification | `test_vipe_benchmark_s1_recovery.ReservationClockTests.test_real_segment_publication_barriers::[["first_loads","int",2],["kind","str","qualification"]]` | `test_vipe_benchmark_s1_recovery.ReservationClockTests.test_real_segment_publication_barriers::[["first_loads","int",2],["kind","str","qualification"]]` |
| runtime | `test_vipe_benchmark_s1_recovery.ReservationClockTests.test_real_segment_publication_barriers::[["first_loads","int",2],["kind","str","runtime"]]` | `test_vipe_benchmark_s1_recovery.ReservationClockTests.test_real_segment_publication_barriers::[["first_loads","int",2],["kind","str","runtime"]]` |
| envelope_qualification | `test_vipe_benchmark_s1_recovery.ReservationClockTests.test_real_segment_publication_barriers::[["first_loads","int",3],["kind","str","envelope_qualification"]]` | `test_vipe_benchmark_s1_recovery.ReservationClockTests.test_real_segment_publication_barriers::[["first_loads","int",3],["kind","str","envelope_qualification"]]` |
| hash | `test_vipe_benchmark_s1_recovery.ReservationClockTests.test_real_segment_publication_barriers::[["first_loads","int",5],["kind","str","hash"]]` | `test_vipe_benchmark_s1_recovery.ReservationClockTests.test_real_segment_publication_barriers::[["first_loads","int",3],["kind","str","hash"]]` |
| write | `test_vipe_benchmark_s1_recovery.ReservationClockTests.test_real_segment_publication_barriers::[["first_loads","int",5],["kind","str","write"]]` | `test_vipe_benchmark_s1_recovery.ReservationClockTests.test_real_segment_publication_barriers::[["first_loads","int",3],["kind","str","write"]]` |
| readback | `test_vipe_benchmark_s1_recovery.ReservationClockTests.test_real_segment_publication_barriers::[["first_loads","int",5],["kind","str","readback"]]` | `test_vipe_benchmark_s1_recovery.ReservationClockTests.test_real_segment_publication_barriers::[["first_loads","int",3],["kind","str","readback"]]` |
| reverify | `test_vipe_benchmark_s1_recovery.ReservationClockTests.test_real_segment_publication_barriers::[["first_loads","int",5],["kind","str","reverify"]]` | `test_vipe_benchmark_s1_recovery.ReservationClockTests.test_real_segment_publication_barriers::[["first_loads","int",4],["kind","str","reverify"]]` |
| reuse | `test_vipe_benchmark_s1_recovery.ReservationClockTests.test_real_segment_publication_barriers::[["first_loads","int",7],["kind","str","reuse"]]` | `test_vipe_benchmark_s1_recovery.ReservationClockTests.test_real_segment_publication_barriers::[["first_loads","int",5],["kind","str","reuse"]]` |
| pre_input | `test_vipe_benchmark_s1_recovery.ReservationClockTests.test_real_segment_publication_barriers::[["first_loads","int",5],["kind","str","pre_input"]]` | `test_vipe_benchmark_s1_recovery.ReservationClockTests.test_real_segment_publication_barriers::[["first_loads","int",4],["kind","str","pre_input"]]` |

## Appendix B. Exact new method and finite case tables

The saved literal table adds **11 methods / 486 callbacks**, yielding **248 collected methods / 1012 callbacks** with the six one-to-one migrated IDs. These are exact prospective counts; source/declaration and actual receipt equality is required. New method names below have prefix `test_vipe_benchmark_supervisor.HelperSessionTests.test_progress_plan047_`. The observations contain every expanded typed ID and expected reached-check mapping.

### deadline_steps

Each operation has exactly three cases: `when="before"`, `"equal"`, `"after"`.

| operation | Actual reached check |
| --- | --- |
| checkpoint_write | s1_progress.write_exclusive actual write/short-write loop |
| checkpoint_flush | s1_progress.write_exclusive explicit flush |
| checkpoint_fsync | s1_progress.write_exclusive file fsync |
| checkpoint_close | s1_progress.write_exclusive normal close versus unconditional retirement |
| checkpoint_readback | s1_progress.write_exclusive read_bytes |
| head_write | Publisher._publish head write_exclusive write |
| head_flush | Publisher._publish head flush |
| head_fsync | Publisher._publish head file fsync |
| head_close | Publisher._publish head close |
| head_readback | Publisher._publish head temp readback |
| generation_install | Publisher._publish no-replace link |
| generation_dir_fsync | Publisher._publish fsync_dir after generation install |
| generation_reopen_hash | Publisher._publish read_record current |
| head_install | Publisher._publish os.replace |
| head_dir_fsync | Publisher._publish fsync_dir after head install |
| final_head_read | Publisher._publish final head read |
| final_generation_read | Publisher._publish final generation read |
| notice_send | Publisher._publish sendto |
| owner_retention | Consumer.tick cache acknowledge |
| ack_send | Consumer.tick send closure |
| ack_receipt | Publisher._publish receive and final time check |
| array_npy | stages.array_file np.save sink |
| array_png | stages.png_file cv2.imwrite |
| npz_member | stages.segment diagnostic archive member write |
| npz_finalize | stages.segment diagnostic archive central-directory/close sink |
| array_hash | stages.segment file_record after serialization |
| produced_json | publish_segment_row produced serialization |
| produced_read | publish_segment_row read_record before guard |
| produced_guard | s1_evidence.produced_row raw guard |
| qualified_guard | s1_evidence.qualify_row semantic guard |
| first_guard | s1_evidence.verify_first |
| runtime_guard | s1_evidence.qualify_runtime |
| reuse_after_read | first_record existing metadata read then real verify_first |
| cleanup_next_array | preserve_failure between raw artifacts |
| accept_after_read | s1_recovery.accept_result read then validate_result |
| complete_after_read | prepare_terminal_evidence accepted/result reads then guard |
| next_input | stages.segment RGBLoader.load entry |
| worker_popen | supervisor.supervise immediately after install_progress/env preparation before Popen |
### ownership

| kind | Required result and relevance |
| --- | --- |
| paired_env_runner_root | env locator+digest and rehashed runner-root note reject against kernel capture parent |
| paired_env_foreign_output | env run-directory+note pair rejects against runner fd0 |
| stale_dispatch016 | fixed dispatch017 rejects old plan/status |
| forged_dispatch_env | env cannot substitute dispatch path |
| capture_omitted | live capture identity must be owned |
| stdin_inode_replaced | fd0 and named stdin dev/ino/bytes must agree |
| capture_argv_swapped | capture argv must match descriptor-derived directory/timeout |
| driver_log_inode_swapped | root log descriptors must match exec-start evidence |
| ancestor_empty | nonzero root ppid cannot have empty ancestry |
| ancestor_truncated | omitted PID1/PPID0 endpoint rejects |
| ancestor_cycle | cycle rejects |
| ancestor_terminal_changed | changed terminal marker rejects |
| detached_grandchild | retained detached root seeded before recursive child discovery |
| retained_pid_reuse | same pid/new start rejects; unresolved old charged |
| registry_owner_dispatch | same retained object consulted by Owner.run before each helper |
| registry_worker_dispatch | same retained object consulted immediately before supervisor Popen |
| registry_direct_dispatch | same retained object consulted at every direct script creation |
| registry_sentinel_dispatch | same retained object consulted before sentinel/descendant creation |
| registry_missing_enumeration | unknown prior task remains charged and blocks new child |
| test_glob_addition | legitimate current test member accepted only in actual ordered source snapshot |
| test_glob_omission | missing expected test member rejects |
| wrapper_unproven | nonempty wrapper requires creation proof |
| wrapper_one_thread | B7 H1 charge8 accepted |
| wrapper_two_threads | B7 H2 charge9 rejects |
| no_wrapper_reserve | B7 H0 charge8 accepted; B8 H0 rejects |
### limits

Each limit has exactly three integer values: N−1,N,N+1; no patched maximum.

| limit | N | Actual reached check |
| --- | ---: | --- |
| inventory_depth | 4 | candidate_inventory.walk depth before child open |
| variants | 4 | reconcile_rows distinct version insertion |
| identities | 510 | validate_checkpoint/identity_index ordered admitted membership |
| candidates | 2048 | candidate_inventory candidate append/result candidate precheck |
| inventory_sources | 2048 | candidate_inventory source append |
| directory_entries | 4096 | candidate_inventory walk and ClosedInventory global recheck budget |
| embedded_refs | 4096 | Publisher.seal and validate_checkpoint sources/source_indices |
| metadata_bytes | 33554432 | candidate_inventory aggregate reserve before append |
| row_bytes | 262144 | bounded row read/encode |
| path_utf8_bytes | 2048 | canonical and validate_record |
| checkpoint_bytes | 1048576 | encode/decode checkpoint limit |
| checkpoint_depth | 12 | decode lexical depth/primitives |
| checkpoint_nodes | 65536 | decode lexical tokens/primitives counter |
| producer_generations | 1024 | Publisher._publish/validate_checkpoint sequence bound |
| total_generations | 2048 | shared publication preallocation accounting |
| committed_bytes | 2147483648 | shared publication committed-byte preallocation accounting |
| tree_entries | 2057 | dedicated-tree preallocation accounting, no history scan |
| retained_bytes | 4194304 | current+previous immutable body retention accounting |
| context_bytes | 8192 | context encode/decode limit |
| head_bytes | 8192 | head encode/decode limit |
| reference_bytes | 8192 | snapshot compact encode/decode including provenance |
| control_bytes | 4096 | notice/ack encode and receive truncation |
| result_bytes | 33554432 | strict result decoder before parse |
| result_depth | 64 | strict result lexical depth |
| result_nodes | 1048576 | strict result lexical/primitive node budget |
| error_count | 32 | bounded diagnostics append/drop |
| error_utf8_bytes | 1024 | diagnostic bounded encoding |
| socket_address_bytes | 96 | fixed-address validation before bind |
### alias_inventory

| kind | Required result and relevance |
| --- | --- |
| leaf_symlink | candidate leaf symlink rejects |
| component_symlink | any ancestor symlink rejects |
| dot_alias | /./ alias rejects |
| dotdot_traversal | /../ rejects |
| repeated_separator | double slash normalization rejects |
| hardlink_duplicate | two candidate names same dev/ino reject |
| hardlink_external | candidate nlink>1 alias to external file rejects |
| foreign_candidate_root | outside output candidate rejects; request-admitted raw assets remain valid |
| fifo_candidate | nonblocking nonregular read rejects |
| directory_candidate | row filename naming a directory rejects |
| descriptor_replacement | open fd identity differs named path after read rejects |
| row_bytes_closure | row changed during closing recheck invalidates fallback |
| result_bytes_closure | result changed during closing recheck invalidates fallback |
| member_add_closure | added candidate during closing recheck rejects |
| member_remove_closure | removed candidate during closing recheck rejects |
| member_rename_closure | renamed candidate during closing recheck rejects |
| parent_replace_closure | directory dev/ino replaced rejects |
| member_add_after_publish | new member after provisional fallback publication freezes unusable fallback |
| member_remove_after_publish | removed member after provisional publication freezes unusable fallback |
| member_rename_after_publish | renamed member after provisional publication freezes unusable fallback |
| result_replace_after_publish | changed result after provisional publication freezes unusable fallback |
| row_replace_after_publish | changed row after provisional publication freezes unusable fallback |
### nested

Each target has exactly `mutation="missing","extra","wrong_container"` with the named `field`. Extra inserts `__plan047_extra__`; wrong_container substitutes a list; missing removes precisely the named key.

| target | field |
| --- | --- |
| context | schema |
| context.clock | request |
| context.clock.request | sha256 |
| context.clock.reservation | sequence |
| context.authorization | path |
| context.work | pid |
| context.sources | guard |
| context.sources.guard | bytes |
| checkpoint | producer |
| checkpoint.binding | start_ticks |
| checkpoint.previous | path |
| checkpoint.rows.0 | identity |
| checkpoint.rows.0.identity | branch |
| checkpoint.rows.0.row | sha256 |
| checkpoint.rows.0.authority | version |
| checkpoint.sources.0 | bytes |
| checkpoint.diagnostics | dropped |
| checkpoint.diagnostics.first | message |
| checkpoint.diagnostics.last | observed |
| checkpoint.diagnostics.primary | error_class |
| checkpoint.counts | qualified |
| checkpoint.runtime.final | path |
| head | current |
| head.current | sha256 |
| notice | head |
| notice.binding | pgid |
| notice.head | bytes |
| ack | sequence |
| ack.current | path |
| reference | provenance |
| reference.reservation | event_sha256 |
| reference.provenance.worker | accepted_head |
| reference.provenance.worker.accepted_head | sha256 |
| reference.provenance.worker.intended_successor | previous |
| reference.provenance.worker.intended_successor.binding | pid |
| summary.runtime.final | value |
| summary.first_result | status |
### state_authority

| kind | Required result and relevance |
| --- | --- |
| produced_then_semantic_failure | real produced guard+ack retained; real semantic failure no qualified upgrade |
| first_identity_semantics | first=True guard belongs to true first identity, not first discovered fallback |
| worker_reuse_exact | exact acknowledged seal reused with no new raw guard |
| worker_stale_interleave | worker new ack between reconcile snapshot and consume rejects stale authority |
| worker_future_reference | unacknowledged future reference rejects |
| worker_self_reference | self-selected record cannot authorize worker |
| worker_qualified_overclaim | produced-only seal cannot be reused as qualified |
| worker_sources_changed | source indices/record mutation rejects |
| worker_row_version_changed | same identity different row/version rejects |
| worker_detached_identity | registered retained producer matches full boot/start/pgid through reparenting |
| trusted_conflict | incompatible trusted producer seals are integrity failure |
| discovered_conflict | unique trusted worker lower bound remains plus sticky conflict |
| fallback_no_unique_version | two unsealed versions credit none |
| fallback_invalidated | already published fallback-only snapshot becomes unusable/frozen; worker authority retained |
| conflict_to_closed | attempt to clear conflict rejects |
| overflow_to_closed | attempt to clear overflow rejects |
| overflow_to_incomplete | attempt to clear overflow rejects |
| conflict_plus_overflow | conflict precedence with both reasons and stop retained |
| errors_saturation | 32 errors then saturating drops, first primary/first-last retained |
| diagnostics_drop_regression | dropped counter decrease rejects |
| diagnostics_primary_replaced | nonnull first primary mutation rejects |
| checkpoint_v1_rejected | old v1 or mixed diagnostics shape rejects current checkpoint validation |
| qualification_regression | qualified true->false rejects |
| first_runtime_regression | verified first/runtime removal or replacement rejects |
| acceptance_regression | accepted record removal/replacement rejects |
| duplicate_exact | latest exact duplicate idempotent within original ack deadline |
| duplicate_conflict | same seq changed bytes rejects |
| sequence_replay | old seq rejects |
| sequence_jump | prior+2 rejects |
| request_changed_late | same producer seq with unauthorized request rejects |
### recovery

| kind | Required result and relevance |
| --- | --- |
| accepted_exact | same head/body verified, exact counts/refs |
| optional_valid_successor | trusted credentialed intended next notice; successor not promoted; accepted old usable/newest unavailable/incomplete |
| optional_successor_body_missing | trusted successor provenance and unchanged old body permit old lower bound, no new credit |
| optional_successor_body_truncated | same as missing; old accepted usable |
| optional_successor_head_truncated | trusted successor provenance distinguishes newer damage; preserve accepted lower bound, scan incomplete |
| head_missing_no_intent | uncertain stop true scan false; no healthy fallback |
| head_truncated_no_intent | uncertain stop true scan false; existing old count remains historical only |
| accepted_body_missing | integrity failure stop true |
| accepted_body_changed | integrity failure stop true |
| accepted_head_changed | valid same-sequence changed current/previous fails integrity |
| head_regressed | integrity failure stop true |
| context_changed | integrity failure stop true |
| foreign_provenance | forged head/intended successor rejects |
| unacknowledged_only | no externally accepted record means no healthy progress |
| history_tripwire | at most2heads/4bodies/context; any enumeration/raw open fails |
| current_previous_retention | third publication evicts oldest memory body but preserves exact current+previous bound |
| late_recovery | metadata-only afterW cannot promote or raw guard |
### cancellation

Each stage has exactly `when="before","after"`: `dequeue`, `credentials`, `context_read`, `old_checkpoint_read`, `head_read`, `new_checkpoint_read`, `worker_authority_read`, `retention`, `ack_send`, `ack_receipt`. All assert cancellation/freeze, no further fallible read/cache/ack, and retained pointer equality.

### result_summary

| kind | Required result and relevance |
| --- | --- |
| result_duplicate_top | duplicate top-level key rejects before equality |
| result_duplicate_row | duplicate nested identity/row key rejects |
| result_nonfinite | NaN/Infinity result rejects |
| result_supplied_bool_int | parsed snapshot differs typed supplied object; rejects |
| result_full510 | original full fixture strict parse and actual scientific guard passes |
| runtime_unverified_nonnull | unverified runtime value={} rejects |
| runtime_verified_null | verified runtime null rejects |
| runtime_unknown_status | runtime status enum rejects |
| first_unverified_nonnull | first unverified value={} rejects |
| runtime_final_conflict | different verified final ref rejects |
| runtime_alias | partial alias rejects |
| summary_unknown_totals | ordinary zero cannot clear unknown or lowerbounds |
| notice_bool_pid | bool PID rejects |
| notice_bool_request | bool request rejects |
| ack_bool_sequence | bool sequence rejects |
| clock_bool_start | bool monotonic start rejects |
| clock_negative_time | negative time rejects |
| clock_overflow_time | 10**400 rejects without permissive float comparison |
| clock_nonfinite | NaN/infinity rejects |
| reservation_bool_sequence | bool reservation seq rejects |
| process_pid_bound | PID2**31 and nonpositive reject |
| identity_bool_camera | bool camera rejects |
| identity_wrong_branch | non-calibration branch rejects |
| identity_pair_nonnull | nonnull pair_start rejects |
| identity_order_duplicate | duplicate/reordered admitted rows reject |
| indices_bool | bool index rejects |
| indices_duplicate | duplicate index rejects |
| indices_out_of_range | out-of-range index rejects |
| context_wrong_boot | wrong boot binding rejects |
| context_wrong_guard | changed guard hash rejects |
| notice_wrong_uid | SCM UID mismatch rejects |
| notice_wrong_pid | SCM PID mismatch rejects |
| notice_wrong_sender | sender address mismatch rejects |
| notice_truncated | MSG_TRUNC or CMSG_TRUNC rejects |
| notice_missing_credentials | zero/multiple credential tuple rejects |
| ack_wrong_binding | ack context/current mismatch rejects |
| reference_v1_rejected | old v1 or mixed provenance shape cannot enter current v2 recovery |
| reference_bool_frozen | bool exactness rejects integer frozen |
| reference_wrong_reservation | different event hash rejects |
### complete_final_sample

| kind | Required result and relevance |
| --- | --- |
| success | full510 acceptance/340fit/170selection control with exact correlated first/runtime/result |
| final_sample_failure | same genuine completion ack before injected final sampler primary; actual failed supervisor outcome and null receipt, accepted reference survives |
### publication_faults

| kind | Required result and relevance |
| --- | --- |
| checkpoint_open | exclusive nofollow open error; preserve original fault, prior ack and bounded partial bytes |
| checkpoint_write_short | actual short write terminates publication; preserve original fault, prior ack and bounded partial bytes |
| checkpoint_flush | flush raises; preserve original fault, prior ack and bounded partial bytes |
| checkpoint_fsync | file fsync raises; preserve original fault, prior ack and bounded partial bytes |
| checkpoint_close | normal close raises; retirement attempted; preserve original fault, prior ack and bounded partial bytes |
| checkpoint_readback | actual written bytes readback mismatch; preserve original fault, prior ack and bounded partial bytes |
| head_open | head temp exclusive open error; preserve original fault, prior ack and bounded partial bytes |
| head_write_short | head short write; preserve original fault, prior ack and bounded partial bytes |
| head_flush | head flush error; preserve original fault, prior ack and bounded partial bytes |
| head_fsync | head fsync error; preserve original fault, prior ack and bounded partial bytes |
| head_close | head close error; preserve original fault, prior ack and bounded partial bytes |
| head_readback | head temp readback mismatch; preserve original fault, prior ack and bounded partial bytes |
| generation_collision_exact | exact bytes collision idempotent only if all binding checks pass; preserve original fault, prior ack and bounded partial bytes |
| generation_collision_changed | collision changed bytes integrity failure; preserve original fault, prior ack and bounded partial bytes |
| generation_dir_fsync | directory fsync error leaves unacknowledged bytes; preserve original fault, prior ack and bounded partial bytes |
| head_dir_fsync | head directory fsync error unacknowledged; preserve original fault, prior ack and bounded partial bytes |
| final_generation_readback | generation tamper at final readback; preserve original fault, prior ack and bounded partial bytes |
| final_head_readback | head tamper at final readback; preserve original fault, prior ack and bounded partial bytes |
| ack_send_short | actual send short return no accepted new pointer; preserve original fault, prior ack and bounded partial bytes |
| ack_send_late | send returns afterW explicit ambiguity/frozen old pointer; preserve original fault, prior ack and bounded partial bytes |
| ack_receive_late | matching ack received atW cannot promote; preserve original fault, prior ack and bounded partial bytes |
| owner_retention_error | retention failure preserves previous pointer; preserve original fault, prior ack and bounded partial bytes |

## Appendix C. Exact new provenance shape and preservation map

Add only `provenance` to the existing compact reference schema. It is an exact producer-keyed map (worker/reconcile only); each retained producer has `{accepted_head,previous_checkpoint,previous_head,intended_successor}`. The first is a strict file record; the next two are null together at first accepted generation, otherwise strict records for the previous acknowledged generation/head. `intended_successor` is null or exactly `{binding,request_id,sequence,current,previous,head,completed}` copied from the credential-validated pending notice and bound to this context/producer. Validate process/type/time/next-sequence and all records with the same strict validators. The accepted checkpoint remains in existing `checkpoints`; it and accepted_head must correlate exactly. This is externally retained provenance, not authority inferred from disk. Keep all bounds in §4 and uncertainty decisions in §6. The compact reference is exactly s1-progress-reference/v2; current consumers reject old v1 or mixed provenance shapes. Checkpoint is exactly s1-verified-progress/v2 with required diagnostics as defined in section6; context/head/notice/ack labels remain unchanged. Historical v1 files remain immutable and are not reinterpreted as v2.

The plan observations preserve every current source/test-method assertion AST and declaration. IMPLEMENT must produce the after-map, keep all old assertion expressions and 526 logical cases (six mapped IDs), append only these declared methods/cases, and preserve the old037–046 evidence. Strengthening existing scenario/controller records and accepted-head status assertions is additive. No additional old semantic-assertion edits are authorized.

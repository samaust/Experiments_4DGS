# Plan049 Correction015 transitive source-closure audit 004

**Verdict: FAIL under Addendum015 authority record23. No source-edit, test, admission, diagnostic, aggregate, or launch clearance.** The exact Addendum015 SHA-256 is `f679493e758957003c6af14668a15168d8b3a5f2c6357c972a1b252f6401ad5a`, independent plan review006 is `66b3aa6af5e2660b99e4c2288454d5dc8bce90b220ee8a33fa2fa79555134519`, and the Main adoption record is the `status.md:92` entry at `51d883601f19fd67c40774b205845a60e42adb3b7c39c409b955a9a539fe4b78`. Those three hashes matched the bytes read for this audit. The review passes plan wording only. The current source and adopted inventory do not meet the required transitive path, command/environment, or numeric whole-ledger proof.

## Selected entry, closure boundary, and disposition

The selected child remains `ARGV=['.local/envs/stg-colmap/bin/python','-B','-']`, with exact 200-byte stdin SHA-256 `4a05322d55f9a6e13343c93e971be5b202b242d296453f7d80005db8533b8fd4`; that stdin calls `runpy.run_module('vipe_benchmark.s1_validation_runner',run_name='__main__',alter_sys=True,init_globals={'STDIN_PYTHON_ARGV':tuple(sys.argv)})`. The ordered suites are `s1_semantics,s1_recovery,backends,contracts,component_recovery,execution,budgets,supervisor,review_annotations`. Diagnostic focus is `supervisor.HelperSessionTests`; the selected probe uses `-B -m vipe_benchmark.s1_validation_runner --helper-probe`; six literal direct-script suite/selector pairs are at `tests/test_vipe_benchmark_s1_recovery.py:2300-2311`. The 69 conservative source paths in the hash appendix were reread and all matched audit003, including `s1_cpu_helper.py`, `s1_validation_runner.py`, selected test files and their import closure. This is a static source boundary, not a proof that every import-reachable definition executes. Audit001's actual-versus-unselected creator disposition remains applicable to these unchanged bytes: capture Popen; supervisor Popen wrapper; `Owner.spawn`/`FaultOwner.spawn` posix-spawn and nested descendants; fixture/direct-script launch wrappers; the native owner thread and three budget-test `Thread.start` sites are selected. The selected callsites reserve before create/start and bind/ack afterward, but the addendum011 exact owner/operation protocol and retirement proof are not implemented. Unselected `nvidia-smi`, runtime setup, native S3 and transfer-proxy creator definitions are not promoted to selected invocations; the runner patches both GPU-reading entrypoints. A census cannot prove OS-wide containment.

## Eight typed path domains and corrected direct-R map

Let `R=ROOT/docs/resolve-blocker/plan031-progress-20260922` and `A=R/{kind}-049-{index:03d}`. The `:03d` notation means minimum width three, no truncation. Type is assigned by exact producer and slot, not by a common physical prefix. A canonical direct child of `R` is never an `attempt_path` merely because it is in the same run directory.

| Domain | Exact selected values / provenance | Audit disposition |
| --- | --- | --- |
| `attempt_root_path` | Driver `launch-049-exec.py:109,122` constructs `A`; capture's positional directory argv is exactly `A` (`s1_validation_capture.py:25-29,103-110`). | Unique capture-output root only; current code has no eight-type slot renderer. |
| `attempt_path` | Capture's `A/{stdin.py,runner.py,capture.py,process-stdout.log,process-stderr.log,stdout.log,stderr.log,receipt.json,execution.json}` and exact output records (`launch-049-exec.py:204`, capture `:29-49,79-99`). | Strict descendants of `A`; current path creation alone does not prove canonical parent/vacancy/length for all slots. |
| `repository_path` | Fixed executable/module/test and `sys.path` paths under `ROOT`: driver `ROOT/'scripts'` at `:15`, interpreter and capture module at `:135`, source manifest at `:118-131`; `nested_worker_code`'s `scripts` and `tests` entries from helper-fixtures `:899-907`; L35 test-module path; the six direct-script test paths. | Module/test/selector role only; final post-edit `-m` hashes and exact rendered templates remain unavailable. |
| `fixture_temp_path` | Retained `SupervisorTests.temporary` and `self.root/'output'` (`tests/test_vipe_benchmark_supervisor.py:17-36`); L35 `with TemporaryDirectory()` owner and its marker/release descendants (`:1657-1666`); the other selected TemporaryDirectory callsites enumerated in audit003. | Require retained exact owner, captured effective base, immediate-child/descendant proof and concrete random suffix; a host `/tmp` prefix is insufficient. |
| `run_evidence_path` | Direct-R ledger `.job-ledger-{kind}-049-{index}.{jsonl,lock}` (`s1_helper_session.py:42-49,84-109`), `launch-{identity,admission,note}` (`launch-049-exec.py:104,205,238`), `main-session-proof` (`:223`), Main event records, and `driver-049-{kind}-{index}-{exec-start.json,stdout.log,stderr.log}` from prefix `RUN/('driver-049-'+suffix)` (`:203-204,237,256`). The ledger/note paths also flow through `S1_JOB_LEDGER`/`S1_OWNED_ROOT_NOTE` into capture/helper environment. | These are **siblings of `A`**, correcting audit003. Current source lacks a complete exact-slot/phase/effective-environment authority record. |
| `run_status_path` | Exactly `R/status.md`; Main-only serialized status/adoption, never a child-command path. | Read as audit evidence at the bound hash above. Driver's `implementation-status-049.md` is a different fixed read-only input. |
| `run_readonly_input_path` | Addendum015 Table 1's 34 fixed direct-R name/hash rows plus its self-reference, with role classification below. | **FAIL: the selected `session_proof()` dereferences `R/authorization-049-session-proof-001.md` at `s1_validation_contract.py:526-528`, SHA-256 `6ee2d0f899c6ee20de96415079d9aa07900b51f2321ef37d20af5e7e171bd755`, but that basename is absent from closed Table 1.** It is not evidence, status, attempt output, repository authority, or fixture temp. Exact hash checking inside source does not create a permitted path type. |
| `repository_authority_path` | Exactly `AGENTS.md` SHA-256 `3d09a19b0bf8e4bfcf7c25f5b001a769f2cce372a425fc1dd1a14fc299ef620f` and `plans/plan_049.md` SHA-256 `89d1f634ad2407b02558ff9c030d4a4f12f8f4ab010c93e2cf532876564afe7e`. | Both matched; neither can be relabeled as executable `repository_path` or selected from argv/environment. |

The missing session-proof authorization is a **plan-inventory defect** requiring a newly reviewed exact Table 1/path-domain correction and adoption before source closure could pass. No audit may silently expand the allowlist. Table 1 membership grants read/hash permission only: the selected driver `:220-221` still binds only Corrections001-015 and addenda001-003/006, not every Table 1 proposal. `authorization-049.md`, the ancestor authorization and the source-checked driver/dispatch are current launch inputs; `implementation-status-049.md` is a frozen historical snapshot. Corrections001-015 and addenda001-003/006 are the existing ordered source-bound authority chain described by Main's record20 adoption in `plan031-session-proof-wrapper-20260923/status.md:53`. Addendum011 is adopted record20, Addendum013 record21 (`:62`), Addendum014 record22 (`:67`), and Addendum015 record23 (`R/status.md:92`) **for the staged audit scope only**. Addenda004/005 are rejected historical proposals; 007-010/012 are unadopted historical proposals. A hash match on any historical or proposed input does not elevate it to operative authority. Source does not yet append records20-23 to its `addenda` binding, so the future command/authority snapshot requires a reviewed exact-source correction.

## Current and legacy evidence grammar

Addendum015 permits the closed current-kind/index direct-R families: three `launch-{identity,admission,note}` JSON records; `driver` exec-start and two logs; two ledger extensions; session proof; session `{event,send,poll,terminal}-{sequence}`; **eight** typed start/terminal forms (`main-launch-attempt-`, `main-launch-`, `main-attempt-`, `main-` times `{start,terminal}`); admission and launch preparation; process and final preflight; launch state; cleanup; diagnostic outcome and timestamp correction (diagnostic only); and kind-qualified storage. Every current index is positive decimal with minimum width three and no truncation, sequence is Main's exact nonnegative ordinal, and creation is phase-specific with exact canonical parent `R` and exclusive vacancy at that boundary. Existing kindless `main-storage-049-{index}.json` is **read-only diagnostic history**; all new storage paths require `main-storage-049-{kind}-{index}.json`.

The selected driver high-water scan at `launch-049-exec.py:80-102` recognizes `launch-{identity,admission,note}`, driver exec-start, session proof, session **event** only, ledger extensions, and the exact eight typed start/terminal variants from `main-(?:launch-)?(?:attempt-)?(?:start|terminal)-049-{kind}-{index}.json`. Its only legacy untyped scan names are `main-launch-attempt-start-{legacy_index}.json` and `main-launch-terminal-{legacy_index}.json` (`:94-101`), opened only to infer historical kind/index. It does **not** scan session send/poll/terminal, preparations, preflights, launch-state, cleanup, diagnostic outcomes/corrections or kind-qualified storage. Addendum015 recognizes those families as historical high-water inputs; the source scan therefore cannot establish a complete current candidate from every permitted prior evidence state. It also calls `initialize_job_ledger` at `launch-049-exec.py:58` **before** this high-water scan and before Addendum015's read-only index/OS/whole-ledger precheck. Source still needs a pre-mutation exhaustive grammar scan, content/phase checks, candidate-specific size proof and failure path preserving H charge.

Read-only enumeration at this audit saw five diagnostic007 exact-evidence names (`launch-identity`, launch preparation/state, process and final preflight), no diagnostic008 evidence name, and the two legacy untyped index001 names. The status/adoption record calls diagnostic007 retired and diagnostic008 uncleared. Thus the **current candidate is diagnostic008, `d(index)=1`**, subject to a fresh Main/driver preflight; this observation is not admission or a global attempt-count cap.

## Command, environment and host ceilings

The selected generated commands and child creation sites are the unchanged audit003 source map: capture's fixed `ARGV`/stdin; driver `execve` to `-m vipe_benchmark.s1_validation_capture`; `Owner.spawn` and `FaultOwner.spawn` `-m` workers; `SupervisorTests.command(code)` and its fixture root; selected cache-worker f-string; `nested_worker_code(20,False)` and `(10,True)` with two repository `sys.path` slots and a grandchild; L35's runtime `-c` marker/release paths and nested child; three budget thread starts; helper-probe; saved-original-Popen test seams; and six direct-script atomic suite/selector pairs. Audit003 identifies the literal `-c 'pass'` and `-c 'import time; time.sleep(10)'` hashes. These source bytes have not changed. No canonical static template renderer with unique typed delimiters and finite per-slot maxima exists for all paths, especially L35's random fixture root and caller-supplied inline `code`; no independent rendered-versus-actual executable/argv/cwd/flags comparison precedes every reservation and OS create. The direct-script pairs and selected imports are listed in audit003 and remain hash-bound in the appendix. This is a command-byte closure FAIL, not a claim that the nested child is absent.

In-process, read-only stdlib host interfaces returned `os.sysconf('SC_ARG_MAX')=2,097,152`, `os.sysconf('SC_PAGE_SIZE')=4,096`, `resource.getrlimit(RLIMIT_STACK)=(8,388,608,-1)` and 8-byte pointers. `/proc/sys/kernel/pid_max` (kernel limit metadata, not a process inspection) read `4,194,304`, giving at most seven PID decimal digits for this observation. Installed `/usr/include/linux/binfmts.h` SHA-256 `d1cc61064593aac83ec6ec73efd968a673a5cac74d984aedaddb6883d18a1834` gives the reviewed Linux per-string rule `MAX_ARG_STRLEN=PAGE_SIZE*32=131,072` bytes **including NUL**. Future preflight must reacquire these limits in the already-counted Main/driver process and fail closed if an interface/rule is unsupported; this audit's values are not future admission metadata. No `getconf` or helper was launched.

Under the proposed 16,384-byte executable+argv descriptor, 1,048,576-byte full environment and 4,096-entry limits, a deliberately loose Linux x86_64 combined vector estimate is `1,048,576 + 2×4,096 + 16,384 + 16,384 + 8×(16,384+4,096+2) = 1,253,392` bytes, leaving 843,760 below observed `ARG_MAX` before any platform-specific overhead; the margin cannot replace checking the actual rendered vector. Every argv and every encoded environment `key=value\0` must independently fit 131,072 bytes. The aggregate 1 MiB environment cap permits a single larger entry, so it does not imply this per-string condition. Current driver builds `env=dict(os.environ,**settings)` at `:136-138`, records only `settings` in expected bindings/note at `:228,237`, then adds `S1_OWNED_ROOT_NOTE`, hash and `S1_JOB_LEDGER` at `:239-241`; capture copies ambient `os.environ` and overlays `ENVIRONMENT`/run-directory at `s1_validation_capture.py:36-44`. The complete effective environment is neither size-checked nor bound as one immutable snapshot handed unchanged through all selected creates. The Main handle has a **proposed** 16,384-decimal-digit maximum and same-handle retirement policy; current source checks only positive int (`launch-049-exec.py:65-78`, contract `:521`), so the width guard is absent. An exact returned handle wider than policy must fail before ADMIT while H remains charged; no guessed handle or alternate retirement is allowed.

## Whole-ledger event accounting: no numeric upper bound

Current `_job_line` (`s1_helper_session.py:36-40`) serializes sorted compact JSON plus one newline, with 64-hex previous and row hashes. `JOB_LEDGER_LIMIT=8,388,608`; `append_job_event` at `:185-207` guards each append, not the prospective total. `_job_state` at `:116-183` accepts the event names below but does not enforce exact `data` key sets. The selected emitters and their current field shapes are:

| Current event | Current selected data fields / emitting line | Required finite count/max-line result |
| --- | --- | --- |
| `attempt-open` | `kind,index,h,driver_pid`; `initialize_job_ledger:88` | Exactly one. At a max-width 32-character UTC string its diagnostic line is `340+d(index)+d(driver_pid)`. Candidate008 and observed seven-digit PID bound give **≤348 bytes** for this current schema. Driver does not precheck this before sidecar creation. |
| `main-handle` | `session_id,start_event_sha256`; driver `:78` | At most one. Current sequence-one line is `392+d(session_id)`; proposed 16,384-digit policy gives **≤16,776 bytes** only after an actual width guard. |
| `session-terminal` | `_job_state:126-128` accepts `session_id`; no selected project emitter found. | At most one by state; final exact producer, field set and canonical line maximum unknown. |
| `root-reserved` / `descendant-reserved` | `token,role,label,creator` and additionally `root` for descendant; `reserve_job_root:220-235`. | One per reservation key under proposed one-shot rules, but complete selected aggregate/focus/direct-script maxima and bound on label/creator fields not proved. |
| `root-bound` / `descendant-bound` | `token,identity,handle{kind,object_id}`; `bind_job_root:239-248`. | One per successful bind; identity/handle exact field maxima and coexistence with failures unknown. |
| `root-wait` | `token,terminal,handle_object_id`; `wait_job_root:250-261`. | One per root wait under proposal; terminal union and error/result sizes are not closed. |
| `root-retired` | `token,terminal`, optionally `method`; `wait_job_root:265`, `finalize_waited_job_root:281`, pidfd retirement `:329`. | State permits at most one per root, but failure/replay operation-key proof and terminal/method bounds absent. |
| `descendant-creator-ack` / `descendant-ack` | `token,root,creator,identity,census` (`:738`); or `worker_pid,child_pid,census` (`:304`). | Creator ack once per child; L35 ack once for its selected descendant. Census row bound/schema and selected max count not proved. |
| `descendant-retired` | `token,terminal,handle_object_id` or `token,method,identity`; `wait_job_root:259`, pidfd `:325`. | State at most one per child, but disjoint terminal branches and line maxima not proved. |

Addendum011's future wait claim/result, signal intent/result, pidfd pin/close receipts, replay and uncertainty records have **no final canonical event names, exact data schemas, field maximum bytes or per-operation maximum counts in current source**. A one-shot rule is a proposal; there is no implemented operation-key ledger or matching-receipt readback to exclude repeated rows, and unknown outcomes must remain charged. Selected fixed counts (249 methods, 1,028 callbacks, 42 scenarios, six direct scripts) do not by themselves bound all nested creator/failure operations. `session-terminal` is also not a current selected emission. Consequently the required disjoint formula is

`L = L_attempt-open + L_main-handle + L_session-terminal + Σ_current_lifecycle_kind(N_kind × M_kind) + Σ_planned_operation_kind(N_kind × M_kind) + L_other_fixed`.

For candidate008, the two **conditionally bounded current fixed rows** contribute at most `348+16,776=17,124` bytes including their JSON framing, two 64-hex hashes and newlines, leaving `8,388,608−17,124=8,371,484` bytes for every other nonoverlapping row. This is **not** a whole-ledger maximum: the other terms are undefined, and the current first two bounds rely on guards not yet present. No concrete integer `L≤8,388,608` can be certified for aggregate, diagnostic focus or direct scripts. The exact index may be recomputed for every candidate without a global index/attempt cap; a too-large prospective whole attempt must stop before creating its sidecar. No cap increase is authorized.

## Preserved boundary and minimal intervention

The adopted scope remains nine editable source paths, 78 source members, 249 methods, 1,028 callbacks, unchanged assertions, ordering, error precedence and behavioral deadlines, serial CPU-only execution, `B+max(1,H)≤8`, 150 GiB artifacts, 64 MiB memo and no operational time ceiling. Diagnostic005 is failed history,006 lost/unused,007 retired,008 an uncleared candidate. This audit proposes no change to those limits. To make a later PASS possible, first obtain a reviewed/adopted exact inventory correction for the omitted session-proof authorization; then supply finite typed command/path/environment renders, exhaustive pre-bootstrap high-water/host checks, closed event schemas and per-selected-path one-shot maxima with an independently recomputed integer ≤8 MiB. These are blockers, not an instruction to edit under record23.

## Exact inputs and read-only method

All listed hashes below were recomputed from current bytes. The path inventory in Table 1 has **34/34 fixed SHA-256 matches**; its self-reference is the Addendum015 hash above. The selected 69-source appendix has **69/69 matches**. Hashes bind this audit only; final post-edit module bytes and random temporary path sizes are unknown. Source reading used `rg -n`, `sed -n`, `cat`, and stdlib-only Python `pathlib`, `re`, `hashlib`, `os.sysconf`, `resource.getrlimit` and integer arithmetic. Directory enumeration was limited to names in `R`; no live process or pidfd was inspected. No project code import/execution, test, fixture, source edit, admission, launch, aggregate, external `getconf`/helper, or prompt access occurred. The sole write was this audit004 document.

### Governing and host inputs

| Path | SHA-256 |
| --- | --- |
| `AGENTS.md` | `3d09a19b0bf8e4bfcf7c25f5b001a769f2cce372a425fc1dd1a14fc299ef620f` |
| `plans/plan_049.md` | `89d1f634ad2407b02558ff9c030d4a4f12f8f4ab010c93e2cf532876564afe7e` |
| `docs/resolve-blocker/plan031-progress-20260922/status.md` | `51d883601f19fd67c40774b205845a60e42adb3b7c39c409b955a9a539fe4b78` |
| `docs/resolve-blocker/plan031-session-proof-wrapper-20260923/status.md` | `3ed7209af98d0791ce25b1f47c20e8d3c2a1f5d8658eba30fd9de9cc0fbd5085` |
| `docs/resolve-blocker/plan031-progress-20260922/authorization-049-session-proof-001.md` | `6ee2d0f899c6ee20de96415079d9aa07900b51f2321ef37d20af5e7e171bd755` |
| `docs/resolve-blocker/plan031-progress-20260922/plan049-correction-015.md` | `a3242ed06131aa9ca00bc05180805c8d5bf5ea8d965919b92054154f10a00bab` |
| `docs/resolve-blocker/plan031-progress-20260922/plan049-correction-015-source-scope-addendum-006.md` | `d165e8412005fcbabdf610ad62840c569d7688e01a6f65e08722d8bff370351f` |
| `docs/resolve-blocker/plan031-progress-20260922/plan049-correction-015-source-scope-addendum-011.md` | `18e0d807a074fdb11817251b459db54ea3b0725161222da824b86c5ebfe52d65` |
| `docs/resolve-blocker/plan031-progress-20260922/plan049-correction-015-source-scope-addendum-013.md` | `14398e0974258104018a366f5d9a9d653e69c9efb894baefe73b498542b1c78c` |
| `docs/resolve-blocker/plan031-progress-20260922/plan049-correction-015-source-scope-addendum-014.md` | `0d630af7c3da1274efc78fb30d859212d3cedbf851bbeabc814d0865ccb82ea1` |
| `docs/resolve-blocker/plan031-progress-20260922/plan049-correction-015-source-scope-addendum-015.md` | `f679493e758957003c6af14668a15168d8b3a5f2c6357c972a1b252f6401ad5a` |
| `docs/resolve-blocker/plan031-progress-20260922/plan049-correction-015-source-scope-addendum-014-independent-review-004.md` | `091244dc21eee11131a03a81f29facc9497f4ed536da3f9e282caece417efaf2` |
| `docs/resolve-blocker/plan031-progress-20260922/plan049-correction-015-source-scope-addendum-015-independent-review-006.md` | `66b3aa6af5e2660b99e4c2288454d5dc8bce90b220ee8a33fa2fa79555134519` |
| `docs/resolve-blocker/plan031-progress-20260922/plan049-correction-015-transitive-source-closure-audit-003.md` | `7b691be6e86b999171fee345e1a2d76ef13cb101f8a98148c3ba8f15a3bbdfdc` |
| `docs/resolve-blocker/plan031-progress-20260922/plan049-correction-015-transitive-source-closure-audit-003-independent-review.md` | `fbc1d1a89b24684deca7a6711a03d75e58fa329d92007cc6c161f1c57eba17d7` |
| `/usr/include/linux/binfmts.h` | `d1cc61064593aac83ec6ec73efd968a673a5cac74d984aedaddb6883d18a1834` |

### Table 1 direct-R read-only inventory

| Exact basename | SHA-256 | Role for this audit |
| --- | --- | --- |
| `implementation-dispatch-049.json` | `d7177d2dae0d553321863481af72647f210557087c54c3b802c8317f572937be` | Source-bound launch dispatch; comparison input |
| `implementation-status-049.md` | `7a3085aed5b7bfcd5ace290d91d875feb738da0764319c8acde894647fb4f0e0` | Frozen historical implementation snapshot; source-bound comparison |
| `authorization-049.md` | `9ba97b6487d459eea268c1e0d0bac5000a1d5601162ec490ddb2533ec4efc31f` | Current Plan049 authorization note |
| `authorization-049-ancestor-process-001.md` | `734fc8fc67f2cc7f60ead6eba279b797abff47bbf32602cf5106e07ef540605d` | Current source-bound ancestor authorization |
| `launch-049-exec.py` | `be9cdd762b866204eb77aa58e18ca8ed4e48b68df625313fda52610caa90bc1e` | Selected driver source, not adoption by itself |
| `plan049-correction-001.md` | `720da1670cfc9d3f4bd5d8fbb01ddcbf3c91be2b64fad886a8d33f937ca76b0c` | Adopted Corrections001–015 chain; driver-bound |
| `plan049-correction-002.md` | `d5b852ba16ec0b64b2c93b39ef178629cf7dd679bc4c195d131d9c979e2ccea1` | Adopted Corrections001–015 chain; driver-bound |
| `plan049-correction-003.md` | `1e08bf6398f5a040bd79aa33ff63cb5d989142aa17f9fc2538e660416868dea0` | Adopted Corrections001–015 chain; driver-bound |
| `plan049-correction-004.md` | `011cd7dc04762d7c85c265017a5e8f3979a92d77f6e27b514a96f5f72395e384` | Adopted Corrections001–015 chain; driver-bound |
| `plan049-correction-005.md` | `dfb606c58dc192111469d004c64d6e4d861d8b4a75fe4ad944bb6fe242a7dbec` | Adopted Corrections001–015 chain; driver-bound |
| `plan049-correction-006.md` | `9bfcc162a1fb85b857d1b643022ee87986747dee3c17bbf2d97ffd58974725b3` | Adopted Corrections001–015 chain; driver-bound |
| `plan049-correction-007.md` | `c7ac7c902e74fff0727da145035a5f96d18af933aea463a7c7e072814d2a1b16` | Adopted Corrections001–015 chain; driver-bound |
| `plan049-correction-008.md` | `e68129133349fbbecc25e725025c0cda833c7ab149aaacad0ff05ead4737cf91` | Adopted Corrections001–015 chain; driver-bound |
| `plan049-correction-009.md` | `c4298d6c63f4c96ca416b583d98041e3b5f8c909feeea01c4885595616d82fa6` | Adopted Corrections001–015 chain; driver-bound |
| `plan049-correction-010.md` | `ac9a4d3f392ad60dfa308622d25f0fe8c7dc07d0dab7139b8275be96050f9d6a` | Adopted Corrections001–015 chain; driver-bound |
| `plan049-correction-011.md` | `bdc431bc354e0c8cb11c0515d7ed1ebea4e529abf2f3ae9e65b9e280f1fb558e` | Adopted Corrections001–015 chain; driver-bound |
| `plan049-correction-012.md` | `2cdf540e39fccb28a63b7b385b2f67f13f09fb9cd7b3697e5b2ee6cf162d02e9` | Adopted Corrections001–015 chain; driver-bound |
| `plan049-correction-013.md` | `9e64e2b088822ba886c529b4482b4b00c7061ed1b1c43de2a3c449ffda279126` | Adopted Corrections001–015 chain; driver-bound |
| `plan049-correction-014.md` | `f874eb395b61a5c05f83418ab26c938d65884fed71e18c978f748ec47a13d557` | Adopted Corrections001–015 chain; driver-bound |
| `plan049-correction-015.md` | `a3242ed06131aa9ca00bc05180805c8d5bf5ea8d965919b92054154f10a00bab` | Adopted Corrections001–015 chain; driver-bound |
| `plan049-correction-015-source-scope-addendum-001.md` | `f08fad270dcea9596d1a4c45a41d13f2f5675f7d51fe464699a1ec4046f0b45e` | Adopted records16–19; driver-bound |
| `plan049-correction-015-source-scope-addendum-002.md` | `9a175afcdce5b31c6fa17543f1fe7be6183095cb2f5c6beec0621ce7ad33511e` | Adopted records16–19; driver-bound |
| `plan049-correction-015-source-scope-addendum-003.md` | `92e69b78659baa45da6e74c439a0bc18d14450c3d88592aa46ba8d8495d3dd8a` | Adopted records16–19; driver-bound |
| `plan049-correction-015-source-scope-addendum-004.md` | `e56795a0b241c3d0a0e11622d8daa828e151227199ce536d111cf4a9e7663b26` | Rejected historical proposal; read-only only |
| `plan049-correction-015-source-scope-addendum-005.md` | `ae085276ea0b8a96b905ff7e53554464a578ae1dae69fa4f665509309c316cbb` | Rejected historical proposal; read-only only |
| `plan049-correction-015-source-scope-addendum-006.md` | `d165e8412005fcbabdf610ad62840c569d7688e01a6f65e08722d8bff370351f` | Adopted records16–19; driver-bound |
| `plan049-correction-015-source-scope-addendum-007.md` | `48f32823d66bdf9d822c62289029015feb1dbeb1a55cc08156cf02f63577d492` | Unadopted historical proposal; read-only only |
| `plan049-correction-015-source-scope-addendum-008.md` | `eeeb2816a480ab6940ffc1e36321bcb1ee6f543b613d9f775d2f3a0175104737` | Unadopted historical proposal; read-only only |
| `plan049-correction-015-source-scope-addendum-009.md` | `dfbb0689e37f9d3cdf76f65a7124268285ecef6da44552b698418b07b1097f34` | Unadopted historical proposal; read-only only |
| `plan049-correction-015-source-scope-addendum-010.md` | `59d8127aeb6dffdbb5ae3e15da54beb4ac89338ea51bb339d7c30cbea66ac4dc` | Unadopted historical proposal; read-only only |
| `plan049-correction-015-source-scope-addendum-011.md` | `18e0d807a074fdb11817251b459db54ea3b0725161222da824b86c5ebfe52d65` | Adopted record20; audit authority, absent driver addenda list |
| `plan049-correction-015-source-scope-addendum-012.md` | `bc9b5c341194a9eaec93e021f148aee14cc06d60d6210cbdf0f5742e3613e1b1` | Unadopted historical proposal; read-only only |
| `plan049-correction-015-source-scope-addendum-013.md` | `14398e0974258104018a366f5d9a9d653e69c9efb894baefe73b498542b1c78c` | Adopted record21; audit authority, absent driver addenda list |
| `plan049-correction-015-source-scope-addendum-014.md` | `0d630af7c3da1274efc78fb30d859212d3cedbf851bbeabc814d0865ccb82ea1` | Adopted record22; audit authority, absent driver addenda list |
| `plan049-correction-015-source-scope-addendum-015.md` | `f679493e758957003c6af14668a15168d8b3a5f2c6357c972a1b252f6401ad5a` | Adopted record23 for audit only; absent driver addenda list |

### Rehashed conservative selected project-source inventory

| SHA-256 | Repository-relative source | Reach |
| --- | --- | --- |
| `be9cdd762b866204eb77aa58e18ca8ed4e48b68df625313fda52610caa90bc1e` | `docs/resolve-blocker/plan031-progress-20260922/launch-049-exec.py` | entry |
| `7bec9c071dacdc2197b6d9d8b7ca52ee4eb2ae6ad6781db72773781a2c37e601` | `scripts/basketball_alternatives_compare.py` | import |
| `b39315281f9a696e883e76c0b2b97977abcb9d147a74c28950f9542c07a5ce39` | `scripts/basketball_alternatives_protocol.py` | import |
| `e74e89d1aafea7c7a563c3afb78e13d686c4757a4978544ac9d95875364863ad` | `scripts/basketball_audit.py` | import |
| `a79dd48cbb111147d716c408bb2416cecd1bfb0327082edaa52f33adb827f85b` | `scripts/basketball_continuation_audit.py` | import |
| `2836d92478282df7be894a85abed1c45ac08ce6481344c47e08840105aac3679` | `scripts/basketball_pose_stability.py` | import |
| `2b6b490b340a2f6d6f32344089f4dcdda0f46283545a87c9629495a560e7ef4c` | `scripts/basketball_protocol.py` | import |
| `b00d6d9a3f16e80cf129cac684ff17149fed873e5291d80cf1b487ddfeba69fd` | `scripts/basketball_scale.py` | import |
| `60b5bf1dbeb6aa2fc3c89e33928512c64430e280f8c9f3a17bddfb8b241b0ea6` | `scripts/basketball_study.py` | import |
| `2c273cc7826390f62847e2218a5af573f8a5022df5ed4c8d8127d0ada71e7cf6` | `scripts/basketball_temporal_cloud.py` | import |
| `285d29198adda2045967dd79dcaedd1ff5b1e15dd1e920be6f8fce736aa28a70` | `scripts/basketball_temporal_geometry.py` | import |
| `2c9d4bf4973896c43263962f66e3b434728a38799ba9c08161e6c1e8d83674b5` | `scripts/basketball_vipe_worker.py` | import |
| `87c1204c695aeb004f3d4d507f14a8cee8a2469eae5b3c6023515f4e8a5db31f` | `scripts/edgs_source.py` | import |
| `8a28824220773678e9ba036dbab64b3a15eedae1c9f324c4ddd615c6aa47488f` | `scripts/triangulation.py` | import |
| `c85315fbe798b7b027f69aed6dc758496ddbb8cd7b2897901d7caeffa9abcc21` | `scripts/vipe_benchmark/__init__.py` | entry |
| `e34949d97a4d1f0165db3c0640e7ad30f3594ba9e2b78ed6087f51f9054a2ece` | `scripts/vipe_benchmark/access.py` | import |
| `79ba26254cea4c4fa0e9084c6f08fe1307aa06257139f0d13bf17f112c5f0abf` | `scripts/vipe_benchmark/aggregation.py` | import |
| `3f744704e4a4a7357c6e2ce9274572cf438d0f25450148f67ad61dc3c2ebf6ea` | `scripts/vipe_benchmark/annotations.py` | import |
| `22c80c8ec798fa9cc5fcab9f726dea0a52e91adf8b4df46c6f210fcf4f0c99c4` | `scripts/vipe_benchmark/auto_annotations.py` | import |
| `f87bff85926d97ca6cee0868b83237090c3015e5e24752c19ba87a1bc2b40419` | `scripts/vipe_benchmark/backends.py` | import |
| `2fbb10e6e2adb201c071945c050f5b19acf4d053f58e338ad71f9ec588943a45` | `scripts/vipe_benchmark/budgets.py` | import |
| `8660d808890bbc009dfb401b63cb2742b51ea63ac34ac2457086e4ef916b2ef4` | `scripts/vipe_benchmark/config.py` | import |
| `15950cbe4e4a34c68418b83aa8b5c482a5f284b9cc43a9d1f0f039b13b487d75` | `scripts/vipe_benchmark/contracts.py` | import |
| `3bcb7b09a805ea058bb1ce144836ff66975debf42677c64d2ba5bfca7c2f3da1` | `scripts/vipe_benchmark/diagnostics.py` | import |
| `17efaaf6a1b8fe9c823f9444782232c37dbcd3eb71c0c7cc377fd346a0fd43d2` | `scripts/vipe_benchmark/execution.py` | import |
| `6731caae7af2e561233fc0ac847f6111922ca0f2a01a2f2eacd150e81056641b` | `scripts/vipe_benchmark/files.py` | import |
| `563d853981d1adf554a205daaffab90ade4686a9ef7c6d55c14d0e9967ff9586` | `scripts/vipe_benchmark/geometry.py` | import |
| `6107dc7b3314638b9f9deb6542924e516e5b6446f25ce261c44ab06df107e5b8` | `scripts/vipe_benchmark/hf_auth.py` | import |
| `b4184a260710efc2d25dd65ab098af27f10cc0488eacd10bfee5133a616eb43c` | `scripts/vipe_benchmark/isolation.py` | import |
| `41e4d36d423aa52f35396c680ddee48182b1fcc2b08f407923731b0cfb9d218d` | `scripts/vipe_benchmark/ledger.py` | import |
| `ac1615a8610212f626627bda4fcdb74497642c0f5cbf93205a6e4117c51c84c3` | `scripts/vipe_benchmark/licenses.py` | import |
| `639a96f6db7de127c4ee3bc3f00489f42895dbf966a3d87c88cfb36344dbef84` | `scripts/vipe_benchmark/metrics.py` | import |
| `c2f8c30de3942ba7a6bf89cea51116694d3f1d42c6636bf5f28e4ec8e430242f` | `scripts/vipe_benchmark/motion.py` | import |
| `8e0f3d8dbb38a96bce59871ad19cb19a781ac7ccc13aee3125f239a0c4ef9fd8` | `scripts/vipe_benchmark/native_helpers.py` | import |
| `215f5fcea9a56b90486713bf1e5ac95f4d6fc649b22b3682bbf3c078c682960d` | `scripts/vipe_benchmark/neighbors.py` | import |
| `7fed08252faee19bc165c47d3ec71abe5fe8ac407629976cbf1fb49e5d369381` | `scripts/vipe_benchmark/prepare.py` | import |
| `2eea5f2745e7a3b08bd090a4b370569f62687123fdb27cfe7e94f69fb8e744eb` | `scripts/vipe_benchmark/reporting.py` | import |
| `18cf36442f912a43fac44ce6633589d81ed1709e4e56fee4090a39f4fd20717f` | `scripts/vipe_benchmark/review_annotations.py` | import |
| `89b0ca22c4730964feb00e60cebb371c654e3f8d339eac748448c468f75b0166` | `scripts/vipe_benchmark/runtime.py` | import |
| `28c5bf953ddea75ff6e74c515173aea18eb9667f9d2c6e8280aec0647287ef03` | `scripts/vipe_benchmark/runtime_capture.py` | import |
| `a363162262d9eaa26b5bd2b7122d87b926d6b027168eb19bf2e3e363de0d168e` | `scripts/vipe_benchmark/runtime_inventory.py` | entry |
| `8fa3f997115ae4d71e1459a23c8bfb71502e0088ea2a771cc3e03a3d67fe3918` | `scripts/vipe_benchmark/s1_clock.py` | import |
| `ef89d60a789a4a9c71a73be21df661cfcc507b57f9249ae4730512be7fed9139` | `scripts/vipe_benchmark/s1_cpu_helper.py` | import |
| `14ea47c7cc56418ae7a8e0e7aa442fb7664774d8a8f15b27c558ddcf69c679db` | `scripts/vipe_benchmark/s1_evidence.py` | import |
| `c3326fe0c738e0180b42289f03c52ff8586e9eef86fd242dc3ea3a013a72e106` | `scripts/vipe_benchmark/s1_helper_session.py` | import |
| `d53a203c64c1b78a19a720ba72aaa28efbe427333c704f81166a4151e485b89d` | `scripts/vipe_benchmark/s1_progress.py` | import |
| `4b4385d7aa0603566e46eed5bc674009748a05a21eed0ba34b10ac4e3ba4e257` | `scripts/vipe_benchmark/s1_recovery.py` | import |
| `478b20b2c8b00931ac7dc9db5ef65a9ca767ea8734ea7df070908c0daf40aa52` | `scripts/vipe_benchmark/s1_validation_capture.py` | import |
| `72f8a853bb1f6893045e26e3f77a76c0cfb3c351d749b79ac4332aeb0f2b5a0e` | `scripts/vipe_benchmark/s1_validation_contract.py` | import |
| `3735efbd70b1bd35f54344a034b90df144c52633a43d9de4fb80b5a5d80e9248` | `scripts/vipe_benchmark/s1_validation_runner.py` | import |
| `e2bdf1e49fd5bb47145dcbab8f789c9e56fb6a078cd58b9bd53e2dc4b1a841d6` | `scripts/vipe_benchmark/sam2_postprocessing.py` | import |
| `09f19b9ed5e476df3fdf104bf6cdac6c8e23f3c8027273e15bf98e60d2313afe` | `scripts/vipe_benchmark/sam3_memory.py` | import |
| `00c45fa0deab90ea924bebd291c0ebf75484483201fdcc3abe4058e039e97ca2` | `scripts/vipe_benchmark/scale.py` | import |
| `533a36658d2da0963d9d60dd647b552bd43cd5c43bb9268a7e4b123237d95c3d` | `scripts/vipe_benchmark/selection.py` | import |
| `03850f57c595e867f230a9fc6a76b90aa87284e8b6600b3e54b27bb6f37778de` | `scripts/vipe_benchmark/setup_recipes.py` | import |
| `dde6e2500cf09f8a2c4d508101a8a6b463069af181ed7f748ce0e99024148a67` | `scripts/vipe_benchmark/stages.py` | import |
| `2d04eea77a507392feda918c4003bd9ec599fe8d9325cb1e9feafdba143257ad` | `scripts/vipe_benchmark/supervisor.py` | import |
| `a0a3a39b32f02e389d6fd9ec49f6f13f87fcafd1d39533a2bc667ea04c3becbf` | `scripts/vipe_benchmark/toolkit.py` | import |
| `550b9a7d42998a22c558cd6dc215d7e69d648478edae33f2a8265662e25c9f8b` | `scripts/vipe_benchmark/transfer_proxy.py` | import |
| `f71af4270a9c0ea600622e094b2cf669a189271770921326dce1af96f2b877fa` | `tests/test_vipe_benchmark_backends.py` | import |
| `566f8599355b48c62d9d375b8cb9454472305820295065091445a2c56d178a2c` | `tests/test_vipe_benchmark_budgets.py` | import |
| `032ec8acefa12fdc0c12c8201396827ec201940ba7d60a16fc29f2d676334f99` | `tests/test_vipe_benchmark_component_recovery.py` | import |
| `3f805ac63594c446ec1aed48638ebad72900e8e95a0312a5630b5d14f53fa22a` | `tests/test_vipe_benchmark_contracts.py` | import |
| `c976d5da43f80f027096fc7e4b96f8dd61562e5b85666219560dfde2b7c01d56` | `tests/test_vipe_benchmark_execution.py` | import |
| `b9395d06c0ed3beeddd0616d40055c9833c4ac04b32e575a92123480606e8d51` | `tests/test_vipe_benchmark_review_annotations.py` | import |
| `202f20d1b4108680d802394ccd89c2a46da66abaa4108bc421fdd8b59a8a3b7a` | `tests/test_vipe_benchmark_s1_helper_fixtures.py` | import |
| `da27052c9e70c3defe02b9bba3d670a456af1034fb86b5e116346737b5f37018` | `tests/test_vipe_benchmark_s1_recovery.py` | import |
| `61335ea63f231cc1d0e9ed673f571604c647ce24fe9807e4febdb100406369e7` | `tests/test_vipe_benchmark_s1_semantics.py` | import |
| `c1f74f4fb121afb6a7639043a61fff81775b41e6de23ab3a66bfa039f7917188` | `tests/test_vipe_benchmark_supervisor.py` | import |

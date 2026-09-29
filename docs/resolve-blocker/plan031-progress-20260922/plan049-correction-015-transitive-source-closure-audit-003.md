# Plan049 Correction015 transitive source-closure audit 003

**Verdict: FAIL under user-authorized, adopted addendum014** (SHA-256 `0d630af7c3da1274efc78fb30d859212d3cedbf851bbeabc814d0865ccb82ea1`). Its independent plan review004, SHA-256 `091244dc21eee11131a03a81f29facc9497f4ed536da3f9e282caece417efaf2`, passes wording only. This audit does not establish a finite numeric maximum for every ledger event, so it cannot prove a whole selected attempt stays within **8,388,608 bytes**. The proposed 1,048,576-byte environment cap alone also permits an individual `key=value` string larger than the authorized Linux host's 131,072-byte per-string limit. No source edit or launch clearance follows.

## Exact selected entry and provenance domains

The fixed child is `ARGV=['.local/envs/stg-colmap/bin/python','-B','-']`; its 200-byte UTF-8 stdin, including final newline, is SHA-256 `4a05322d55f9a6e13343c93e971be5b202b242d296453f7d80005db8533b8fd4` and calls `runpy.run_module('vipe_benchmark.s1_validation_runner',run_name='__main__',alter_sys=True,init_globals={'STDIN_PYTHON_ARGV':tuple(sys.argv)})`. The runner selects the exact nine ordered suites `s1_semantics,s1_recovery,backends,contracts,component_recovery,execution,budgets,supervisor,review_annotations`; diagnostic focus selects supervisor `HelperSessionTests`, and the helper-probe child uses `-B -m vipe_benchmark.s1_validation_runner --helper-probe`. Six direct-script pairs remain the literal suite/selector records at `tests/test_vipe_benchmark_s1_recovery.py:2300-2311`. Audit001's reviewed source map and audit002's candidate template map are inputs, not closure PASS.

Addendum014's four path domains are **typed and mutually exclusive by slot**, even when canonical physical paths nest:

| Domain | Exact selected source and provenance | Static finding |
| --- | --- | --- |
| `attempt_root_path` | Driver `launch-049-exec.py:79-130` derives the reserved output directory from fixed `RUN`, kind and increasing index; capture's positional output-directory argv element is exactly that directory. | Only this argument may equal the canonical attempt root. It is under repository `docs`, but cannot be relabeled `repository_path`. Current source has no typed slot record or one-pass renderer. |
| `attempt_path` | Driver/capture outputs under the exact run directory: receipt, execution, stdin/runner/capture copies, stdout/stderr, and launch-log paths (`launch-049-exec.py:204,237,256`; capture `:25-31,46-49`). | Strict descendant check and finite encoded length must bind each value before create. An output path supplied by arbitrary argv is not authority. |
| `repository_path` | Fixed `ROOT`/`RUN` from reviewed `__file__`; capture executable and cwd; `-m` modules; `nested_worker_code`'s `scripts` and `tests` `sys.path` entries from helper-fixtures `__file__.resolve()` (`:899-907`); L35's test-module path (`tests/test_vipe_benchmark_supervisor.py:1660`); six direct-script test paths from `config.ROOT` and the literal pair table. | These can be checked against exact final project source hashes and module resolution. The direct suite/selector must be one atomic typed pair. Pre-edit hashes are history; final post-edit bytes are unavailable now. Repository slots cannot name the attempt root or its descendants. |
| `fixture_temp_path` | `SupervisorTests.setUp` retains `self.temporary` and uses `self.root=Path(self.temporary.name)` (`tests/test_vipe_benchmark_supervisor.py:17-21`); `SupervisorTests.command` uses `self.root/'output'` (`:28-36`). L35 creates a default `TemporaryDirectory()` at `:1657`, then embeds `Path(temp)/'ready'` and `Path(temp)/'release'` at `:1658-1666`. | These are returned-root/descendant values, not attempt paths. L35's `with` retains its context manager until exit, but the source binds only its returned string to `temp`; a future authority record must bind the retained exact owner, exact callsite, captured effective temporary base and immediate-child relation. The random suffix's concrete size/hash cannot be known pre-edit. |

Other selected `TemporaryDirectory` owner callsites were found at: `tests/test_vipe_benchmark_budgets.py:16`; `review_annotations.py:19,129,138`; `execution.py:27,42,55,71,91,104,118,134,145,163`; `component_recovery.py:16`; `contracts.py:68,80`; `backends.py:53,121,298`; `supervisor.py:19,1070,1317,1456,1483,1512,1657,1763,2046,2096,2155,2207,2244,2276,2316,2363,2430,2481,2538,2593,2713,2802,2983,3105,3267,3361,3849,4101`; `s1_recovery.py:181,520,545,596,1338,1363`; and `test_vipe_benchmark_s1_helper_fixtures.py:1551` (`dir=root`, owner retained in `objects`, finalizer detached). These line references are under `tests/test_vipe_benchmark_*.py`. Most supply disposable fixture data rather than a child-command path; the command-bearing owners identified above require exact owner/parent proof. A general host `/tmp` prefix alone is insufficient. If the environment-selected temporary base canonically overlaps the attempt/repository domain, addendum014 requires domain rejection, not relabeling.

## Selected creation and generated-command edges

The selected process creators remain capture's `Popen` (`s1_validation_capture.py:59`, `start_new_session=True`), supervisor's `create_owned_process(...,subprocess.Popen,command,...)` (`supervisor.py:445-447`), `Owner.spawn` and `FaultOwner.spawn` `os.posix_spawn(...,setsid=True)` (`s1_helper_session.py:1011-1015`; helper fixtures `:18-31`), direct-script/sentinel and fixture Popen/posix-spawn wrappers (helper fixtures `:589-615,879-906`), and nested descendants in the L35 and `nested_worker_code` programs. The selected thread creators are the one native joinable owner thread (`s1_helper_session.py:1249-1256`) and three budget-test `threading.Thread` starts (`tests/test_vipe_benchmark_budgets.py:342-353,369-379`). Reservation precedes those starts, with bind afterward; the pre-bind interval remains charged. The saved-original-Popen seams in supervisor/recovery tests call a real child under the common wrapper. `nvidia-smi`, setup/runtime commands, native S3 helpers and transfer-proxy threading are source hits without a proved selected invocation under the runner's patches/selected test branches.

Generated source/path slots include `SupervisorTests.command(code)`'s `self.root/'output'` and caller-supplied inline code (`tests/test_vipe_benchmark_supervisor.py:28-39`), the cache-worker f-string with the six fixed cache-variable names (`:51-70`), `nested_worker_code(seconds,parent_wait)` with selected `(20,False)` and `(10,True)` and repository `sys.path` values (helper fixtures `:899-907`), L35's test path plus marker/release temp paths and nested child (`supervisor` test `:1659-1666`), the six direct-script pairs (`s1_recovery` test `:1981-2021,2300-2311`), and driver/capture attempt-root/log paths. The direct-script suite/selector pairs are `s1_semantics/S1SemanticsTests.test_contract_rejects_missing_or_tampered_assignment`, `s1_recovery/ReceiptContractTests.test_typed_primitive_callbacks`, `backends/AssetAndDetectorTests.test_phrase_ambiguity_and_capacity_fail_before_casting`, `contracts/AccessTests.test_heldout_final_window_wrong_branch_and_pair_rejected`, `component_recovery/ComponentRecoveryTests.test_scope_validation_and_cumulative_cap_are_not_relaxed`, and `supervisor/HelperIntegrationTests.test_cleanup_failures`. Each resolves the suite to `ROOT/tests/test_vipe_benchmark_<suite>.py` and keeps its selector paired atomically. The nested grandchild literal `-c 'import time; time.sleep(10)'` is 27 UTF-8 bytes and SHA-256 `fd7850f365dfe06093452d15f5d71327f6a24646c4a264b391e47b0a83a33251`; `-c 'pass'` is 4 bytes and SHA-256 `d74ff0ee8da3b9806b18c877dbf29bbde50b5bd8e4dad7a3a725000feb82e8f1`. Static source does not expose a reviewed canonical renderer, uniquely delimited literal templates, per-slot finite maxima or exact static-byte contributions for all generated programs, so no exact worst rendered descriptor can be calculated for each selected template. The future renderer must independently compare complete executable, argv, `-c` bytes, cwd, flags and the same complete environment before reservation and just before OS create; `s1_helper_session.py:718-739` and direct capture do not currently do so.

Selected in-process AST `exec(compile(...))` slices are at `tests/test_vipe_benchmark_s1_recovery.py:1025-1061,1127-1137` (driver `main` admission/handoff `If` nodes, `local_identity`, `main.body[-2:]`, and three `local_identity(` comparisons) and `tests/test_vipe_benchmark_supervisor.py:4191-4200` (first `Try.body[:4]` of `monitored_call`). The test scopes mock the `os.execve`/lifecycle seams; these are not extra real child creates. Positional slices must be rebound to final exact source and rejected if their AST shape changes.

## Input caps versus authorized host limits

Read-only host metadata: `uname -s/-m` = Linux/x86_64; `getconf ARG_MAX` = **2,097,152 bytes**; `getconf PAGE_SIZE` = **4,096 bytes**; shell stack limit `ulimit -s` = **8,192 KiB**. The installed `/usr/include/linux/binfmts.h` (SHA-256 `d1cc61064593aac83ec6ec73efd968a673a5cac74d984aedaddb6883d18a1834`, lines 11-16) gives `MAX_ARG_STRLEN=PAGE_SIZE*32`, hence **131,072 bytes for one argv or environment string including its NUL**. The host metadata is an observation at this audit; it is not a runtime admission sample.

The proposed 16,384-byte canonical executable-plus-argv descriptor makes every individual argv string shorter than 131,072 if its encoding honestly includes every byte. For the **complete** environment, 1,048,576 key/value bytes across ≤4,096 entries does **not** imply `len(key)+1+len(value)+1≤131,072` for every entry. A single legal-under-proposal 1,048,576-byte value violates the kernel per-string ceiling. Addendum014 permits fail-closed rejection; the future gate needs this explicit per-string check before reservation. The source has none. Using intentionally loose maxima, `argc≤16,384`, `envc≤4,096`, 8-byte pointers, at most 16,384 argv payload bytes and NULs, and environment `key=value\0` framing ≤1,048,576+2×4,096, the combined upper bound is **1,253,392 bytes** (`1,048,576+8,192+16,384+16,384+8×(16,384+4,096+2)`), leaving 843,760 below observed `ARG_MAX`. This checks a conservative combined budget only; it does not fix the per-string failure or prove an actual invocation fits. The same OS-byte, string and combined checks must be applied to `Popen`, `posix_spawn`, and driver `execve`, with executable path and `argv[0]` distinguished and no ambient-environment reread.

## Whole-ledger arithmetic: FAIL

The existing journal cap is `JOB_LEDGER_LIMIT=8*1024*1024=8,388,608` (`s1_helper_session.py:29`). `_job_line` at `:36-40` uses sorted compact canonical JSON plus newline and includes a 64-hex previous hash and a 64-hex row hash. The appender at `:185-207` checks `len(raw)+len(line)` before write, then fsyncs and rereads. This **per-append** guard does not give a whole-attempt maximum.

Disjoint event partition from `_job_state` (`:116-183`) and selected append callsites:

| Event kind | Maximum count in one selected attempt | Exact current serialized maximum under adopted proposed caps |
| --- | ---: | --- |
| `attempt-open` bootstrap (`initialize_job_ledger:84-109`) | 1 | Its max-width 32-character UTC serialization is `340+d(index)+d(driver_pid)` bytes for diagnostic or `339+d(index)+d(driver_pid)` for aggregate, where `d` is decimal digits. This term can use the actual candidate index at each preflight. The current driver calls bootstrap initialization at `launch-049-exec.py:58` before validating its resulting length against a prospective whole-ledger bound, so the current source does not implement that per-attempt check. |
| `main-handle` (`launch-049-exec.py:78`) | 1 | **Unproved**: with sequence 1 and max-width UTC, `392+d(session_id)` bytes. The Main tool's positive session id has no declared maximum decimal digits in selected source. |
| `session-terminal` (accepted by `_job_state:126-128`) | At most 1 by state machine; emitting source/field set is outside the selected project callsites | **Unproved**: no exact bounded final event schema/payload or selected producer was found. |
| `root-reserved`, `root-bound`, `root-wait`, `root-retired` | Each tied to selected B/H root creation and lifecycle, but maximum number of creates across all fixed tests/branches has not been derived | **Unproved**: addenda011/013/014 require new descriptor/owner/receipt fields; exact final field set, string bounds and canonical row maxima are absent pre-edit. |
| `descendant-reserved`, `descendant-bound`, `descendant-creator-ack`, `descendant-ack`, `descendant-retired` | Each tied to selected nested creator; L35 adds a distinct live-census ack. Maximum across focus, aggregate and six direct scripts has not been derived | **Unproved** for the same reasons, including census identity shape and future descriptor fields. |
| Planned wait-claim, signal-intent/result, pin-close/result, replay and uncertainty events of addendum011 | Not emitted by current source; counts for coexisting failure/replay branches are unavailable | **Unproved**: event names, exact field schemas, idempotent replay multiplicity and byte maxima require a reviewed bounded design. |

The exact nonoverlapping accounting form is `L = L_attempt-open + L_main-handle + L_session-terminal + Σ_kind N_kind×M_kind + L_other-fixed`. The first three terms are the fixed-session partition and are excluded from the lifecycle sum. `L_other-fixed` must enumerate any additional fixed event exactly once. A read-only status entry at `status.md:80-81` retires diagnostic007 and identifies **diagnostic008** as the next candidate; `status.md:90-91` says diagnostic008 remains uncleared. Thus `d(index)=1` for that specific candidate, giving diagnostic bootstrap `341+d(driver_pid)` bytes at the 32-character timestamp maximum. A later per-attempt preflight can substitute its then-current exact high-water candidate without imposing a global attempt count or index cap. The existing driver still needs a pre-bootstrap length check before calling `initialize_job_ledger`; bootstrap append failure is not a prospective whole-attempt proof. Neither `Σ N_kind×M_kind` nor `L_session-terminal` has a source-bound integer here; the Main handle and PID digit counts also require exact per-attempt binding or finite field limits. Therefore **no concrete integer `L≤8,388,608` can be derived** for the fixed aggregate, focus or direct-script paths. The current code's append cap can stop an overlarge attempt; it cannot turn the required proof into a PASS. The 249 methods, 1,028 callbacks, 42 scenarios and six scripts are selection counts, not lifecycle-event maxima. No cap increase is authorized.

## Hash binding, method and disposition

All paths are repository-relative except the host header. `HEAD=db485e99f160337c4812833619cdd1386fb7ebc1`; the working tree was already dirty. The nine editable paths below retain their exact pre-edit hashes. The 69 conservative reachable-project-source rows from audit001 were each reread and rehashed for this audit; all matched (full row list follows). A syntactic import row is a conservative read boundary, not proof its creator definition executes. These are pre-edit history, never final post-edit `-m` authority.

| Editable path | SHA-256 |
| --- | --- |
| `docs/resolve-blocker/plan031-progress-20260922/launch-049-exec.py` | `be9cdd762b866204eb77aa58e18ca8ed4e48b68df625313fda52610caa90bc1e` |
| `scripts/vipe_benchmark/s1_validation_capture.py` | `478b20b2c8b00931ac7dc9db5ef65a9ca767ea8734ea7df070908c0daf40aa52` |
| `scripts/vipe_benchmark/s1_validation_contract.py` | `72f8a853bb1f6893045e26e3f77a76c0cfb3c351d749b79ac4332aeb0f2b5a0e` |
| `scripts/vipe_benchmark/s1_helper_session.py` | `c3326fe0c738e0180b42289f03c52ff8586e9eef86fd242dc3ea3a013a72e106` |
| `scripts/vipe_benchmark/supervisor.py` | `2d04eea77a507392feda918c4003bd9ec599fe8d9325cb1e9feafdba143257ad` |
| `tests/test_vipe_benchmark_s1_helper_fixtures.py` | `202f20d1b4108680d802394ccd89c2a46da66abaa4108bc421fdd8b59a8a3b7a` |
| `tests/test_vipe_benchmark_supervisor.py` | `c1f74f4fb121afb6a7639043a61fff81775b41e6de23ab3a66bfa039f7917188` |
| `tests/test_vipe_benchmark_s1_recovery.py` | `da27052c9e70c3defe02b9bba3d670a456af1034fb86b5e116346737b5f37018` |
| `tests/test_vipe_benchmark_budgets.py` | `566f8599355b48c62d9d375b8cb9454472305820295065091445a2c56d178a2c` |

| Governing input | SHA-256 |
| --- | --- |
| `AGENTS.md` | `3d09a19b0bf8e4bfcf7c25f5b001a769f2cce372a425fc1dd1a14fc299ef620f` |
| `plans/plan_049.md` | `89d1f634ad2407b02558ff9c030d4a4f12f8f4ab010c93e2cf532876564afe7e` |
| `docs/resolve-blocker/plan031-progress-20260922/plan049-correction-015.md` | `a3242ed06131aa9ca00bc05180805c8d5bf5ea8d965919b92054154f10a00bab` |
| `docs/resolve-blocker/plan031-progress-20260922/plan049-correction-015-source-scope-addendum-006.md` | `d165e8412005fcbabdf610ad62840c569d7688e01a6f65e08722d8bff370351f` |
| `docs/resolve-blocker/plan031-progress-20260922/plan049-correction-015-source-scope-addendum-011.md` | `18e0d807a074fdb11817251b459db54ea3b0725161222da824b86c5ebfe52d65` |
| `docs/resolve-blocker/plan031-progress-20260922/plan049-correction-015-source-scope-addendum-013.md` | `14398e0974258104018a366f5d9a9d653e69c9efb894baefe73b498542b1c78c` |
| `docs/resolve-blocker/plan031-progress-20260922/plan049-correction-015-source-scope-addendum-014.md` | `0d630af7c3da1274efc78fb30d859212d3cedbf851bbeabc814d0865ccb82ea1` |
| `docs/resolve-blocker/plan031-progress-20260922/plan049-correction-015-source-scope-addendum-014-independent-review-004.md` | `091244dc21eee11131a03a81f29facc9497f4ed536da3f9e282caece417efaf2` |
| `docs/resolve-blocker/plan031-progress-20260922/plan049-correction-015-transitive-source-closure-audit-001.md` | `ff4b7caac5d64e39fd0d2b7aec360eed472d16ad234150c5211ca41a8b83a5a7` |
| `docs/resolve-blocker/plan031-progress-20260922/plan049-correction-015-transitive-source-closure-audit-001-independent-review.md` | `ba272430cdb3b3717aad45cf10d8bdc0e4a000b0b20216b17ebb2faa1ee09868` |
| `docs/resolve-blocker/plan031-progress-20260922/plan049-correction-015-transitive-source-closure-audit-002.md` | `bff30fce1eedaf7300ee7a43f9597ca7a4e47fc97230ad8914892de318707963` |
| `docs/resolve-blocker/plan031-progress-20260922/plan049-correction-015-transitive-source-closure-audit-002-independent-review.md` | `9d2b900e856e9ff00d0b0257b782adc18dc7a00a21e944914ce5b2a62ccb40b2` |
| `docs/resolve-blocker/plan031-progress-20260922/status.md` (candidate-index evidence) | `322ce2e0e9ae521421af5be97a73830e44d709d36a3b7da7b5dd261617746416` |
| `/usr/include/linux/binfmts.h` | `d1cc61064593aac83ec6ec73efd968a673a5cac74d984aedaddb6883d18a1834` |

Read-only tools: `rg -n`, `rg --files`, `sed -n`, `cat`, `sha256sum`, `git status --short`, `git rev-parse HEAD`, `uname`, `getconf`, `ulimit -s`, and `/usr/bin/python3 -B -` using only stdlib AST/JSON/hashlib for static parsing, byte arithmetic and hash checks. `/proc/sys/kernel/arg_max` was absent on this host; `getconf ARG_MAX` succeeded. No project code import/execution, test, fixture, process/pidfd inspection, diagnostic, admission, aggregate, launch or prompt access occurred. The only write is this audit003 artifact. Any runtime random path size and final post-edit module hash are unknown by design. Until finite template and all-event bounds, source closure remains **FAIL**, with no source or launch clearance.

## Rehashed reachable project-source rows

| SHA-256 | Project source path | Conservative reach |
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

# Plan049 Correction015 transitive source-closure audit 001

**Verdict: FAIL — static source closure and runtime clearance are withheld.** This is a read-only source audit under addendum011, not an implementation or a census. The current selected validation path contains a generated inline Python program whose final bytes depend on runtime temporary paths. Its bytes cannot be hash-bound before execution. The conservative source-import map also reaches external/native code whose process and thread behavior is outside this project's static source closure. No source edit, import, test, fixture, pidfd operation, diagnostic, aggregate, or process inspection was performed for this audit.

## Exact entry and selection

The contract in `scripts/vipe_benchmark/s1_validation_contract.py` fixes `ARGV=['.local/envs/stg-colmap/bin/python','-B','-']`. Its UTF-8 stdin is exactly 200 bytes, SHA-256 `4a05322d55f9a6e13343c93e971be5b202b242d296453f7d80005db8533b8fd4`, including its final newline:

```python
import runpy
import sys
sys.path.insert(0, "scripts")
runpy.run_module("vipe_benchmark.s1_validation_runner", run_name="__main__", alter_sys=True, init_globals={"STDIN_PYTHON_ARGV": tuple(sys.argv)})
```

`s1_validation_runner.py:77-109` uses `unittest.TestLoader.discover` serially with pattern `test_vipe_benchmark_{name}.py`. The exact ordered `SUITES` tuple in `s1_validation_contract.py:13-14` is:

1. `s1_semantics` → `tests/test_vipe_benchmark_s1_semantics.py`
2. `s1_recovery` → `tests/test_vipe_benchmark_s1_recovery.py`
3. `backends` → `tests/test_vipe_benchmark_backends.py`
4. `contracts` → `tests/test_vipe_benchmark_contracts.py`
5. `component_recovery` → `tests/test_vipe_benchmark_component_recovery.py`
6. `execution` → `tests/test_vipe_benchmark_execution.py`
7. `budgets` → `tests/test_vipe_benchmark_budgets.py`
8. `supervisor` → `tests/test_vipe_benchmark_supervisor.py`
9. `review_annotations` → `tests/test_vipe_benchmark_review_annotations.py`

`S1_RECEIPT_DIAGNOSTIC=1` changes the runner loop to only `supervisor`, then filters to `HelperSessionTests` (`s1_validation_runner.py:75,90-95`); it is a distinct focus path and does not validate the complete nine-suite aggregate. The selected supervisor test `test_importable_guarded_file_control` launches `[sys.executable,'-B','-m','vipe_benchmark.s1_validation_runner','--helper-probe']` (`tests/test_vipe_benchmark_supervisor.py:855-868`). This enters `helper_probe()` at `s1_validation_runner.py:60-68`, then `supervisor.monitored_call`/`HelperLifecycle`/`s1_helper_session.Session`; it does not enter the aggregate loop. The outer prospective driver/capture is a separate edge: `launch-049-exec.py` calls the capture module; `s1_validation_capture.py:58-65` reserves a B root, invokes `subprocess.Popen(ARGV,...,start_new_session=True)`, registers and binds the exact handle, and later waits. The capture is not imported by the stdin program as its launcher.

Plan049's diagnostic focus launch is `.local/envs/stg-colmap/bin/python -B -m vipe_benchmark.s1_validation_capture <absolute R/diagnostic-049-NNN> --no-timeout --diagnostic`; the aggregate omits `--diagnostic` and uses `<absolute R/aggregate-049-NNN>` (`plans/plan_049.md:78-79`). The plan's concrete driver command is `exec /home/auss/git_repos/samaust/Experiments_4DGS/.local/envs/stg-colmap/bin/python -B /home/auss/git_repos/samaust/Experiments_4DGS/docs/resolve-blocker/plan031-progress-20260922/launch-049-exec.py diagnostic 1 'Plan049 integrated corrections and memo coverage'` (`plans/plan_049.md:87`); the aggregate variant at line 93 passes `aggregate 1 'Plan049 complete current-source independent validation'`. These are specified commands only; none was run in this audit.

The nine editable paths in addenda001–003/006 are `docs/resolve-blocker/plan031-progress-20260922/launch-049-exec.py`, `scripts/vipe_benchmark/s1_validation_capture.py`, `scripts/vipe_benchmark/s1_validation_contract.py`, `scripts/vipe_benchmark/s1_helper_session.py`, `scripts/vipe_benchmark/supervisor.py`, `tests/test_vipe_benchmark_s1_helper_fixtures.py`, `tests/test_vipe_benchmark_supervisor.py`, `tests/test_vipe_benchmark_s1_recovery.py`, and `tests/test_vipe_benchmark_budgets.py`. All are included below. Other reachable files were read only.

## Creator, group, and command edges

| Actual selected source path/lines | Entry, argv or target | Reserve/create/bind/ack and containment disposition |
| --- | --- | --- |
| `s1_validation_capture.py:53-79` | `subprocess.Popen(ARGV)`, `start_new_session=True` | `reserve_job_root('B')` precedes create; `register_owned`, `bind_job_root`, and wait follow. Group changes at Popen. A successful census later is observation, not OS-wide containment. Exception-path signal/wait and ledger semantics require the planned source repair and independent review. |
| `s1_helper_session.py:1011-1015` | `Owner.spawn` uses `create_owned_process(os.posix_spawn, sys.executable, [sys.executable,'-B','-m','vipe_benchmark.s1_cpu_helper',role,session,fd],...,setsid=True)` | Wrapper at `:718-739` reserves before spawn, binds after creation and emits descendant creator ack when parent B root is matched. `setsid=True` creates a new session for the root helper. Child module runs `s1_cpu_helper.py:181-183`; its request dispatch reaches `s1_progress`, `s1_recovery`, `s1_evidence`, and their imports. |
| `tests/test_vipe_benchmark_s1_helper_fixtures.py:18-31,69-119` | `FaultOwner.spawn` substitutes `-m test_vipe_benchmark_s1_helper_fixtures` through same wrapper, `setsid=True`; descendant mode launches `-c 'import time; time.sleep(10)'` through same wrapper | Root helper is reserve/create/bind. Child `ready()` in descendant mode creates another process at `:104-108`; wrapper identifies it as a descendant, binds, then emits creator ack. This selected test helper must be covered recursively. |
| `s1_helper_session.py:1249-1257` | `_thread.start_joinable_thread(self.owner.run,daemon=False)` | H root is reserved before creation; exact native identity/handle bind follows. The pre-bind interval stays reserved. This is not evidence that an extra uncharged thread exists, but a failure/ambiguity must remain charged. `tests/test_vipe_benchmark_supervisor.py:1694-1725` exercises a mocked ambiguous native start. |
| `tests/test_vipe_benchmark_budgets.py:342-353,369-379` | Three `threading.Thread` starts in two selected tests | Each H root is reserved before `Thread.start()`, bound after start, and retired after exact `join`/stopped observation. The start-to-bind interval remains charged; a bind/retirement race is not established merely by reading these lines. |
| `scripts/vipe_benchmark/supervisor.py:445-447` | `create_owned_process('supervisor worker',subprocess.Popen,command,...,start_new_session=True)` | `command` is supplied by selected supervisor fixtures and P01 progress scenario. Wrapper reserves/binds; Popen creates a new session. Concrete inline payloads and dynamic cases are listed below. |
| `tests/test_vipe_benchmark_supervisor.py:1104-1112` | A selected supervisor test captures the original `Popen`, patches the supervisor call to `worker`, and `worker` calls original `Popen([sys.executable,'-c','import time; time.sleep(10)'],**kwargs)` | This is an actual child created inside the enclosing `create_owned_process` call, not a pure mocked Popen. The test's later cleanup outcome is separate from creator registration. |
| `tests/test_vipe_benchmark_s1_helper_fixtures.py:589-615,879-906` | `direct_script_launch`, `l18_sentinel_launch`, `fixture_process_launch`; Popen or `os.posix_spawn`; direct script/sentinel use new sessions | All call `create_owned_process` before `register_owned`; the wrapper reserves/binds, and descendant ack is emitted for a matched parent. `fixture_process_launch` also checks one live ledger match. Direct six scripts are invoked by `test_vipe_benchmark_s1_recovery.py:1981-2021`, with argv `[sys.executable,'-B',str(ROOT/'tests'/('test_vipe_benchmark_'+case['suite']+'.py')),case['selector'],'-v']`; their six literal suite/selector rows are at `:2300-2311`. This selects the same six files but one method each, and may reach helper processes through the supervisor selector. |
| `tests/test_vipe_benchmark_supervisor.py:201-216,855-869,897-905,1569-1678` | Race children, helper-probe child, helper-test workers, L31–L35 scenario workers; `-c` payloads; scenario workers use `start_new_session=True` | Parent calls `fixture_process_launch` or `supervisor` wrapper. Nested `-c` programs import `test_vipe_benchmark_s1_helper_fixtures.fixture_process_launch`, so the child itself can create a descendant. L35 uses runtime marker/release paths and is not fully byte-bound statically. |
| `tests/test_vipe_benchmark_supervisor.py:1795-1796` | P01 `-c` imports `progress_worker`; other selected progress worker uses `-c 'pass'` | `supervisor` wrapper creates the worker. `progress_worker` is project code in the helper-fixtures module at `:399`; its transitive imports are in the source inventory. |
| `tests/test_vipe_benchmark_s1_recovery.py:394-415,452-459,1981-2021` | `run_controller` saves `real_popen`, patches `supervisor.subprocess.Popen` to `worker`, and `worker` calls `real_popen([sys.executable,'-c','pass'],**kwargs)`; six real direct declaration scripts | The recovery worker is an actual process despite the patched seam. `supervisor.py:445-447` still encloses the call in `create_owned_process`, so reservation/bind apply. The six scripts use `direct_script_launch`. |

`s1_helper_session.py:718-739` is the common real creator gate: optional owned predispatch check, deadline check, ledger reserve, creator syscall, stable identity, ledger bind, and descendant creator ack. The reservation remains charged on post-create identity/bind failure. This source inspection does not certify the addendum011 owner-incarnation, single-flight wait/signal/close, or exact retirement protocol; those are future source corrections. A `Popen`/`posix_spawn` parameter is still a dynamic execution edge, so each caller and child program must be reviewed separately. A child can leave a tracked process group through its own `setsid`, `setpgid`, or nested spawn; no census proves the absence of such an event.

The selected project-side group/session changes found by targeted source search are the `start_new_session=True` Popen calls and `setsid=True` posix-spawn calls in the table. No explicit selected `os.setpgid()` or `os.setsid()` call was found in the inspected Python source. `supervisor.py:112-161` uses `os.killpg` during `stop_group` to signal an existing group; this is a cleanup action, not a group-change operation or a proof that descendants cannot leave that group. Dynamic/unbound child bytes and native code prevent an exhaustive negative claim.

### Actual paths versus unselected source hits

The runner patches `vipe_benchmark.supervisor.gpu_reading` and `vipe_benchmark.execution.gpu_reading` to raise (`s1_validation_runner.py:88-89`). Thus the `subprocess.check_output(['nvidia-smi',...])` definition in `supervisor.py:165-177` is not an actual external process call on the selected run. `execution.py:128-209` has `runtime_inventory.py` and `git` subprocess definitions, while selected `tests/test_vipe_benchmark_execution.py:26-96` returns before matrix dispatch or patches `_qualify_existing`; the selected `execute_s1_recovery` fixture patches `execution.gpu_reading` and `supervisor.subprocess.Popen` (`tests/test_vipe_benchmark_s1_recovery.py:452-459`). These definitions are conservative import-reachable, but those external invocations are not established as executed by the selected tests. `runtime.py:640-735` defines uv/setup and runtime-inventory commands; selected execution tests call `extract_source` only (`tests/test_vipe_benchmark_execution.py:155`), not setup. `transfer_proxy.py:365-366` defines a thread for runtime setup; no selected call to `uv_proxy` was found. `native_helpers.py:240-293` defines `ConfinedPopen` for S3, while the S1 gate in `stages.py:122` rejects native helpers; no selected S3 native launch was found. These are still audit limitations, not proof about arbitrary future calls.

`tests/test_vipe_benchmark_runtime.py`, `tests/test_vipe_benchmark_native_helpers.py`, and `tests/test_vipe_benchmark_annotations.py` appear in broad `rg` results but are outside the nine selected suites and six direct-script selectors. Their creator hits are excluded from actual-path claims. The six direct scripts inherit one of the selected suite files, and the helper-probe is an additional selected child command, not another suite.

## Unresolved edges and disposition

1. `tests/test_vipe_benchmark_supervisor.py:1659-1666` builds the L35 `-c` source with `marker` and `release` from `tempfile.TemporaryDirectory()`. Those absolute paths are unknown until runtime. The literal template and its project import are visible, but the final child-program byte string cannot be extracted or hash-bound at this pre-edit static gate. That program calls `fixture_process_launch` at runtime and creates a second process. This is a reachable child creator, so the missing final byte binding is a closure failure, independent of a later successful census.
2. `tests/test_vipe_benchmark_supervisor.py:51-70` builds a worker `-c` string with an f-string based on a local keys list; its final bytes can be statically reconstructed only after expression evaluation is independently pinned. The command in `:28-39` accepts caller-supplied `code`; the audit enumerated the visible selected callers but cannot treat the function signature alone as a closed command authority. The generated `nested_worker_code(seconds,parent_wait)` at `tests/test_vipe_benchmark_s1_helper_fixtures.py:899-907` embeds resolved repository paths and selected arguments (`10` or `20` seconds); the source template is bound, but absolute path resolution and final bytes need a byte-bound construction record.
3. Imported modules use dynamic `importlib.import_module` and external/native libraries (`backends.py:139,1276,1293,1383`, `runtime.py:568-586`). The selected S1 semantic/backend tests patch many native seams, but static project-source inspection alone cannot establish that every external import, extension, audit hook, or native library is incapable of creating threads/processes or changing groups. This audit makes no OS-wide or native containment claim.
4. `tests/test_vipe_benchmark_s1_recovery.py:1029-1137` and `tests/test_vipe_benchmark_supervisor.py:4199` use `exec(compile(...))` on AST slices of the driver/monitored code under synthetic scopes. The relevant operations are mocked in the visible fixtures, but this dynamic code-selection edge requires exact sliced-node and scope review to certify no real creator is invoked. It is not a child process edge on the inspected branch.

**Minimum intervention before any source edit:** Main should obtain a separately reviewed narrow containment/source-scope amendment for a deterministic, statically hashable inline child-program construction (including L35), and a source review that binds every dynamic command/import edge or explicitly narrows it to a proved inactive branch under the exact selected test command. If that correction requires a tenth editable file, changed suite/selector, new process/thread/observer, or changed behavioral assertion/deadline, it requires its own authority; the current nine-path boundary must not be silently widened. Until then the ledger tree remains charged on any uncertain creator/owner path and the source closure is **FAIL**. No runtime clearance follows from this report.

## Inputs, method, and limits

Read-only tools: `git status --short`, `git rev-parse HEAD`, `rg --files`, targeted `rg -n`, `sed`, `cat`, `sha256sum`, and `/usr/bin/python3 -B -` using only stdlib `ast`, `pathlib`, and `hashlib` to parse and hash source bytes. No project module was imported or executed. The AST walk starts with the contract/runner/capture/CPU helper and nine selected suites; it recursively follows literal local imports in modules and test files, including function-local imports. This yields a **conservative syntactic import closure** of 66 Python files and 652 local import edges. The inventory below adds the launch driver, package init, and runtime-inventory child target; the AST walk also follows the in-process `basketball_vipe_worker` import in the selected recovery test. A syntactic import edge is not proof that a function was invoked, and a function not found by this pass is not proof of absence when imports/commands are dynamic. The working tree was dirty before this audit; these hashes bind observed bytes only. `HEAD` was `db485e99f160337c4812833619cdd1386fb7ebc1`.

Key input SHA-256: `AGENTS.md` `3d09a19b0bf8e4bfcf7c25f5b001a769f2cce372a425fc1dd1a14fc299ef620f`; `plans/plan_049.md` `89d1f634ad2407b02558ff9c030d4a4f12f8f4ab010c93e2cf532876564afe7e`; addendum011 `18e0d807a074fdb11817251b459db54ea3b0725161222da824b86c5ebfe52d65`; independent plan review001 `59ecde9fe6c17019130fa1bfa7a227a470c9c116a272a95b946b2e787e96d24c`. This audit was requested as a source-stage precondition under the addendum; plan PASS is not source or launch PASS.

## Hash-bound project source inventory

Each row is SHA-256 of the exact on-disk file bytes at this audit snapshot. Rows from the recursive AST walk are marked `import`; additional command/authority inputs are marked `entry`.

| SHA-256 | Project source path | Reach |
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

## Extracted inline command byte hashes

These are UTF-8 bytes of complete static `-c` literals or complete static local `code` assignments that feed the selected `SupervisorTests.run_worker`/`worker`/`scenario_worker` paths. Identical bytes are listed once. Dynamic constructions are explicitly unresolved above.

| SHA-256 | Exact UTF-8 source (Python repr) | Selected site |
| --- | --- | --- |
| `5412061db9644499b71bf5a65aa9f490d0e8f809ab447381cb227227424f289a` | `'import os,signal,time; os.kill(os.getppid(),signal.SIGTERM); time.sleep(20)'` | `tests/test_vipe_benchmark_supervisor.py:113` |
| `5d38fec43f371d1eaf2a1817a0778df1a82012511c09dfc89307301509204ce7` | `'import time; time.sleep(20)'` | `tests/test_vipe_benchmark_supervisor.py:124,139,167` |
| `07dced62a888cacc1726f7e9f76f53354ddaf19916ad9bb9cce74f35f1199fc3` | `'import signal,time; signal.signal(signal.SIGTERM, signal.SIG_IGN); time.sleep(20)'` | `tests/test_vipe_benchmark_supervisor.py:75` |
| `b10412dbc3d47d973791584a123e66848faffffdbf02a04deea3549b3fa7e02e` | `"import sys,json; from pathlib import Path; p=Path(sys.argv[1]); p.mkdir(); (p/'result.json').write_text(json.dumps({'status':'complete'}))"` | `tests/test_vipe_benchmark_supervisor.py:146`, `tests/test_vipe_benchmark_supervisor.py:42` |
| `d2a8e4fd6b42e87de6cafa47854185fb1540b50dcc7637720914a7eaf800111b` | `"import sys;sys.path.insert(0,'tests');from test_vipe_benchmark_s1_helper_fixtures import progress_worker;progress_worker(sys.argv[1],sys.argv[2])"` | `tests/test_vipe_benchmark_supervisor.py:1795` |
| `fd7850f365dfe06093452d15f5d71327f6a24646c4a264b391e47b0a83a33251` | `'import time; time.sleep(10)'` | `tests/test_vipe_benchmark_s1_helper_fixtures.py:106`, `tests/test_vipe_benchmark_s1_helper_fixtures.py:610`, `tests/test_vipe_benchmark_supervisor.py:1111` |
| `d74ff0ee8da3b9806b18c877dbf29bbde50b5bd8e4dad7a3a725000feb82e8f1` | `'pass'` | `tests/test_vipe_benchmark_s1_recovery.py:414`, `tests/test_vipe_benchmark_supervisor.py:1796` |

The complete L35 `-c` bytes, the f-string cache worker, and the generated `nested_worker_code` variants have no static final-byte hash in this report. Their literal pieces are bound by their source-file hashes; that is insufficient for the addendum011 command-byte closure gate.

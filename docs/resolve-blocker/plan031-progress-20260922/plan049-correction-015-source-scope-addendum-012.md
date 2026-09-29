# Plan049 Correction015 source-scope addendum 012 — byte-bound generated child commands

This plan-only proposal responds to the independently confirmed FAIL in `plan049-correction-015-transitive-source-closure-audit-001.md`. It preserves addendum011's nine editable paths and all Plan049 behavior/resource constraints. It does not authorize source edits or runtime. If independently reviewed PASS, explicit user authorization and Main adoption of this exact hash are required before implementing the additional launch-evidence binding.

## Finding addressed

The L35 scenario builds a nested Python `-c` command using runtime `TemporaryDirectory()` paths, so the final command bytes do not exist at the static pre-edit audit. Other fixture helpers similarly parameterize generated inline programs and path arguments. Addendum011's exact-expanded-bytes-before-edit gate cannot be met by source hashes alone. This addendum changes only the evidence method: statically bind each deterministic generator/template and the exact allowed input sources, then durably bind the fully expanded bytes immediately before the existing OS create call.

## Static template and substitution proof

The pre-edit read-only closure audit must enumerate every reachable generated command, including the L35 parent and nested child, `nested_worker_code(seconds,parent_wait)`, the f-string worker program, and any other selected `-c`/dynamic argv or `exec(compile(...))` path. For each, bind the exact source file hash and source range/AST construction, the generator callsite, every substitution's type and source, and its allowed domain. Paths may be runtime-created only when their source is the existing attempt-local `TemporaryDirectory` or another fixed authorized root; numeric/time arguments must be exact selected literals or bounded validated values from the existing scenario. No `eval`, ambient environment, user data, dynamic import, external shell, or unresolved command may supply code/argv. The audit must mechanically reason about the byte construction without importing/executing project code. Any non-deterministic or unbounded source of code/argv remains a closure FAIL and stops before editing.

## Pre-create durable exact-byte binding

Within the existing nine paths, extend the current process reservation record to include an exact launch descriptor before the OS create call. The descriptor is derived from the actual arguments passed to the existing `create_owned_process` creator (and from the existing direct capture Popen site) and includes:

- a versioned canonical, type-preserving, length-delimited encoding of the executable and complete argv, with SHA-256 and encoded byte length;
- when argv includes `-c`, the exact UTF-8 source bytes' SHA-256 and length;
- when argv includes `-m`, the exact module name and the pre-edit audit's source hash for the resolved project entry module;
- exact cwd, start-new-session/setpgid/setsid flags and a canonical digest of relevant environment entries (store only the digest, never secret values).

Compute and validate this descriptor before appending the root/descendant reservation event, durably append and read it back under the existing interprocess lock, then invoke the already authorized creator with those same immutable executable/argv/options values. No creator may reconstruct or mutate the command after reservation. The creator call must prove its actual bytes/options equal the committed descriptor before syscall entry. If canonical encoding or command inspection is unsupported, fail before OS creation and leave the logical reservation charged or durably cancel only with proof that no child was created. For existing direct capture Popen, bind the same descriptor before Popen using the existing reserved B token. A detached/nested `fixture_process_launch` records its own independent descriptor in its descendant reservation.

The per-attempt job-ledger chain already binds root/session identity and source authority. The launch descriptor is an additional field in existing reservation events, not a new sidecar, process, thread, observer, source module, or test method. It consumes the existing 8 MiB job-ledger cap; before implementation, compute the maximum added bytes from the exact command/argv limits and show the full ledger still fits its fixed cap. Preserve `B+max(1,H)≤8`, 150 GiB artifacts, 64 MiB memo, and all process/deadline/callback/assertion limits.

At runtime, every actual command hash is known and durable before process creation, even when temporary paths vary. The static template hash plus typed substitution-source map proves that the generated content follows the reviewed source construction; the reservation's exact argv/code hash binds that specific invocation. The child's same-handle receipt and creator acknowledgment remain distinct; a hash is not identity or terminal evidence.

## Reachability and no-bypass conditions

The existing closure audit's map remains the baseline. The reviewer must verify all selected code and six direct-script selectors. Process/thread creates in `create_owned_process`, capture, owner native-thread start, budget threads, test direct scripts, helper descendants, and fixture workers remain individually accounted. Definitions such as `nvidia-smi`, setup/runtime subprocesses, and native/thread helpers count only when an exact selected call path reaches them; CPU runner patches and inert fixture mocks must be verified as guards at the actual selected path. Any dynamic import/command/sliced `exec` whose execution can create an unbound child or bypass the descriptor must be proven unreachable under the exact fixed command or the audit fails. Do not claim that group census excludes arbitrary OS-level forks or native runtime behavior.

## Gates and preserved authority

Preserve addendum011's exact process-incarnation/nonce owner binding, mutex/interprocess transaction, readback-first event replay, no-repeat behavior for unknown signals, same-handle `process.wait(timeout=...)` call, legacy no-ledger semantics, original cleanup deadline/error precedence and addendum006 final-census/return behavior. Preserve every existing assertion and behavioral deadline; add no source member, method, callback, scenario, suite, selector, process, thread, or observer. No ten-source-path expansion is proposed.

Independent plan review must compare this exact proposal with Plan049, Correction015/014, addenda001–011, source review004, audit001, and its independent review. PASS is plan wording only. After PASS, explicit user authorization and Main adoption of this exact hash are required. Then revise the read-only closure audit to use the template/substitution proof and pre-create launch descriptor, obtain a fresh independent audit PASS before source edits, implement only within the nine paths, obtain distinct exact-source review, and complete fresh source, artifact-capacity, process ownership/capacity, output-path, attempt-index/high-water, and Main-session preflight. No tests, fixtures, pidfd operations, diagnostics, admission, launch, or aggregate are cleared here.

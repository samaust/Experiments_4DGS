# S3 reconstruction native-helper repair

The user explicitly authorized one additional S3 reconstruction attempt, capped at 90 minutes, after repair. [Authorization](s3-reconstruction-recovery-authorization-001.json) binds the preserved, cleaned-up original failure and [validation009](implementation-validation-009.json). This request resumes only S3 reconstruction; it does not launch the continuous-improvement loop or reopen other stopped work.

## Implemented boundary

The existing ViPE import/source guard remains active. Five native command families are admitted from the pinned Triton 3.6/Python 3.12 sources: exact `ldconfig -p`, interpreter-only `file -b`, native C helper/launcher compilation, bundled `ptxas --version` (both native callsites), and arch89 PTX assembly. C and PTX inputs must match their pinned native producers; launcher C is checked against `make_launcher` using the native constants, signature and descriptor metadata. Ordered compiler flags, includes/libraries, source/output locations, executable identities and relevant environment overrides are checked. Unknown commands, shells, response files, process-group overrides, extra descriptors and direct fork/exec alternatives remain denied. The audit capability is thread-local, single-use, and cleared on failure.

Each admitted helper runs inside bubblewrap mount/user/PID/network/IPC/UTS namespaces. Its filesystem exposes read-only `/usr`, the system linker cache, the pinned Triton directory and required interpreter/header paths, plus the supervised attempt's writable temporary tree. A private proc mount prevents parent-root traversal. The host home/repository and ViPE tree are absent outside the specifically mounted inputs. Mount confinement is inherited by compiler/assembler/linker descendants. Helpers inherit the supervised host process group; no new session is created. Extra host descriptors are closed; native stdin/stdout/stderr and native tool arguments are retained.

The system toolchain and `/usr` headers/libraries remain trusted; their whole distribution tree is not individually pinned by this repair. Selected helper executables and pinned producer sources are hashed in the policy receipt. This is not a hostile-Python-code sandbox: trusted Python can construct stack/code objects, and Python audit hooks do not confine arbitrary in-process native code. The new OS boundary specifically prevents helper descendants from escaping into the host source trees. Do not describe callsite checks alone as that boundary.

Each helper records original and confined argv, executable/source policy hashes, relevant non-secret environment, parent/child process group, preserved generated source, exit status and generated output hash. A completed manifest binds these records to the segmentation result. Cold attempt-local native caches and all inference settings remain unchanged.

## Validation

All **322 CPU benchmark tests pass** (14.568 seconds). New fixtures cover forbidden/symlink paths, environment/tool/flag changes, tampered C/PTX, exact version callsites, single-use capability rejection, recovery scope, one-attempt consumption, cumulative GPU deadline shortening and downstream result resolution without relabeling the original failure.

The minimal bubblewrap namespace probe was denied inside the Codex sandbox and succeeded on its one prescribed host retry. Subsequent host fixtures verified nested-child denial and hidden host/proc-root access; confined native discovery (`ldconfig`, `file`, bundled `ptxas --version`) passed. An integrated audit/Popen/namespace fixture passed in the qualified E3 interpreter. Its fixture function deliberately uses the pinned code filename to exercise admission; it is not evidence of hostile Python isolation or actual Triton model qualification. No model, GPU forward, native compilation or JIT smoke job ran during repair validation.

The NVIDIA skill catalog lookup likewise succeeded on its single host retry after sandbox network denial. No skill was installed. Repository-specific implementation and local pinned sources supplied the repair.

## Accounting and handoff

`S3-reconstruction-recovery-001` receives exactly one attempt of at most 5,400 seconds, including cleanup. Both reconstruction attempts remain charged against the unchanged cumulative 93,600-second GPU ceiling. Memory remains at most 22 GiB on the one exclusive RTX 4090 process group. Existing storage/download/CPU ceilings remain binding. The original output directory and ledger failure are never overwritten. Successful downstream lookup can resolve the recovery while the original job remains failed in accounting.

Before dispatch: four GPU attempts consumed 646.942 seconds; the new GPU attempt remains unused. Original setup, calibration and historical source/result records remain intact. The real reconstruction attempt supplies native compilation and first-pair qualification evidence; passing CPU fixtures alone does not establish those outcomes.

# Triton 3.6 subprocess isolation review

The S3 reconstruction traceback establishes a local audit-policy rejection of the first native Triton CUDA initialization at `backends/nvidia/driver.py:25`: `subprocess.check_output(['/sbin/ldconfig', '-p'])`. This review authorizes no retry: the original S3 reconstruction remains consumed and its artifacts/time unchanged. AGENTS.md and Plan 031 isolation, setup/import and no-extra-attempt rules were reread.

## Native command closure for the selected NVIDIA path

The following are the complete Python-level external command families found in the inspected CUDA driver/launcher/compiler path. Cache hits can avoid some calls. Names below describe native behavior; no command was executed during review.

| Operation and exact callsite | Native argument shape | Necessary checks |
| --- | --- | --- |
| CUDA library lookup: `backends/nvidia/driver.py:25` | `['/sbin/ldconfig', '-p']` | Exact two arguments, resolved trusted system binary, no mutation options. Keep native output parsing and selected libcuda directory. |
| Platform cache identity: `runtime/build.py:59–64` → Python 3.12 `platform.architecture` → `/usr/lib/python3.12/platform.py:669` | `['file', '-b', resolved_sys_executable]`, child environment has `LC_ALL=C` | Resolve `file` using effective PATH and bind its realpath/hash; sole input is the actual qualified interpreter after native symlink resolution. Current blanket audit denial is caught as OSError by platform.py, silently weakening the architecture cache key. Do not emulate/cache fabricated output. |
| C helper/launcher compile: `runtime/build.py:20–49`, callers NVIDIA `driver.py:62–68,683–689` | `[cc, src, '-O3', '-shared', '-fPIC', '-Wno-psabi', '-o', so, '-l:libcuda.so.1', '-L'+triton_lib_dir, '-L'+each_native_libcuda_dir, '-I'+triton_include, '-I'+srcdir, '-I'+python_include, ...]` | Native CC selection uses CC if set, otherwise GCC preferred over Clang via shutil.which. Bind actual resolved compiler, source/output/include/lib identities and exact ordered flags. Normal NVIDIA callsites add no ccflags. Extra include paths can come from TRITON_CUDACRT_PATH/TRITON_CUDART_PATH and must be explicitly admitted or rejected. |
| PTX assembler version: `knobs.py:184`; NVIDIA `compiler.py:43` | `[bundled_ptxas, '--version']` | RTX4090 arch89 selects `backends/nvidia/bin/ptxas`, not ptxas-blackwell. Verify exact installed binary identity. Reject unadmitted TRITON_PTXAS_PATH overrides instead of letting native fallback choose another executable. |
| PTX→cubin: NVIDIA `compiler.py:461–494` | Default `[ptxas, '-lineinfo', '-v', '--gpu-name=sm_89', temporary_ptx, '-o', temporary_ptx+'.o']` | Bind source PTX to the pinned compiler's generated source, fresh supervised TMPDIR and same output stem; no arbitrary input/output paths or extra options. Native `enable_fp_fusion=False` inserts `--fmad=false`. Other debug/optimization flags derive from recorded native knobs, not a generic flags allowance. |

NVIDIA compiler normally uses LLVM/libtriton in-process to generate PTX. Its Python callsites above do not invoke nvcc, nvlink, a shell, package installers or nvidia-smi. Triton testing utilities contain nvidia-smi clock/persistence commands and cuda-memcheck; the active default do_bench path does not require them and they must stay denied. GCC/Clang can themselves execute compiler/assembler/linker descendants (for example cc1/as/collect2/ld for GCC); their exact host paths and closure were not probed here and are not governed by the parent's Python audit hook.

## Minimal reviewable admission policy

Keep NoViPE import denial and existing open/listdir/scandir/dlopen path checks. Replace the blanket Popen decision only with a capability scoped to verified native Triton callsites and these five command families, backed by the exact source and executable hashes. Reject shell commands, arbitrary executables, response files, compiler plugins, changed prefixes, unrecognized options, mismatched executable-vs-argv identity, forbidden lexical/resolved paths and symlink escapes. Bind the capability to one child invocation and close it on success or exception; do not leave a general compiler permit active.

`cuda_utils.c` must equal the pinned NVIDIA driver.c bytes. `__triton_launcher.c` must match the captured output of pinned `make_launcher` for that actual native signature/constants. Check the generated source and output share the fresh temporary directory; record input/output hashes and the exact approved include/header/library closure. PTX likewise must match the source handed to native make_cubin. Validate effective CC/PATH, CPATH/C_INCLUDE_PATH, compiler search variables, LD_PRELOAD/LD_AUDIT/LD_LIBRARY_PATH, Triton tool/build overrides and custom cache managers. No relevant search path may resolve into ViPE or prompts. Unexpected overrides should fail for review, not be silently replaced with different native settings. Existing supervisor already places Triton/cache/temp outputs under the monitored attempt directory; preserve that isolation and its cold-cache timing.

**Boundary:** an argv/callsite matcher does not make Python audit hooks apply to compiler children. A hard no-ViPE filesystem guarantee requires inherited OS filesystem confinement covering those children and their descendants, with the allowed system toolchain/header/driver trees and this attempt's inputs/outputs. Otherwise the implementation must retain an explicit trusted-toolchain/closed-input limitation and cannot claim general child filesystem isolation. A callsite stack check alone is not such confinement. No OS confinement availability or toolchain closure was tested here. If the required boundary cannot be validated, remain blocked rather than grant blanket subprocess access.

Save command, executable/source hashes, cwd, relevant non-secret environment policy, native option provenance, child process-group membership and generated artifacts in the attempt evidence. Preserve native flags, library discovery, return/error behavior, kernel autotuning and supervisor cleanup/deadline charging. CPU fixtures should exercise only fake command admission/rejection, including ViPE symlinks, tampered generated source, unexpected flags/env, reused capability and nested children; no model/JIT smoke attempt is allocated by this review.

## Evidence and limits

Read-only source review, including recursively excluded prompts paths. No native imports, subprocess probes, compilation, models, GPU/network operations, source edits, ledger edits, delegation or commits. Only this document was written. Current helper/tool binaries, header/linker closure, future native command success and OS confinement remain unverified.

Source fingerprints, SHA-256:

- Triton `backends/nvidia/driver.py`: `4ad4b4440aa4a5ee15ac2382ae78a7aa8029986c22ec2acbd072a91810e85e94`
- Triton `backends/nvidia/driver.c`: `439c1e886fa9eac7346d7523d03ba0a4c52aa4c9b518ea86d8659b5c07eb7dc9`
- Triton `backends/nvidia/compiler.py`: `eea55698bab00c726b3d1d495b390b72a63aaa8d167781a65ea5212d394d76f6`
- Triton `runtime/build.py`: `26c6ddd4dba3534ce54790f12d2b75729f51e467c48b2f740dd62b7c75a85b39`
- Triton `knobs.py`: `d84bda664f733f0547f9f4397c2dab11da1f9c58f974a840a3f1c61ea48c76fa`
- Triton `testing.py`: `44e3fae7b4cc41b4db3b8b41a4f0a818d7fe9d036cfe4e0f4f08036a75eaafe4`
- `scripts/vipe_benchmark/isolation.py`: `7c322b999ae1cfff1c7c6e758a3b2603f9decc0d3c475d322f3d2bb935ac51e0`
- `/usr/lib/python3.12/platform.py`: `ed0defe8ff7c116710493ffd099b566d3de686ab1b431a3d5401056798e59341`
- `.local/vipe-alternatives/plan031-20260913T032700Z/jobs/S3-reconstruction/failure.json`: `c42b0f891494f9e1aacc9cf7c018556f081afe95b78354c052505200c68bb39b`

Start 2026-09-13T08:55:52+00:00; end 2026-09-13T08:59:11.956120+00:00; conservative full wall elapsed **199.956 seconds**, idle 0, within the new 240-second cap. No extension.

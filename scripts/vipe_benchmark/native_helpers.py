"""Pinned Triton 3.6 helpers inside an inherited bubblewrap filesystem boundary.

This is a trusted Python/native toolchain policy, not a hostile-code sandbox for
an arbitrary Python adapter. Helpers see system tools, admitted immutable inputs
and one attempt's temporary tree; they cannot see the host home/repository/proc.
"""
import inspect
import os
from pathlib import Path
import shutil
import subprocess
import sys
import sysconfig
import threading

from .files import file_record, verify_record, write_json

PINS = {
    'backends/nvidia/driver.py': '4ad4b4440aa4a5ee15ac2382ae78a7aa8029986c22ec2acbd072a91810e85e94',
    'backends/nvidia/driver.c': '439c1e886fa9eac7346d7523d03ba0a4c52aa4c9b518ea86d8659b5c07eb7dc9',
    'backends/nvidia/compiler.py': 'eea55698bab00c726b3d1d495b390b72a63aaa8d167781a65ea5212d394d76f6',
    'runtime/build.py': '26c6ddd4dba3534ce54790f12d2b75729f51e467c48b2f740dd62b7c75a85b39',
    'knobs.py': 'd84bda664f733f0547f9f4397c2dab11da1f9c58f974a840a3f1c61ea48c76fa',
}
CACHE_ENV = {'TRITON_HOME', 'TRITON_CACHE_DIR', 'TRITON_DUMP_DIR', 'TRITON_OVERRIDE_DIR'}
UNSAFE_ENV = {'CC', 'CXX', 'CPATH', 'C_INCLUDE_PATH', 'CPLUS_INCLUDE_PATH', 'OBJC_INCLUDE_PATH',
              'COMPILER_PATH', 'GCC_EXEC_PREFIX', 'LIBRARY_PATH', 'LD_PRELOAD', 'LD_AUDIT',
              'LD_LIBRARY_PATH', 'PTXAS_OPTIONS', 'DISABLE_PTXAS_OPT', 'NVPTX_ENABLE_DUMP',
              'LLVM_EXTRACT_DI_LOCAL_VARIABLES', 'USE_IR_LOC'}


def checked_path(value, forbidden_roots):
    lexical = Path(os.path.abspath(value))
    resolved = lexical.resolve()
    if ('prompts' in lexical.parts or 'prompts' in resolved.parts or
            any(p.is_relative_to(root) for root in forbidden_roots for p in (lexical, resolved))):
        raise PermissionError('native helper path crosses prohibited source boundary')
    return resolved


def check_environment(env, temporary, forbidden_roots):
    for key, value in env.items():
        if value and (key in UNSAFE_ENV or key.startswith('TRITON_') and key not in CACHE_ENV):
            raise ValueError(f'unadmitted native helper environment override: {key}')
        if key in CACHE_ENV and not checked_path(value, forbidden_roots).is_relative_to(temporary):
            raise ValueError('native cache must remain inside the supervised attempt')
    if checked_path(env.get('TMPDIR', ''), forbidden_roots) != temporary:
        raise ValueError('native temporary directory differs from supervised attempt')
    for entry in env.get('PATH', '').split(os.pathsep):
        checked_path(entry or '.', forbidden_roots)


def confined_command(argv, *, readonly, temporary):
    command = ['/usr/bin/bwrap', '--die-with-parent', '--unshare-user', '--unshare-pid',
               '--unshare-net', '--unshare-ipc', '--unshare-uts', '--cap-drop', 'ALL',
               '--ro-bind', '/usr', '/usr', '--symlink', 'usr/bin', '/bin',
               '--symlink', 'usr/sbin', '/sbin', '--symlink', 'usr/lib', '/lib',
               '--symlink', 'usr/lib64', '/lib64', '--proc', '/proc', '--dev', '/dev',
               '--ro-bind', '/etc/ld.so.cache', '/etc/ld.so.cache']
    for path in sorted(set(map(str, readonly))):
        if not Path(path).is_relative_to('/usr'):
            command += ['--ro-bind', path, path]
    command += ['--bind', str(temporary), str(temporary), '--chdir', str(temporary), '--', *argv]
    return command


class NativeHelpers:
    def __init__(self, triton, temporary, forbidden_roots):
        self.forbidden = [Path(p).resolve() for p in forbidden_roots]
        self.triton = checked_path(triton, self.forbidden)
        self.temporary = checked_path(temporary, self.forbidden)
        if not self.temporary.is_dir():
            raise ValueError('fresh supervised native temporary directory missing')
        check_environment(os.environ, self.temporary, self.forbidden)
        self.records = {key: file_record(self.triton / key, pin) for key, pin in PINS.items()}
        self.platform = file_record('/usr/lib/python3.12/platform.py',
            'ed0defe8ff7c116710493ffd099b566d3de686ab1b431a3d5401056798e59341')
        gcc = shutil.which('gcc') or shutil.which('clang')
        self.tools = {name: file_record(checked_path(path, self.forbidden)) for name, path in {
            'bwrap': '/usr/bin/bwrap', 'ldconfig': '/sbin/ldconfig', 'file': shutil.which('file'),
            'cc': gcc, 'ptxas': self.triton / 'backends/nvidia/bin/ptxas'}.items()}
        if any(not Path(self.tools[k]['path']).is_relative_to('/usr') for k in ('bwrap', 'ldconfig', 'file', 'cc')):
            raise ValueError('native system tools must resolve inside /usr')
        self.interpreter = checked_path(sys.executable, self.forbidden)
        scheme = sysconfig.get_default_scheme()
        self.include = checked_path(sysconfig.get_paths(scheme='posix_prefix' if scheme == 'posix_local' else scheme)['include'], self.forbidden)
        self.local = threading.local()
        self.log = self.temporary / 'native-helper-evidence'
        self.log.mkdir(exist_ok=False)
        self.sequence = 0
        self.evidence = dict(boundary='bubblewrap mount/user/pid/network namespaces inherited by descendants',
            sources=self.records, platform=self.platform, tools=self.tools, log=str(self.log),
            trusted_system_tree='/usr', inherited_process_group=True,
            limitation='Trusted pinned Python callsites and host system toolchain; not an arbitrary-code sandbox')
        write_json(self.log / 'policy.json', self.evidence)

    def frame(self, frames, relative, name):
        record = self.platform if relative == 'platform' else self.records[relative]
        for frame in frames:
            if Path(frame.f_code.co_filename).resolve() == Path(record['path']) and frame.f_code.co_name == name:
                verify_record(record)
                return frame
        return None

    def admit(self, argv, frames, env):
        if not isinstance(argv, (list, tuple)) or not argv or any(not isinstance(a, str) for a in argv):
            raise PermissionError('native helper requires explicit string argv')
        check_environment(env, self.temporary, self.forbidden)
        executable = checked_path(shutil.which(argv[0], path=env.get('PATH')) or argv[0], self.forbidden)
        for arg in argv:
            if arg.startswith('@'):
                raise PermissionError('native response files prohibited')
            if arg.startswith('/'):
                checked_path(arg, self.forbidden)
        source, result = None, None
        readonly = [self.triton, self.interpreter, self.include]
        driver = 'backends/nvidia/driver.py'
        if executable == Path(self.tools['ldconfig']['path']):
            if argv != ['/sbin/ldconfig', '-p'] or not self.frame(frames, driver, 'libcuda_dirs'):
                raise PermissionError('unadmitted ldconfig invocation')
            kind = 'ldconfig'
        elif executable == Path(self.tools['file']['path']):
            if (list(argv) != ['file', '-b', str(self.interpreter)] or env.get('LC_ALL') != 'C' or
                    not self.frame(frames, 'platform', '_syscmd_file') or
                    not self.frame(frames, 'runtime/build.py', 'platform_key')):
                raise PermissionError('unadmitted interpreter architecture invocation')
            kind = 'file'
        elif executable == Path(self.tools['cc']['path']):
            build = self.frame(frames, 'runtime/build.py', '_build')
            compile_frame = self.frame(frames, 'runtime/build.py', 'compile_module_from_src')
            origin = self.frame(frames, driver, '__init__')
            if build is None or compile_frame is None or origin is None:
                raise PermissionError('native compiler requires pinned Triton build origin')
            values = build.f_locals
            name = values['name']
            source = checked_path(values['src'], self.forbidden)
            result = checked_path(values['so'], self.forbidden)
            if (name not in ('cuda_utils', '__triton_launcher') or
                    not source.is_relative_to(self.temporary) or source.parent != result.parent or
                    source.name != name + '.c' or values['ccflags']):
                raise PermissionError('unadmitted native compiler input/output/options')
            text = compile_frame.f_locals['src']
            if name == 'cuda_utils':
                expected_source = (self.triton / 'backends/nvidia/driver.c').read_text()
            else:
                v = origin.f_locals
                expected_source = origin.f_globals['make_launcher'](v['constants'], v['signature'], v['tensordesc_meta'])
            if source.read_text() != text or text != expected_source:
                raise PermissionError('native generated source differs from pinned producer')
            libraries = values['library_dirs']
            expected_includes = [str(self.triton / 'backends/nvidia/include'), str(source.parent), str(self.include)]
            if values['include_dirs'] != expected_includes or values['libraries'] != ['libcuda.so.1']:
                raise PermissionError('unadmitted compiler include/library closure')
            if not libraries or Path(libraries[0]).resolve() != self.triton / 'backends/nvidia/lib':
                raise PermissionError('unadmitted Triton library directory')
            if any(not checked_path(p, self.forbidden).is_relative_to('/usr') for p in libraries[1:]):
                raise PermissionError('CUDA system libraries must resolve inside /usr')
            expected = [values['cc'], str(source), '-O3', '-shared', '-fPIC', '-Wno-psabi', '-o', str(result),
                        '-l:libcuda.so.1', *['-L' + p for p in libraries], *['-I' + p for p in expected_includes]]
            if list(argv) != expected:
                raise PermissionError('native compiler argv differs from exact pinned recipe')
            kind = 'cc'
        elif executable == Path(self.tools['ptxas']['path']):
            kind = 'ptxas'
            if list(argv) == [str(executable), '--version']:
                if not (self.frame(frames, 'knobs.py', 'from_path') or
                        self.frame(frames, 'backends/nvidia/compiler.py', 'get_ptxas_version')):
                    raise PermissionError('unadmitted assembler version origin')
            else:
                frame = self.frame(frames, 'backends/nvidia/compiler.py', 'make_cubin')
                if frame is None:
                    raise PermissionError('unadmitted PTX producer')
                v = frame.f_locals
                source = checked_path(v['fsrc'].name, self.forbidden)
                result = checked_path(v['fbin'], self.forbidden)
                expected = [str(executable), '-lineinfo', *([] if v['opt'].enable_fp_fusion else ['--fmad=false']),
                            '-v', '--gpu-name=sm_89', str(source), '-o', str(source) + '.o']
                if (list(argv) != expected or not source.is_relative_to(self.temporary) or
                        str(result) != str(source) + '.o' or source.read_text() != v['src']):
                    raise PermissionError('PTX argv or generated source differs from pinned producer')
        else:
            raise PermissionError('unadmitted native executable')
        verify_record(self.tools[kind])
        verify_record(self.tools['bwrap'])
        return confined_command(list(argv), readonly=readonly, temporary=self.temporary), source, result, kind

    def consume(self, args):
        expected = getattr(self.local, 'permit', None)
        self.local.permit = None
        return expected is not None and args[0] == expected[0] and list(args[1]) == expected and args[2] is None

    def install(self):
        policy = self
        original = subprocess.Popen

        class ConfinedPopen(original):
            def __init__(self, args, *positional, **kwargs):
                if positional or any(kwargs.get(k) for k in ('shell', 'executable', 'cwd', 'preexec_fn',
                                                             'start_new_session', 'pass_fds')) or 'process_group' in kwargs:
                    raise PermissionError('native helper process overrides prohibited')
                frames = []
                frame = inspect.currentframe().f_back
                while frame:
                    frames.append(frame)
                    frame = frame.f_back
                try:
                    command, source, result, kind = policy.admit(args, frames, kwargs.get('env') or os.environ)
                finally:
                    del frames, frame
                policy.sequence += 1
                self.receipt = policy.log / f'{policy.sequence:06d}'
                self.artifact = result
                self.saved = False
                self.receipt.mkdir()
                if source:
                    saved_source = self.receipt / source.name
                    saved_source.write_bytes(source.read_bytes())
                write_json(self.receipt / 'request.json', dict(argv=args, confined_argv=command, kind=kind,
                    parent_pid=os.getpid(), pgid=os.getpgrp(), cwd=os.getcwd(),
                    source=None if source is None else file_record(source),
                    archived_source=None if source is None else file_record(saved_source),
                    environment={k: v for k, v in (kwargs.get('env') or os.environ).items()
                                 if k in CACHE_ENV | UNSAFE_ENV | {'PATH', 'TMPDIR', 'LC_ALL'}}))
                policy.local.permit = command
                try:
                    # Keep native standard streams, but do not leak host file
                    # descriptors into the confined process or its descendants.
                    kwargs['close_fds'] = True
                    super().__init__(command, **kwargs)
                finally:
                    policy.local.permit = None
                try:
                    group = os.getpgid(self.pid)
                except ProcessLookupError:
                    group = None
                write_json(self.receipt / 'started.json', dict(pid=self.pid, observed_pgid=group,
                    inherited_pgid=os.getpgrp()))

            def wait(self, *args, **kwargs):
                code = super().wait(*args, **kwargs)
                if not self.saved:
                    self.saved = True
                    write_json(self.receipt / 'result.json', dict(returncode=code,
                        output=file_record(self.artifact) if self.artifact and self.artifact.exists() else None))
                return code

        subprocess.Popen = ConfinedPopen


def finalize_evidence(isolation):
    helpers = isolation.get('native_helpers')
    if not helpers:
        return
    log = Path(helpers['log'])
    entries = []
    for directory in sorted(log.iterdir()):
        if directory.is_dir():
            entries.append({name: file_record(directory / (name + '.json'))
                            for name in ('request', 'started', 'result')})
    path = log / 'completed.json'
    write_json(path, dict(status='complete', policy=file_record(log / 'policy.json'), commands=entries))
    helpers['completed'] = file_record(path)

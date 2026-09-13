"""CPU-only command admission and single-attempt accounting fixtures."""
import os
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from vipe_benchmark.native_helpers import NativeHelpers, checked_path, check_environment, confined_command
from vipe_benchmark.config import load
from vipe_benchmark.files import file_record, write_json
from vipe_benchmark.ledger import Ledger


class NativeHelperTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.forbidden = self.root / 'vipe'
        self.forbidden.mkdir()
        self.scratch = self.root / 'scratch'
        self.scratch.mkdir()

    def test_forbidden_direct_and_symlink_paths(self):
        (self.root / 'alias').symlink_to(self.forbidden, target_is_directory=True)
        for p in (self.forbidden / 'source.c', self.root / 'alias/source.c', self.root / 'prompts/no-file'):
            with self.subTest(path=p), self.assertRaises(PermissionError):
                checked_path(p, [self.forbidden])

    def test_environment_rejects_toolchain_and_triton_overrides(self):
        for name in ('CC', 'CPATH', 'LD_PRELOAD', 'LD_LIBRARY_PATH', 'TRITON_PTXAS_PATH',
                     'TRITON_CACHE_MANAGER', 'TRITON_CUDACRT_PATH', 'GCC_EXEC_PREFIX', 'PTXAS_OPTIONS'):
            with self.subTest(name=name), self.assertRaises(ValueError):
                check_environment({'TMPDIR': str(self.scratch), name: 'bad'}, self.scratch, [self.forbidden])
        check_environment({'TMPDIR': str(self.scratch), 'TRITON_CACHE_DIR': str(self.scratch / 'cache')},
                          self.scratch, [self.forbidden])
        with self.assertRaises(ValueError):
            check_environment({'TMPDIR': str(self.scratch), 'TRITON_CACHE_DIR': str(self.root)}, self.scratch, [])

    def test_descendant_boundary_hides_host_home_and_proc(self):
        command = confined_command(['/usr/bin/true'], readonly=['/usr/include', self.root / 'input'], temporary=self.scratch)
        self.assertIn('--unshare-pid', command)
        self.assertIn('--unshare-net', command)
        self.assertNotIn('--new-session', command)
        mounts = [command[i+1] for i, v in enumerate(command) if v in ('--bind', '--ro-bind')]
        self.assertNotIn('/', mounts)
        self.assertNotIn('/home', mounts)
        self.assertNotIn('/proc', mounts)
        self.assertEqual(mounts[-1], str(self.scratch))

    def policy(self):
        policy = NativeHelpers.__new__(NativeHelpers)
        policy.forbidden = [self.forbidden]
        policy.temporary = self.scratch
        policy.triton = self.root / 'triton'
        policy.interpreter = Path('/usr/bin/python3').resolve()
        policy.include = Path('/usr/include')
        policy.tools = {k: {'path': str(Path(v).resolve())} for k, v in {
            'ldconfig': '/sbin/ldconfig', 'file': '/usr/bin/file', 'cc': '/usr/bin/gcc',
            'bwrap': '/usr/bin/bwrap', 'ptxas': str(policy.triton / 'backends/nvidia/bin/ptxas')}.items()}
        policy.frame = lambda frames, relative, name: frames.get((relative, name))
        return policy

    def test_ldconfig_exact_callsite_argv_and_single_use(self):
        p = self.policy()
        env = {'TMPDIR': str(self.scratch), 'PATH': '/usr/bin:/usr/sbin'}
        frames = {('backends/nvidia/driver.py', 'libcuda_dirs'): True}
        with patch('vipe_benchmark.native_helpers.verify_record'):
            command, source, output, kind = p.admit(['/sbin/ldconfig', '-p'], frames, env)
        self.assertEqual(kind, 'ldconfig')
        self.assertIsNone(source)
        p.local = SimpleNamespace(permit=command)
        self.assertTrue(p.consume((command[0], command, None, env)))
        self.assertFalse(p.consume((command[0], command, None, env)))
        for args, caller in [(['/sbin/ldconfig'], frames), (['/sbin/ldconfig', '-p', '-N'], frames),
                             (['/sbin/ldconfig', '-p'], {}), (['/bin/sh', '-c', 'true'], frames)]:
            with self.subTest(args=args), self.assertRaises(PermissionError):
                p.admit(args, caller, env)

    def test_permit_rejects_executable_mismatch_and_is_consumed_on_rejection(self):
        p = self.policy()
        p.local = SimpleNamespace(permit=['/usr/bin/bwrap', '--fixture'])
        self.assertFalse(p.consume(('/bin/sh', ['/usr/bin/bwrap', '--fixture'], None, {})))
        self.assertIsNone(p.local.permit)

    def test_compiler_source_and_flags_bound_to_producer(self):
        p = self.policy()
        src = self.scratch / 'cuda_utils.c'
        src.write_text('int fixture;')
        driver = p.triton / 'backends/nvidia/driver.c'
        driver.parent.mkdir(parents=True)
        driver.write_text(src.read_text())
        output = self.scratch / 'cuda_utils.so'
        include = [str(p.triton / 'backends/nvidia/include'), str(self.scratch), str(p.include)]
        libs = [str(p.triton / 'backends/nvidia/lib'), '/usr/lib/x86_64-linux-gnu']
        values = dict(name='cuda_utils', src=str(src), so=str(output), ccflags=[], cc='/usr/bin/gcc',
                      library_dirs=libs, include_dirs=include, libraries=['libcuda.so.1'])
        frames = {('runtime/build.py', '_build'): SimpleNamespace(f_locals=values),
                  ('runtime/build.py', 'compile_module_from_src'): SimpleNamespace(f_locals={'src': src.read_text()}),
                  ('backends/nvidia/driver.py', '__init__'): SimpleNamespace(f_locals={})}
        argv = ['/usr/bin/gcc', str(src), '-O3', '-shared', '-fPIC', '-Wno-psabi', '-o', str(output),
                '-l:libcuda.so.1', *['-L'+v for v in libs], *['-I'+v for v in include]]
        env = {'TMPDIR': str(self.scratch)}
        with patch('vipe_benchmark.native_helpers.verify_record'):
            self.assertEqual(p.admit(argv, frames, env)[3], 'cc')
        with self.assertRaises(PermissionError):
            p.admit(argv + ['-fplugin=evil'], frames, env)
        src.write_text('tampered')
        with self.assertRaises(PermissionError):
            p.admit(argv, frames, env)

    def test_ptx_source_arch_and_flags_bound_to_producer(self):
        p = self.policy()
        src = self.scratch / 'fixture.ptx'
        src.write_text('fixture PTX')
        v = dict(fsrc=SimpleNamespace(name=str(src)), fbin=str(src)+'.o',
                 src=src.read_text(), opt=SimpleNamespace(enable_fp_fusion=True))
        frames = {('backends/nvidia/compiler.py', 'make_cubin'): SimpleNamespace(f_locals=v)}
        argv = [p.tools['ptxas']['path'], '-lineinfo', '-v', '--gpu-name=sm_89', str(src), '-o', str(src)+'.o']
        env = {'TMPDIR': str(self.scratch)}
        with patch('vipe_benchmark.native_helpers.verify_record'):
            self.assertEqual(p.admit(argv, frames, env)[3], 'ptxas')
        for bad in (argv + ['--opt-level=0'], [s.replace('sm_89', 'sm_90') for s in argv]):
            with self.assertRaises(PermissionError):
                p.admit(bad, frames, env)
        src.write_text('tampered')
        with self.assertRaises(PermissionError):
            p.admit(argv, frames, env)

    def test_version_helpers_require_exact_origin_and_interpreter(self):
        p = self.policy()
        env = {'TMPDIR': str(self.scratch), 'PATH': '/usr/bin', 'LC_ALL': 'C'}
        frames = {('platform', '_syscmd_file'): True, ('runtime/build.py', 'platform_key'): True}
        with patch('vipe_benchmark.native_helpers.verify_record'):
            p.admit(['file', '-b', str(p.interpreter)], frames, env)
            for origin in [('knobs.py', 'from_path'), ('backends/nvidia/compiler.py', 'get_ptxas_version')]:
                p.admit([p.tools['ptxas']['path'], '--version'], {origin: True}, env)
        with self.assertRaises(PermissionError):
            p.admit(['file', '-b', '/usr/bin/true'], frames, env)
        with self.assertRaises(PermissionError):
            p.admit([p.tools['ptxas']['path'], '--version'], {}, env)


class ReconstructionRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.config = load()
        self.ledger = Ledger(self.root / 'ledger.jsonl', self.config)
        self.ledger.reserve('S3-reconstruction', [], {})
        failure = self.ledger.finish('S3-reconstruction', 'failed', 11.236, cleanup_confirmed=True)
        src = self.root / 'source.py'
        src.write_text('fixture')
        validation = self.root / 'validation.json'
        write_json(validation, dict(status='passed', sources=[file_record(src)]))
        self.document = dict(schema='vipe-benchmark-s3-reconstruction-recovery/v1',
            job_id='S3-reconstruction-recovery-001', original_job_id='S3-reconstruction',
            attempts_limit=1, seconds_limit=5400, reset_previous_consumption=False,
            gpu_total_seconds_limit=self.config['gpu_total_seconds_limit'], unrelated_attempts_reopened=False,
            authorization='fixture explicit user authorization', repair_validation=file_record(validation),
            original_failure_event_sha256=failure['event_sha256'])

    def authorize(self, **changes):
        path = self.root / ('authorization-' + str(len(list(self.root.glob('authorization*')))) + '.json')
        write_json(path, dict(self.document, **changes))
        return self.ledger.authorize_reconstruction_recovery(file_record(path))

    def test_one_new_attempt_preserves_original_and_cumulative_cap(self):
        original = self.ledger.path.read_bytes()
        self.authorize()
        self.assertTrue(self.ledger.path.read_bytes().startswith(original))
        reservation = self.ledger.reserve('S3-reconstruction-recovery-001', [], {})
        self.assertEqual(reservation['seconds'], 5400)
        self.ledger.finish('S3-reconstruction-recovery-001', 'failed', 12, cleanup_confirmed=True)
        self.assertEqual(self.ledger.totals()['gpu']['attempts'], 2)
        self.assertEqual(self.ledger.totals()['gpu']['elapsed_seconds'], 23.236)
        with self.assertRaises(ValueError):
            self.authorize()
        with self.assertRaises(ValueError):
            self.ledger.reserve('S3-reconstruction-recovery-001', [], {})
        with self.assertRaises(ValueError):
            self.ledger.reserve('S3-reconstruction', [], {})

    def test_scope_changes_unregistered_attempt_and_note_bypass_rejected(self):
        for change in (dict(seconds_limit=5401), dict(attempts_limit=2), dict(job_id='S3-reconstruction-recovery-002'),
                       dict(original_failure_event_sha256='bad'), dict(unrelated_attempts_reopened=True)):
            with self.subTest(change=change), self.assertRaises(ValueError):
                self.authorize(**change)
        with self.assertRaises(ValueError):
            self.ledger.reserve('S3-reconstruction-recovery-001', [], {})
        with self.assertRaises(ValueError):
            self.ledger.note('reconstruction_recovery_authorized')

    def test_cumulative_gpu_limit_can_shorten_recovery(self):
        self.config['gpu_total_seconds_limit'] = 20.
        self.document['gpu_total_seconds_limit'] = 20.
        self.authorize()
        self.assertAlmostEqual(self.ledger.reserve('S3-reconstruction-recovery-001', [], {})['seconds'], 8.764)

    def test_downstream_resolves_recovery_without_relabeling_original_failure(self):
        from vipe_benchmark.execution import result_record
        self.authorize()
        job = 'S3-reconstruction-recovery-001'
        path = self.root / 'jobs' / job / 'result.json'
        write_json(path, dict(status='complete', job_id=job, component='S3', branch='reconstruction', rows=[{}]*840))
        self.ledger.reserve(job, [], {})
        self.ledger.finish(job, 'complete', 10, result=file_record(path), cleanup_confirmed=True)
        self.assertEqual(result_record(self.root, 'S3-reconstruction'), file_record(path))
        self.assertEqual(self.ledger.states()['S3-reconstruction']['status'], 'failed')

import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

HERE = Path(__file__).parent
spec = importlib.util.spec_from_file_location('wrapper', HERE / 'capture_wrapper.py')
wrapper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(wrapper)


class WrapperTests(unittest.TestCase):
    def test_native_socket_denied_and_exec_inherits(self):
        probe = "import ctypes; c=ctypes.CDLL(None,use_errno=True); r=c.socket(2,1,0); assert r==-1 and ctypes.get_errno()==1,(r,ctypes.get_errno())"
        program = probe + "; import subprocess,sys; subprocess.run([sys.executable,'-I','-B','-c'," + repr(probe) + "],check=True)"
        result = subprocess.run([sys.executable, '-B', str(HERE / 'capture_wrapper.py'), 'sandbox', '--',
            sys.executable, '-I', '-B', '-c', program], capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_changed_bootstrap_rejected_before_output(self):
        with tempfile.TemporaryDirectory() as temporary:
            request = Path(temporary) / 'request.json'
            output = Path(temporary) / 'out'
            request.write_text(json.dumps(dict(schema='plan069-moge-parent-cpu-request/v1', candidate='D6',
                bootstrap=dict(wrapper.record(sys.executable), sha256='wrong'), output=str(output))))
            with self.assertRaisesRegex(ValueError, 'bootstrap'):
                wrapper.run(request)
            self.assertFalse(output.exists())

    def test_disk_deduplicates_hardlinks_and_ignores_symlinks(self):
        import os
        with tempfile.TemporaryDirectory() as temporary:
            p = Path(temporary)
            (p / 'data').write_bytes(b'a' * 4096)
            os.link(p / 'data', p / 'linked')
            (p / 'symlink').symlink_to(p / 'data')
            self.assertEqual(wrapper.disk_bytes(p), (p / 'data').stat().st_blocks * 512)


class IdentityTests(unittest.TestCase):
    def test_reused_pid_is_pinned_as_new_identity(self):
        from unittest.mock import patch
        import os
        observed = {(12345, 1): dict(pid=12345, ppid=os.getpid(), start_ticks=1, state='S', pidfd=900)}
        current = {12345: dict(pid=12345, ppid=os.getpid(), start_ticks=2, state='S')}
        with patch.object(wrapper, 'census', return_value=current), patch.object(wrapper.os, 'pidfd_open', return_value=901) as pin:
            wrapper.observe_descendants(observed)
        self.assertEqual(set(observed), {(12345, 1), (12345, 2)})
        pin.assert_called_once_with(12345)


class OrchestrationTests(unittest.TestCase):
    def request(self, directory):
        root = Path(directory)
        method = root / 'fake-producer.py'
        method.write_text('''import hashlib,json,pathlib,subprocess,sys,time
out=pathlib.Path(sys.argv[sys.argv.index('--output')+1]);out.mkdir()
subprocess.Popen([sys.executable,'-I','-B','-c','import time;time.sleep(60)'])
subprocess.Popen([sys.executable,'-I','-B','-c','import time;time.sleep(60)'])
time.sleep(.3)
p=out/'native-cpu.json';p.write_text('{"fixture":true}')
r=dict(path=str(p),bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest())
(out/'capture.json').write_text(json.dumps(dict(schema='plan069-moge-cpu-capture/v1',candidate='D6',status='passed',cleanup_confirmed=True,native_cpu=r)))
''')
        bindings = {}
        for role in ('setup', 'setup_request', 'setup_dispatch', 'runtime_recipe'):
            p = root / (role + '.json')
            p.write_text('{}')
            bindings[role] = wrapper.record(p)
        bindings['setup']['sha256'] = 'cfd509169b491162d74685792dcab28afa7e126230080f58e013f2dd13a6909e'
        review = root / 'source-review.json'
        review.write_text(json.dumps(dict(candidate='D6',status='passed',root_source_commit='b8e63680',
            runtime_recipe=bindings['runtime_recipe'],local_sources=[])))
        bindings['source_review'] = wrapper.record(review)
        command = [sys.executable,'-B',str(method),'capture','--root',str(root),'--candidate','D6',
            '--setup',bindings['setup']['path'],'--setup-request',bindings['setup_request']['path'],
            '--setup-dispatch',bindings['setup_dispatch']['path'],'--output',str(root/'capture'),'--seconds','1','--artifact-bytes','67108864']
        request = root / 'request.json'
        request.write_text(json.dumps(dict(schema='plan069-moge-parent-cpu-request/v1',candidate='D6',bootstrap=wrapper.record(Path(sys.executable).resolve()),interpreter_invocation=sys.executable,accepted_setup_sha256='cfd509169b491162d74685792dcab28afa7e126230080f58e013f2dd13a6909e',root_source_commit='b8e63680',
            seconds=6,cleanup_seconds=5,cpu_workers=7,admitted=True,charge_owner='root',bindings=bindings,
            command=command,method=wrapper.record(method),root=str(root),output=str(root/'wrapper'),
            disk_roots=[dict(role=role,path=str(root),maximum_total_bytes=100000000,maximum_delta_bytes=100000000)
                        for role in ('global','candidate','runtime-cache')])))
        original = wrapper.record
        def record(path):
            return bindings['setup'] if Path(path) == root/'setup.json' else original(path)
        return request, record

    def test_exit_race_continues_other_descendant_cleanup(self):
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as temporary:
            request, record = self.request(temporary)
            original = wrapper.signal.pidfd_send_signal
            calls = []
            def kill(descriptor, signum):
                calls.append(descriptor)
                if len(calls) == 1:
                    raise ProcessLookupError('fixture exited after census')
                return original(descriptor, signum)
            with patch.object(wrapper,'record',side_effect=record), patch.object(wrapper.signal,'pidfd_send_signal',side_effect=kill):
                wrapper.run(request)
            result=json.loads((Path(temporary)/'wrapper/result.json').read_text())
            self.assertEqual(result['status'],'passed')
            self.assertTrue(result['cleanup_confirmed'])
            self.assertGreaterEqual(len(calls),3)

    def test_final_elapsed_overrun_cannot_exit_success(self):
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as temporary:
            request, record = self.request(temporary)
            original = wrapper.time.monotonic
            checks = []
            def clock():
                value=original()
                # Advance only after all descendant identities were retired.
                if checks and checks[-1]:
                    return value+10
                return value
            disk=wrapper.disk_bytes
            def sample(path):
                value=disk(path)
                # Final disk census occurs after cleanup_confirmed; fake current
                # live census remains empty only after fake capture child cleanup.
                if (Path(temporary)/'capture/capture.json').exists():
                    live=[i for i in wrapper.census().values() if i['ppid']==__import__('os').getpid() and i['state']!='Z']
                    checks.append(not live)
                return value
            with patch.object(wrapper,'record',side_effect=record),patch.object(wrapper.time,'monotonic',side_effect=clock),patch.object(wrapper,'disk_bytes',side_effect=sample):
                with self.assertRaises(ValueError):
                    wrapper.run(request)
            result=json.loads((Path(temporary)/'wrapper/result.json').read_text())
            self.assertEqual(result['status'],'failed')


class OutputScopeTests(unittest.TestCase):
    def test_symlink_parent_rejected_before_producer_runs(self):
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as temporary:
            request, record = OrchestrationTests().request(temporary)
            root=Path(temporary)
            actual=root/'elsewhere';actual.mkdir()
            link=root/'link';link.symlink_to(actual,target_is_directory=True)
            config=json.loads(request.read_text())
            config['command'][config['command'].index('--output')+1]=str(link/'capture')
            request.write_text(json.dumps(config))
            with patch.object(wrapper,'record',side_effect=record):
                with self.assertRaisesRegex(ValueError,'symlink'):wrapper.run(request)
            self.assertFalse((root/'wrapper').exists())
            self.assertFalse((actual/'capture').exists())


if __name__ == '__main__':
    unittest.main()

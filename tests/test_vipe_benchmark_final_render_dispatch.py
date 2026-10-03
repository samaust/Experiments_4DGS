"""Disposable process fixtures at the worker request/result and ledger seams."""
import importlib
from pathlib import Path
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from vipe_benchmark.files import file_record,read_json


class DispatchTests(unittest.TestCase):
    def setUp(self):
        self.fixture=importlib.import_module('test_vipe_benchmark_final_render_pipeline').PipelineTests()
        self.fixture.setUp();self.addCleanup(self.fixture.doCleanups)
        self.root=self.fixture.fixture.base.root
        self.request=self.fixture.request

    def worker(self,code):
        path=self.root/'fixture-worker.py';path.write_text(code)
        return file_record(path)

    def complete_worker(self,extra=''):
        return self.worker('''import json,os,sys
from pathlib import Path
from vipe_benchmark.files import file_record,object_hash,write_json
p=Path(sys.argv[1]);request=json.loads(Path(sys.argv[2]).read_text());p.mkdir()
assert os.environ['CUDA_VISIBLE_DEVICES']==''
'''+extra+'''
(p/'artifact.bin').write_bytes(b'fixture')
result=dict(schema='plan069-final-render-worker-result/v1',record_kind='fixture',status='complete',
arm='QF-B',phase='geometry',composition=request['compositions']['QF-B'],request_sha256=object_hash(request),
allocation_id=request['id']+'/QF-B/geometry',parent_result=None,elapsed_seconds=.25,
peak_device_bytes=0,artifact_bytes=7,cpu_workers_used=1,execution_authorized=False,
native_adapter_qualified=False,artifacts=[file_record(p/'artifact.bin')])
write_json(p/'result.json',result)
sys.exit(0)
''')

    def test_complete_fixture_is_bound_and_charged_with_confirmed_cleanup(self):
        from vipe_benchmark.final_render_dispatch import FixtureDispatcher
        worker=self.complete_worker()
        dispatcher=FixtureDispatcher(self.request,self.root/'dispatch')
        receipt=dispatcher.dispatch('QF-B','geometry',worker,seconds_limit=5.)
        self.assertEqual(receipt['status'],'complete')
        self.assertTrue(receipt['cleanup_confirmed'])
        self.assertFalse(receipt['execution_authorized'])
        ledger=dispatcher.ledger
        state=ledger.states()[receipt['job_id']]
        self.assertEqual(state['status'],'complete')
        self.assertEqual(state['resource'],'cpu')
        self.assertGreater(ledger.totals()['cpu']['elapsed_seconds'],0.)
        self.assertEqual(receipt['worker_result'],file_record(dispatcher.root/'QF-B-geometry/result.json'))
        self.assertEqual(read_json(receipt['worker_result']['path'])['artifacts'][0]['bytes'],7)

    def test_numerical_pool_obeys_one_cpu_allowance_before_import(self):
        from vipe_benchmark.final_render_dispatch import FixtureDispatcher
        self.request['cpu_workers_limit']=1
        self.fixture.fixture.rebind_proposal()
        worker=self.complete_worker("import numpy as np\nnp.ones((4,4))@np.ones((4,4))\nassert len(list(Path('/proc/self/task').iterdir()))<=1\n")
        dispatcher=FixtureDispatcher(self.request,self.root/'one-cpu-dispatch')
        result=dispatcher.dispatch('QF-B','geometry',worker,seconds_limit=5.)
        self.assertEqual(result['status'],'complete')
        self.assertEqual(result['cpu_workers_used'],1)

    def test_fixture_resource_overrun_is_charged_and_stops_owned_group(self):
        from vipe_benchmark.final_render_dispatch import FixtureDispatcher
        worker=self.worker('import time;time.sleep(20)')
        dispatcher=FixtureDispatcher(self.request,self.root/'resource-dispatch')
        with self.assertRaisesRegex(RuntimeError,'device.*ceiling'):
            dispatcher.dispatch('QF-B','geometry',worker,seconds_limit=2.,
                resource_samples=({'device_bytes':0},{'device_bytes':23*2**30}))
        states=dispatcher.ledger.states();state=next(iter(states.values()))
        self.assertEqual(state['status'],'failed')
        self.assertTrue(state['cleanup_confirmed'])
        self.assertGreater(dispatcher.ledger.totals()['cpu']['elapsed_seconds'],0.)

    def test_deadline_preserves_partial_files_and_confirms_group_cleanup(self):
        from vipe_benchmark.final_render_dispatch import FixtureDispatcher
        worker=self.worker('''import signal,sys,time
from pathlib import Path
p=Path(sys.argv[1]);p.mkdir();(p/'partial.bin').write_bytes(b'keep')
signal.signal(signal.SIGTERM,signal.SIG_IGN);time.sleep(20)
''')
        dispatcher=FixtureDispatcher(self.request,self.root/'timeout-dispatch')
        with self.assertRaisesRegex(RuntimeError,'deadline'):
            dispatcher.dispatch('QF-B','geometry',worker,seconds_limit=1.)
        state=next(iter(dispatcher.ledger.states().values()))
        self.assertEqual(state['status'],'failed')
        self.assertTrue(state['cleanup_confirmed'])
        self.assertEqual(state['surviving_pids'],[])
        self.assertLess(state['elapsed_seconds'],1.1)
        self.assertEqual((dispatcher.root/'QF-B-geometry/partial.bin').read_bytes(),b'keep')

    def test_actual_request_and_changed_script_are_rejected_before_reservation(self):
        from vipe_benchmark.final_render_dispatch import FixtureDispatcher
        actual=dict(self.request,record_kind='actual');root=self.root/'actual-dispatch'
        with self.assertRaisesRegex(ValueError,'fixture-only'):
            FixtureDispatcher(actual,root)
        self.assertFalse(root.exists())
        dispatcher=FixtureDispatcher(self.request,self.root/'changed-worker-dispatch')
        worker=self.worker('pass');Path(worker['path']).write_text('raise RuntimeError("changed")')
        with self.assertRaisesRegex(ValueError,'changed file'):
            dispatcher.dispatch('QF-B','geometry',worker)
        self.assertEqual(dispatcher.ledger.events(),[])

    def test_application_failure_consumes_identity_and_preserves_output(self):
        from vipe_benchmark.final_render_dispatch import FixtureDispatcher
        worker=self.worker('''import sys
from pathlib import Path
p=Path(sys.argv[1]);p.mkdir();(p/'partial.bin').write_bytes(b'keep')
raise ValueError('synthetic application failure')
''')
        dispatcher=FixtureDispatcher(self.request,self.root/'failed-dispatch')
        with self.assertRaisesRegex(RuntimeError,'worker exited'):
            dispatcher.dispatch('QF-B','geometry',worker,seconds_limit=2.)
        before=dispatcher.ledger.events()
        with self.assertRaises((ValueError,FileExistsError)):
            dispatcher.dispatch('QF-B','geometry',worker,seconds_limit=2.)
        self.assertEqual(dispatcher.ledger.events(),before)
        self.assertEqual((dispatcher.root/'QF-B-geometry/partial.bin').read_bytes(),b'keep')

    def test_cpu_cumulative_allowance_and_active_reservation_block_dispatch(self):
        from vipe_benchmark.final_render_dispatch import FixtureDispatcher
        dispatcher=FixtureDispatcher(self.request,self.root/'cumulative-dispatch')
        worker=self.worker('pass');ledger=dispatcher.ledger
        identity=f"fixture/{self.request['id']}/QF-B/geometry"
        ledger.reserve(identity,[],{'record_kind':'fixture'})
        with self.assertRaisesRegex(ValueError,'active attempt'):
            dispatcher.dispatch('QF-M1','geometry',worker)
        cap=ledger.config['cpu_prepare_score_report_seconds_limit']
        ledger.finish(identity,'failed',cap,cleanup_confirmed=True,cleanup_uncertain=False)
        with self.assertRaisesRegex(ValueError,'allocation exhausted'):
            dispatcher.dispatch('QF-M2','geometry',worker)
        self.assertEqual(ledger.totals()['cpu']['elapsed_seconds'],cap)
        self.assertFalse((dispatcher.root/'QF-M2-geometry').exists())

    def test_live_child_after_worker_exit_invalidates_success_and_is_cleaned(self):
        from vipe_benchmark.final_render_dispatch import FixtureDispatcher
        worker=self.worker('''import subprocess,sys
subprocess.Popen([sys.executable,'-c','import time;time.sleep(20)'])
''')
        dispatcher=FixtureDispatcher(self.request,self.root/'child-dispatch')
        with self.assertRaises(RuntimeError):
            dispatcher.dispatch('QF-B','geometry',worker,seconds_limit=2.)
        state=next(iter(dispatcher.ledger.states().values()))
        self.assertEqual(state['status'],'failed')
        self.assertTrue(state['cleanup_confirmed'])
        self.assertEqual(state['surviving_pids'],[])


if __name__=='__main__':unittest.main()

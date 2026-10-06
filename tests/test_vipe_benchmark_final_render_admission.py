"""CPU fixture tests at the public admission and locked ledger seams."""
import importlib
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))

class AdmissionTests(unittest.TestCase):
    def setUp(self):
        self.fixture=importlib.import_module('test_vipe_benchmark_extended_final_render_contract').AdmissionTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)

    def test_fixture_review_never_grants_actual_reservation(self):
        from vipe_benchmark.final_render_admission import reserve
        from vipe_benchmark.ledger import Ledger
        ledger=Ledger(self.fixture.base.root/'admission-ledger.jsonl',self.fixture.ledger.config)
        request=self.fixture.record('admission-request',self.fixture.request)
        envelope=self.fixture.record('do-envelope',dict(schema='plan069-final-render-do/v1',record_kind='actual',mode='DO',request=request))
        with self.assertRaisesRegex(ValueError,'actual REVIEW'):
            reserve(envelope,ledger,'QF-B','geometry',['fake'],probe=lambda: {})
        self.assertEqual(ledger.events(),[])

    def simulate(self):
        import json
        from vipe_benchmark.files import object_hash
        from vipe_benchmark.ledger import Ledger
        path=self.fixture.base.root/'fixture-ledger.jsonl'
        previous=None
        with path.open('x') as stream:
            for i,event in enumerate(self.fixture.base.events):
                row=dict(event,resource='cpu',elapsed_seconds=0.,record_kind='fixture',sequence=i,previous_sha256=previous,recorded_unix=0.)
                previous=object_hash(row)
                stream.write(json.dumps(dict(row,event_sha256=previous))+'\n')
        ledger=Ledger(path,self.fixture.ledger.config)
        request=self.fixture.record('simulation-request',self.fixture.request)
        envelope=self.fixture.record('simulation-envelope',dict(schema='plan069-final-render-do/v1',record_kind='fixture',mode='SIMULATE',request=request))
        import time
        live=dict(self.fixture.storage,device_bytes=0,gpu_pids=[],cpu_workers_used=0,cleanup_confirmed=True,observed_unix=time.time())
        return envelope,ledger,live

    def test_private_fixture_reserves_cpu_and_consumes_exact_identity(self):
        from vipe_benchmark.final_render_admission import reserve_fixture
        envelope,ledger,live=self.simulate()
        event=reserve_fixture(envelope,ledger,'QF-B','geometry',['fixture-worker'],probe=lambda:live)
        self.assertEqual(event['job_id'],'fixture/extended-001/QF-B/geometry')
        self.assertEqual((event['resource'],event['seconds']),('cpu',5400))
        self.assertFalse(event['evidence']['execution_authorized'])
        self.assertFalse(event['evidence']['native_adapter_qualified'])
        with self.assertRaisesRegex(ValueError,'active'):
            reserve_fixture(envelope,ledger,'QF-M1','geometry',['fixture-worker'],probe=lambda:live)
        ledger.finish(event['job_id'],'failed',3.,cleanup_confirmed=True,cleanup_uncertain=False)
        with self.assertRaisesRegex(ValueError,'consumed'):
            reserve_fixture(envelope,ledger,'QF-B','geometry',['fixture-worker'],probe=lambda:live)

    def test_deep_depth_validation_runs_before_the_ledger_lock(self):
        # Actual D* re-derivation reads the shared ledger; under the reservation
        # flock that read would deadlock the dispatcher against itself.
        import fcntl
        from unittest import mock
        from vipe_benchmark import depth_review
        from vipe_benchmark.final_render_admission import reserve_fixture
        envelope,ledger,live=self.simulate()
        original=depth_review.validate_decision
        lock_free=[]
        def probing(record,*,actual=True):
            with ledger.path.open('r') as stream:
                try:
                    fcntl.flock(stream,fcntl.LOCK_EX|fcntl.LOCK_NB)
                    lock_free.append(True)
                    fcntl.flock(stream,fcntl.LOCK_UN)
                except BlockingIOError:
                    lock_free.append(False)
            return original(record,actual=actual)
        with mock.patch.object(depth_review,'validate_decision',probing):
            reserve_fixture(envelope,ledger,'QF-B','geometry',['fixture-worker'],probe=lambda:live)
        self.assertEqual(lock_free,[True])

    def test_live_gpu_or_stale_probe_never_mutates_ledger(self):
        from vipe_benchmark.final_render_admission import reserve_fixture
        envelope,ledger,live=self.simulate()
        before=ledger.events()
        for change in (dict(gpu_pids=[12]),dict(observed_unix=0.),dict(cleanup_confirmed=False),dict(device_bytes=1)):
            with self.assertRaises(ValueError):
                reserve_fixture(envelope,ledger,'QF-B','geometry',['fixture-worker'],probe=lambda:dict(live,**change))
            self.assertEqual(ledger.events(),before)

    def test_next_stage_requires_exact_successful_cleaned_parent(self):
        from vipe_benchmark.final_render_admission import reserve_fixture
        envelope,ledger,live=self.simulate()
        before=ledger.events()
        with self.assertRaisesRegex(ValueError,'predecessor'):
            reserve_fixture(envelope,ledger,'QF-B','initializer',['fixture-worker'],probe=lambda:live)
        self.assertEqual(ledger.events(),before)
        event=reserve_fixture(envelope,ledger,'QF-B','geometry',['fixture-worker'],probe=lambda:live)
        result=self.fixture.record('geometry-result',dict(record_kind='fixture',status='complete'))
        ledger.finish(event['job_id'],'complete',3.,cleanup_confirmed=True,cleanup_uncertain=False,result=result)
        next_event=reserve_fixture(envelope,ledger,'QF-B','initializer',['fixture-worker'],probe=lambda:live,parent_result=result)
        self.assertEqual(next_event['seconds'],900)

    def test_unregistered_fixture_process_cannot_enter_native_gate(self):
        from vipe_benchmark.final_render_admission import worker_binding
        envelope,ledger,live=self.simulate()
        invocation=self.fixture.record('fixture-invocation',dict(schema='plan069-final-render-actual-invocation/v1',record_kind='fixture'))
        with self.assertRaisesRegex(ValueError,'actual'):
            worker_binding(invocation,self.fixture.request,'QF-B','geometry')

    def test_parallel_private_reservations_are_serialized(self):
        from concurrent.futures import ThreadPoolExecutor
        from vipe_benchmark.final_render_admission import reserve_fixture
        envelope,ledger,live=self.simulate()
        def attempt(arm):
            try:
                return reserve_fixture(envelope,ledger,arm,'geometry',['fixture-worker'],probe=lambda:live)
            except ValueError:
                return None
        with ThreadPoolExecutor(max_workers=2) as pool:
            results=list(pool.map(attempt,['QF-B','QF-M1']))
        self.assertEqual(sum(r is not None for r in results),1)
        self.assertEqual(sum(e['event']=='reserve' for e in ledger.events()),1)

    def test_cumulative_phase_time_remains_charged_after_finish(self):
        from vipe_benchmark.final_render_admission import reserve_fixture
        envelope,ledger,live=self.simulate()
        event=reserve_fixture(envelope,ledger,'QF-B','geometry',['fixture-worker'],probe=lambda:live)
        ledger.finish(event['job_id'],'failed',57500.,cleanup_confirmed=True,cleanup_uncertain=False)
        before=ledger.events()
        with self.assertRaisesRegex(ValueError,'CPU|cumulative'):
            reserve_fixture(envelope,ledger,'QF-M1','geometry',['fixture-worker'],probe=lambda:live)
        self.assertEqual(ledger.events(),before)

    def test_over_deadline_parent_cannot_advance_even_when_marked_complete(self):
        from vipe_benchmark.final_render_admission import reserve_fixture
        envelope,ledger,live=self.simulate()
        event=reserve_fixture(envelope,ledger,'QF-B','geometry',['fixture-worker'],probe=lambda:live)
        result=self.fixture.record('late-geometry',dict(record_kind='fixture',status='complete'))
        ledger.finish(event['job_id'],'complete',5401.,cleanup_confirmed=True,cleanup_uncertain=False,result=result)
        before=ledger.events()
        with self.assertRaisesRegex(ValueError,'predecessor'):
            reserve_fixture(envelope,ledger,'QF-B','initializer',['fixture-worker'],probe=lambda:live,parent_result=result)
        self.assertEqual(ledger.events(),before)

    def test_uncertain_finished_cleanup_blocks_another_arm(self):
        from vipe_benchmark.final_render_admission import reserve_fixture
        envelope,ledger,live=self.simulate()
        event=reserve_fixture(envelope,ledger,'QF-B','geometry',['fixture-worker'],probe=lambda:live)
        ledger.finish(event['job_id'],'failed',3.,cleanup_confirmed=False,cleanup_uncertain=True)
        before=ledger.events()
        with self.assertRaisesRegex(ValueError,'cleanup'):
            reserve_fixture(envelope,ledger,'QF-M1','geometry',['fixture-worker'],probe=lambda:live)
        self.assertEqual(ledger.events(),before)
        self.assertEqual(ledger.totals()['cpu']['elapsed_seconds'],3.)

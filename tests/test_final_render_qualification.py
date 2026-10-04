"""Public qualification admission boundary; private CPU simulations grant no DO."""
import importlib
from pathlib import Path
import sys
import time
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))


class QualificationTests(unittest.TestCase):
    def setUp(self):
        self.fixture=importlib.import_module('test_vipe_benchmark_extended_final_render_contract').AdmissionTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)

    def test_fixture_request_cannot_bootstrap_actual_native_qualification(self):
        from vipe_benchmark.final_render_qualification import reserve
        from vipe_benchmark.ledger import Ledger
        request=self.fixture.record('qualification-request',self.fixture.request)
        authority=self.fixture.record('qualification-authority',dict(
            schema='plan069-final-render-qualification-do/v1',record_kind='actual',mode='QUALIFY',request=request))
        ledger=Ledger(self.fixture.base.root/'qualification-ledger.jsonl',self.fixture.ledger.config)
        with self.assertRaisesRegex(ValueError,'actual REVIEW'):
            reserve(authority,ledger,'geometry',['fake'],probe=lambda:{})
        self.assertEqual(ledger.events(),[])

    def simulation(self):
        from vipe_benchmark.files import file_record
        from vipe_benchmark.ledger import Ledger
        request=self.fixture.record('simulated-qualification-request',self.fixture.request)
        allocations=[dict(id='native-qualification/probe-001/'+phase,phase=phase,resource=resource,seconds=60,
            scope=dict(purpose='compatibility',actions=['observe '+phase],settings={'case':'cpu fixture'},
                production_adequacy_established=False)) for phase,resource in
            [('geometry','gpu'),('initializer','cpu'),('train','gpu'),('render','gpu')]]
        envelope=dict(schema='plan069-final-render-qualification-do/v1',record_kind='fixture',mode='SIMULATE',
            request=request,approval=None,commercial=None,source_review=None,source_files=[],
            runtime=self.fixture.request['bindings']['runtime'],matcher_runtime=None,checkout=None,
            interpreter=None,interpreter_invocation=None,worker=None,arm='QF-B',allocations=allocations,
            commands={a['phase']:['fixture-worker','--phase',a['phase']] for a in allocations},ledger_head_sha256=None)
        authority=self.fixture.record('simulated-qualification-authority',envelope)
        ledger=Ledger(self.fixture.base.root/'fixture-ledger.jsonl',self.fixture.ledger.config)
        live=dict(self.fixture.storage,device_bytes=0,gpu_pids=[],cpu_workers_used=0,
            cleanup_confirmed=True,observed_unix=time.time())
        return authority,ledger,live,envelope

    def test_private_cpu_probe_consumes_fresh_identity_without_production_qualification(self):
        from vipe_benchmark.final_render_qualification import reserve_fixture
        authority,ledger,live,envelope=self.simulation()
        reservation=reserve_fixture(authority,ledger,'geometry',envelope['commands']['geometry'],probe=lambda:live)
        self.assertEqual(reservation['job_id'],'fixture/native-qualification/probe-001/geometry')
        self.assertEqual(reservation['resource'],'cpu')
        self.assertFalse(reservation['evidence']['execution_authorized'])
        self.assertFalse(reservation['evidence']['native_adapter_qualified'])
        self.assertEqual(reservation['evidence']['scope']['purpose'],'compatibility')
        ledger.finish(reservation['job_id'],'failed',2.,record_kind='fixture',cleanup_confirmed=True,cleanup_uncertain=False)
        with self.assertRaisesRegex(ValueError,'consumed'):
            reserve_fixture(authority,ledger,'geometry',envelope['commands']['geometry'],probe=lambda:live)

    def test_fixture_result_cannot_become_measured_native_probe(self):
        from vipe_benchmark.final_render_qualification import validate_phase_result
        invocation=self.fixture.record('fixture-probe-invocation',dict(record_kind='fixture'))
        with self.assertRaisesRegex(ValueError,'actual'):
            validate_phase_result(dict(record_kind='fixture',status='passed'),invocation)

    def test_nominal_scope_cannot_claim_production_adequacy(self):
        from vipe_benchmark.final_render_qualification import validate_scope
        with self.assertRaisesRegex(ValueError,'adequacy'):
            validate_scope(dict(purpose='compatibility',actions=['small probe'],settings={'steps':2},
                production_adequacy_established=True))

    def test_serial_cpu_simulations_cannot_advance_without_clean_predecessor(self):
        from vipe_benchmark.final_render_qualification import reserve_fixture
        authority,ledger,live,envelope=self.simulation()
        before=ledger.events()
        with self.assertRaisesRegex(ValueError,'predecessor'):
            reserve_fixture(authority,ledger,'initializer',envelope['commands']['initializer'],probe=lambda:live)
        self.assertEqual(ledger.events(),before)
        reservation=reserve_fixture(authority,ledger,'geometry',envelope['commands']['geometry'],probe=lambda:live)
        result=self.fixture.record('probe-measurement',dict(record_kind='fixture',status='measured'))
        ledger.finish(reservation['job_id'],'complete',3.,record_kind='fixture',cleanup_confirmed=True,
            cleanup_uncertain=False,result=result)
        next_phase=reserve_fixture(authority,ledger,'initializer',envelope['commands']['initializer'],
            probe=lambda:live,parent_result=result)
        self.assertEqual(next_phase['resource'],'cpu')
        self.assertFalse(next_phase['evidence']['native_adapter_qualified'])
        with self.assertRaisesRegex(ValueError,'active'):
            reserve_fixture(authority,ledger,'train',envelope['commands']['train'],probe=lambda:live)

    def test_foreign_gpu_and_cumulative_budget_reject_without_mutation(self):
        from vipe_benchmark.final_render_qualification import reserve_fixture
        authority,ledger,live,envelope=self.simulation()
        for change in (dict(gpu_pids=[91]),dict(cleanup_confirmed=False),dict(observed_unix=0.)):
            with self.assertRaises(ValueError):
                reserve_fixture(authority,ledger,'geometry',envelope['commands']['geometry'],probe=lambda:dict(live,**change))
            self.assertEqual(ledger.events(),[])
        ledger.config=dict(ledger.config,cpu_prepare_score_report_seconds_limit=239)
        with self.assertRaisesRegex(ValueError,'cumulative'):
            reserve_fixture(authority,ledger,'geometry',envelope['commands']['geometry'],probe=lambda:live)
        self.assertEqual(ledger.events(),[])

    def test_qualification_approval_head_cannot_be_reused_after_unrelated_write(self):
        from vipe_benchmark.final_render_qualification import reserve_fixture
        authority,ledger,live,envelope=self.simulation()
        with ledger.locked() as (stream,events):
            ledger._append(stream,events,dict(event='fixture-note',record_kind='fixture'))
        before=ledger.events()
        with self.assertRaisesRegex(ValueError,'head changed'):
            reserve_fixture(authority,ledger,'geometry',envelope['commands']['geometry'],probe=lambda:live)
        self.assertEqual(ledger.events(),before)

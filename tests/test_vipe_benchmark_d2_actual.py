from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

from vipe_benchmark import d2_actual as actual
from vipe_benchmark.files import file_record, object_hash, read_json, write_json
from vipe_benchmark.d2_maps import RESULT_SCHEMA
from vipe_benchmark.d2_preflight import SCHEMA as PREFLIGHT


class FakeLedger:
    def __init__(self, path, config):
        self.path, self.config = path, config
        self.current = {}
        self.history = []
        self.authorizations = []
        self.charges = []

    def states(self, _events=None):
        return self.current

    def events(self):
        return self.history

    def totals(self, _events=None):
        return {key: dict(elapsed_seconds=0, reserved_seconds=0)
                for key in ('gpu', 'cpu', 'setup')}

    def authorize_depth_attempt(self, *args, **kwargs):
        self.authorizations.append((args, kwargs))

    def charge_cpu_preparation(self, seconds, evidence):
        self.charges.append((seconds, evidence))


class D2ActualTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.local = self.root / '.local/vipe-alternatives' / actual.RUN
        self.local.mkdir(parents=True)
        self.ledger = FakeLedger(self.local / 'ledger.jsonl', {})
        self.proposal = dict(candidate='D2', max_attempts=1, allocation=dict(gpu_seconds=3600))
        self.review = self.record(self.root / 'review.json', dict(proposals=[self.proposal]))
        self.do = self.root / 'DO.json'
        self.record(self.do, dict(review=self.review, candidate_approvals=[dict(candidate='D2')],
            cap_amendment={}, cap_approval={}))
        self.source = self.root / 'source.json'
        self.record(self.source, dict(status='passed'))
        self.inputs = self.record(self.local / 'prepare/inputs.json', {})
        rgb = self.root / 'rgb.bin'
        rgb.write_bytes(b'accepted rgb')
        self.rgb = file_record(rgb)
        prediction = self.root / 'depth.npz'
        prediction.write_bytes(b'frozen depth fixture')
        self.prediction = file_record(prediction)
        self.rows = [dict(camera=c, frame=f, source_rgb=self.rgb, grid='scale-opencv-integer', K=[])
                     for c in range(34) if c not in (0, 10, 20, 30) for f in range(50, 200)]
        self.context_path = self.local / 'jobs' / actual.CONTEXT_JOB / 'context.json'
        self.context = self.record(self.context_path, dict(schema='plan069-depth-context/v1',
            inputs=self.inputs, rows=self.rows))
        self.receipt_path = self.root / (actual.CONTEXT_JOB + '.json')
        self.charge_path = self.root / (actual.CONTEXT_JOB + '-charge.json')
        self.charge = self.record(self.charge_path, dict(schema='plan069-depth-context-charge/v1',
            status='prepared', context=self.context, inputs=self.inputs))
        self.ledger.history.append(dict(event='cpu_preparation_charge', evidence=self.charge,
                                        event_sha256='charge-event'))
        self.record(self.receipt_path, dict(schema='plan069-depth-context-preparation/v1',
            status='complete', context=self.context, inputs=self.inputs,
            charge_event_sha256='charge-event'))
        self.metadata = dict(native_processed_K=[[1, 0, 0], [0, 1, 0], [0, 0, 1]])
        historical_config = self.record(self.root / 'historical-config.json',
            dict(forbidden_vipe_roots=['/forbidden/vipe']))
        self.historical = self.record(self.root / 'historical.json', dict(status='complete',
            component='D2', component_sha256='frozen-component', configuration=historical_config,
            rows=[dict(identity=dict(camera=c, frame=175), depth=self.prediction,
                metadata=self.metadata) for c in (1, 11, 21, 31)]))
        self.runtime = dict(python=sys.executable)
        self.assets = self.record(self.root / 'assets.json', {})
        self.setup = self.record(self.root / 'E5-result.json', dict(status='complete',
            environment='E5', runtime=self.runtime))
        self.ledger.current.update({
            'E5-setup-recovery-004': dict(event='finish', status='complete', result=self.setup),
            'D2-check': dict(event='finish', status='complete', result=self.historical)})
        self.preflight = self.record(self.root / 'preflight.json', dict(schema=PREFLIGHT,
            candidate='D2', status='cpu_preflight_passed', proposal_sha256=object_hash(self.proposal),
            runtime=self.runtime, assets=self.assets, e5_result=self.setup))
        self.qualification_path = self.root / 'qualification.json'
        self.record(self.qualification_path, dict(schema='plan069-depth-D2-qualification/v1',
            candidate='D2', preflight=self.preflight, worker_runtime=self.runtime,
            assets_record=self.assets, commercial={}, assets=[], runtime={}))
        for name, value in (('shared_run_root', lambda: self.root), ('DO', self.do),
                            ('SOURCE', self.source), ('CONTEXT_RECEIPT', self.receipt_path),
                            ('Ledger', lambda path, config: self.ledger),
                            ('verify_runtime', lambda runtime: None),
                            ('_live', lambda ledger, local: dict(ledger_head_sha256='head')),
                            ('admit', lambda *args, **kwargs: []),
                            ('resources', lambda *args, **kwargs: dict(artifact_bytes=0))):
            patcher = patch.object(actual, name, value)
            patcher.start()
            self.addCleanup(patcher.stop)
        host = patch('vipe_benchmark.d2_actual.Path.read_text', autospec=True,
                     side_effect=self.read_text)
        host.start()
        self.addCleanup(host.stop)

    @staticmethod
    def read_text(path, *args, **kwargs):
        if path == Path('/proc/1/comm'):
            return 'systemd'
        with path.open('r', **kwargs) as stream:
            return stream.read()

    @staticmethod
    def record(path, document):
        write_json(path, document)
        return file_record(path)

    def result(self, request):
        return dict(schema=RESULT_SCHEMA, status='complete', record_kind='actual', candidate='D2',
            job_id=actual.JOB, context=self.context, historical_check=self.historical,
            preflight=self.preflight, proposal_sha256=request['proposal_sha256'],
            new_maps=196, reused_anchors=4, rows=[dict(camera=c, frame=f,
                source_rgb=self.rgb, inputs=self.inputs, grid='scale-opencv-integer',
                domain='camera_z_metres', settings='frozen-component', prediction=self.prediction,
                reused_anchor=f==175, metadata=self.metadata)
                for c in (1, 11, 21, 31) for f in range(150, 200)])

    def supervise(self, ledger, job, command, output, **kwargs):
        request = read_json(command[3])
        self.assertEqual(command[0], self.runtime['python'])
        self.assertEqual(kwargs['evidence']['executable'], file_record(command[0]))
        self.assertEqual(len(ledger.authorizations), 1)
        binding = ledger.authorizations[0][1]
        self.assertEqual(binding['command'], command)
        self.assertEqual(binding['request'], kwargs['evidence']['request'])
        record = self.record(output / 'result.json', self.result(request))
        kwargs['validate_result'](output)
        ledger.current[job] = dict(event='finish', job_id=job, status='complete',
            result=record, cleanup_confirmed=True, surviving_pids=[], cleanup_uncertain=False)
        ledger.history.append(dict(event='reserve', job_id=job, evidence=kwargs['evidence']))
        ledger.history.append(ledger.current[job])
        return dict(status='complete')

    def prepare_maps(self):
        with patch.object(actual, 'supervise', side_effect=self.supervise):
            self.assertEqual(actual.dispatch(self.context_path, self.qualification_path), dict(status='complete'))

    def test_dispatch_binds_exact_request_worker_and_interpreter(self):
        self.prepare_maps()
        request = read_json(self.local / 'requests' / (actual.JOB + '.json'))
        self.assertEqual(request['component'], 'D2')
        self.assertEqual(request['historical_check'], self.historical)
        self.assertEqual(request['runtime'], self.runtime)
        self.assertEqual(request['context'], self.context)

    def test_admission_refreshes_live_snapshot_after_closure_review(self):
        samples = [dict(ledger_head_sha256='initial'), dict(ledger_head_sha256='refreshed')]
        with patch.object(actual, '_live', side_effect=samples) as live, \
             patch.object(actual, 'supervise', side_effect=self.supervise):
            actual.dispatch(self.context_path, self.qualification_path)
        self.assertEqual(live.call_count, 2)
        admission = read_json(self.local / 'requests' / (actual.JOB + '-admission.json'))
        self.assertEqual(admission['live']['ledger_head_sha256'], 'refreshed')

    def test_context_charge_required_before_authorization(self):
        self.ledger.history.clear()
        with patch.object(actual, 'supervise') as supervise:
            with self.assertRaisesRegex(ValueError, 'ledger-charged'):
                actual.dispatch(self.context_path, self.qualification_path)
            supervise.assert_not_called()
        self.assertFalse(self.ledger.authorizations)

    def test_publication_requires_confirmed_cleanup(self):
        self.prepare_maps()
        self.ledger.current[actual.JOB]['cleanup_confirmed'] = False
        with patch.object(actual, 'publish_fixture_clips') as publish:
            with self.assertRaisesRegex(ValueError, 'confirmed cleanup'):
                actual.publish()
            publish.assert_not_called()
        self.assertFalse(self.ledger.charges)

    def test_publication_charges_cpu_and_binds_historical_result(self):
        self.prepare_maps()
        def publisher(context, candidate, domain, rows, anchors, output, provenance, **kwargs):
            self.assertEqual(context, self.context)
            self.assertEqual(candidate, 'D2')
            self.assertEqual(domain, 'camera_z_metres')
            self.assertEqual(len(rows), 200)
            self.assertEqual(len(anchors), 4)
            self.assertEqual(provenance['historical_result'], self.historical)
            self.assertEqual(kwargs['record_kind'], 'actual')
            self.record(output / 'result.json', dict(status='complete'))
            return dict(status='complete')
        with patch.object(actual, 'publish_fixture_clips', side_effect=publisher):
            self.assertEqual(actual.publish(), dict(status='complete'))
        self.assertEqual(len(self.ledger.charges), 1)
        self.assertTrue(self.ledger.charges[0][1]['path'].endswith('plan069-D2-clips-001/result.json'))

    def test_publication_rejects_duplicate_or_changed_reservation(self):
        self.prepare_maps()
        reservation = next(row for row in self.ledger.history if row['event']=='reserve')
        self.ledger.history.append(reservation)
        with patch.object(actual, 'publish_fixture_clips') as publish:
            with self.assertRaisesRegex(ValueError, 'unique exact map reservation'):
                actual.publish()
            publish.assert_not_called()
        self.assertFalse(self.ledger.charges)

    def test_dispatch_rejects_cleanup_uncertainty(self):
        with patch.object(actual, 'supervise', return_value=dict(status='complete')):
            with self.assertRaisesRegex(ValueError, 'cleanup not confirmed'):
                actual.dispatch(self.context_path, self.qualification_path)

    def test_publication_failure_is_charged_and_stops(self):
        self.prepare_maps()
        with patch.object(actual, 'publish_fixture_clips', side_effect=ValueError('encoder failure')):
            with self.assertRaisesRegex(ValueError, 'encoder failure'):
                actual.publish()
        self.assertEqual(len(self.ledger.charges), 1)
        self.assertTrue(self.ledger.charges[0][1]['path'].endswith('clips-001-failure.json'))

    def test_completed_map_rejects_changed_anchor(self):
        self.prepare_maps()
        request = read_json(self.local / 'requests' / (actual.JOB + '.json'))
        result = self.result(request)
        anchor = next(row for row in result['rows'] if row['reused_anchor'])
        anchor['metadata'] = dict(native_processed_K=[[9]])
        with self.assertRaisesRegex(ValueError, 'frozen anchor record'):
            actual.validate_result(result, request, read_json(self.historical['path']))


if __name__ == '__main__':
    unittest.main()

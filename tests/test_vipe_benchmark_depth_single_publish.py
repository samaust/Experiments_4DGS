"""Single-image clip publication requires a supervised complete map finish."""
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from vipe_benchmark.depth_single_publish import publish_after_gpu
from vipe_benchmark.files import file_record, write_json


class SinglePublishTests(unittest.TestCase):
    def test_unaccounted_actual_result_never_creates_clip_output(self):
        with tempfile.TemporaryDirectory() as directory:
            local = Path(directory)
            for candidate in ('D5', 'D6', 'D8', 'D11'):
                with self.subTest(candidate=candidate):
                    result = local / f'jobs/plan069-{candidate}-maps-001/result.json'
                    write_json(result, dict(schema=('plan069-D11-maps-result/v1' if candidate == 'D11' else
                                          'plan069-depth-single-maps-result/v1'),
                        status='complete', record_kind='actual', candidate=candidate))
                    output = local / f'jobs/plan069-{candidate}-clips-001'
                    with self.assertRaisesRegex(ValueError, 'supervised single-image GPU result'):
                        publish_after_gpu(file_record(result), output)
                    self.assertFalse(output.exists())

    def test_accounted_failed_fit_can_publish_qualitative_clips(self):
        from unittest.mock import MagicMock, patch
        import test_vipe_benchmark_depth_single_run as fixtures
        from vipe_benchmark.depth_extension import CONFIG
        from vipe_benchmark.depth_single_run import run_maps
        from vipe_benchmark.files import read_json
        fixture = fixtures.SingleMapsTests()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        local = fixture.root
        qualitative = local / 'qualitative-fixture.json'
        write_json(qualitative, dict(schema='plan069-depth-qualitative-admission/v1',
            record_kind='fixture', component='D5', inputs=fixture.inputs,
            purpose='qualitative-only', status='admitted'))
        request = dict(fixture.request, qualitative_admission=file_record(qualitative))
        with patch('vipe_benchmark.depth_single_run.materialize_role', fixture.materialize):
            result = run_maps(request, local / request['job_id'], backend=fixtures.Plane(fail_fit=True))
        actual_qualitative = local / 'qualitative-actual.json'
        write_json(actual_qualitative, dict(schema='plan069-depth-qualitative-admission/v1',
            record_kind='actual', component='D5', inputs=fixture.inputs,
            purpose='qualitative-only', status='admitted'))
        admission = local / 'admission.json'
        write_json(admission, dict(status='passed'))
        review = local / 'review.json'
        write_json(review, dict(proposals=[dict(candidate='D5',
            candidate_config=read_json(CONFIG)['candidates']['D5'],
            workload=dict(unique_published_maps=256, clips=4, clip_frames=50, clip_fps=25),
            allocation=dict(cpu_seconds=120, artifact_bytes=2**30))]))
        job = 'plan069-D5-maps-001'
        actual_request = dict(request, record_kind='actual', job_id=job,
            qualitative_admission=file_record(actual_qualitative),
            admission=file_record(admission), review=file_record(review))
        actual_result = dict(result, record_kind='actual', job_id=job,
                             admission=actual_request['admission'])
        result_path = local / 'jobs' / job / 'result.json'
        write_json(result_path, actual_result)
        write_json(result_path.parent / 'request.json', actual_request)
        original_request = local / 'requests' / (job + '.json')
        write_json(original_request, actual_request)
        state = dict(event='finish', status='complete', result=file_record(result_path),
                     cleanup_confirmed=True)
        ledger = MagicMock()
        ledger.states.return_value = {job: state}
        ledger.events.return_value = [dict(event='reserve', job_id=job,
            evidence=dict(request=file_record(original_request), admission=file_record(admission)))]
        ledger.totals.return_value = dict(cpu=dict(elapsed_seconds=0))
        def render(context, candidate, domain, rows, anchors, output, provenance, **options):
            self.assertEqual(candidate, 'D5')
            self.assertEqual(len(rows), 200)
            self.assertEqual(sum(r['reused_anchor'] for r in rows), 4)
            self.assertEqual(options['record_kind'], 'actual')
            output.mkdir(parents=True)
            write_json(output / 'package.json', dict(status='published'))
            receipt = dict(record_kind='actual', clips=4, new_map_identities=196,
                           package=file_record(output / 'package.json'))
            write_json(output / 'result.json', receipt)
            return receipt
        output = local / 'jobs/plan069-D5-clips-001'
        with patch('vipe_benchmark.depth_single_publish.Ledger', return_value=ledger), patch(
                'vipe_benchmark.depth_clips.publish_fixture_clips', render):
            receipt = publish_after_gpu(file_record(result_path), output)
        self.assertEqual(receipt['clips'], 4)
        self.assertEqual(ledger.charge_cpu_preparation.call_count, 1)
        publication = read_json(output / 'publication.json')
        self.assertEqual(publication['engineering_eligibility'], 'blocked')
        self.assertEqual(publication['scales'], result['scales'])

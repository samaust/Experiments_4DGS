"""Accounted D11 relative maps use the shared whole-clip publisher."""
from pathlib import Path
import unittest
from unittest.mock import MagicMock, patch

import numpy as np

import test_vipe_benchmark_depth_d11_run as fixtures
from vipe_benchmark.depth_d11_run import run_maps
from vipe_benchmark.depth_extension import CONFIG
from vipe_benchmark.depth_single_publish import publish_after_gpu
from vipe_benchmark.files import file_record, read_json, write_json
from vipe_benchmark.marigold_relative import PROFILE


class D11PublishTests(unittest.TestCase):
    def test_accounted_native_relative_maps_publish_without_metric_scale(self):
        fixture = fixtures.D11MapsTests()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        local = fixture.root
        request = fixture.request
        with patch('vipe_benchmark.depth_d11_run.materialize_role', fixture.fixture.materialize):
            result = run_maps(request, local / request['job_id'], backend=fixtures.RelativePlane())
        admission = local / 'admission.json'
        write_json(admission, dict(status='passed'))
        review = local / 'review.json'
        write_json(review, dict(proposals=[dict(candidate='D11',
            candidate_config=read_json(CONFIG)['candidates']['D11'],
            workload=dict(unique_published_maps=256, clips=4, clip_frames=50, clip_fps=25),
            allocation=dict(cpu_seconds=120, artifact_bytes=2**30))]))
        setup = local / 'setup.json'
        write_json(setup, dict(native_source=dict(test='synthetic'), source_manifest=dict(test='synthetic'),
            runtime=dict(native_qualification=dict(test='synthetic'))))
        native_map = local / 'native.npy'
        np.save(native_map, np.full((540, 960), -2.5, np.float32))
        native = local / 'native-result.json'
        write_json(native, dict(schema='plan069-D11-native-folder-result/v1', status='complete',
            profile=PROFILE, setup_source=dict(test='synthetic'), source_manifest=dict(test='synthetic'),
            native_qualification=dict(test='synthetic'), predictions=[dict(
                id=f"camera{r['camera']:02d}-frame{r['frame']:03d}", prediction=file_record(native_map))
                for r in sorted(result['rows'], key=lambda r: (r['camera'], r['frame']))]))
        job = 'plan069-D11-maps-001'
        actual_request = dict(request, record_kind='actual', job_id=job, setup=file_record(setup),
            admission=file_record(admission), review=file_record(review))
        actual_result = dict(result, record_kind='actual', job_id=job, setup=file_record(setup),
            admission=actual_request['admission'], native_result=file_record(native))
        result_path = local / 'jobs' / job / 'result.json'
        write_json(result_path, actual_result)
        write_json(result_path.parent / 'request.json', actual_request)
        original_request = local / 'requests' / (job + '.json')
        write_json(original_request, actual_request)
        state = dict(event='finish', status='complete', result=file_record(result_path), cleanup_confirmed=True)
        ledger = MagicMock()
        ledger.states.return_value = {job: state}
        ledger.events.return_value = [dict(event='reserve', job_id=job,
            evidence=dict(request=file_record(original_request), admission=file_record(admission)))]
        ledger.totals.return_value = dict(cpu=dict(elapsed_seconds=0))
        def render(context, candidate, domain, rows, anchors, output, provenance, **options):
            self.assertEqual((candidate, domain), ('D11', 'relative_log'))
            self.assertEqual((len(rows), sum(r['reused_anchor'] for r in rows)), (200, 4))
            self.assertEqual(options['record_kind'], 'actual')
            output.mkdir(parents=True)
            write_json(output / 'package.json', dict(status='published'))
            receipt = dict(record_kind='actual', clips=4, new_map_identities=196,
                           package=file_record(output / 'package.json'))
            write_json(output / 'result.json', receipt)
            return receipt
        output = local / 'jobs/plan069-D11-clips-001'
        with patch('vipe_benchmark.depth_single_publish.Ledger', return_value=ledger), patch(
                'vipe_benchmark.depth_clips.publish_fixture_clips', render):
            receipt = publish_after_gpu(file_record(result_path), output)
        self.assertEqual(receipt['clips'], 4)
        self.assertEqual(ledger.charge_cpu_preparation.call_count, 1)
        publication = read_json(output / 'publication.json')
        self.assertEqual(publication['domain'], 'relative_log')
        self.assertEqual(publication['engineering_eligibility'], 'not_applicable')
        self.assertIsNone(publication['scales'])

    def test_native_relative_npz_reaches_real_shared_clip_package(self):
        import test_vipe_benchmark_depth_context as contexts
        from vipe_benchmark.depth_clips import prepare_context, publish_fixture_clips
        fixture = contexts.DepthContextTests()
        fixture.setUp()
        self.addCleanup(fixture.tearDown)
        accepted = read_json(fixture.record['path'])
        for row in accepted['depth']:
            path = fixture.root / f"camera{row['identity']['camera']}-accepted-valid.npy"
            with np.load(row['samples']['path']) as samples:
                np.save(path, samples['valid'] > 0)
            row['valid'] = file_record(path)
        accepted_path = fixture.root / 'accepted-inputs.json'
        write_json(accepted_path, accepted)
        fixture.record = file_record(accepted_path)
        context = prepare_context(fixture.record, fixture.root / 'context', fixture.config)
        request = dict(schema='plan069-D11-maps-request/v1', record_kind='fixture', candidate='D11',
            job_id='plan069-D11-maps-fixture-001', inputs=fixture.record, context=context)
        result = run_maps(request, fixture.root / request['job_id'], backend=fixtures.RelativePlane())
        selected = [r for r in result['rows'] if r['camera'] in (1, 11, 21, 31) and r['frame'] >= 150]
        rows = [dict(r, settings=result['component_sha256'], reused_anchor=r['frame'] == 175) for r in selected]
        anchors = {r['camera']: r['prediction'] for r in selected if r['frame'] == 175}
        configuration = fixture.root / 'configuration.json'
        outcome = fixture.root / 'outcome.json'
        write_json(configuration, request)
        write_json(outcome, dict(record_kind='fixture', status='complete'))
        origin = dict(source_result=file_record(fixture.root / request['job_id'] / 'result.json'),
            configuration=file_record(configuration), ledger_outcome=file_record(outcome))
        receipt = publish_fixture_clips(context, 'D11', 'relative_log', rows, anchors,
            fixture.root / 'clips', origin, max_seconds=120)
        package = read_json(receipt['package']['path'])
        display = package['settings']['depth_display']
        self.assertEqual(display['domain'], 'relative_log')
        self.assertEqual(display['normalization_scope'], 'whole 50-frame clip')
        self.assertEqual(display['direction'], 'larger means farther')
        self.assertEqual((receipt['clips'], receipt['new_map_identities']), (4, 196))
        for candidate in package['candidates']:
            self.assertEqual(len(candidate['media']), 4)
            self.assertTrue(all(Path(row['record']['path']).stat().st_size > 0 for row in candidate['media']))
        with np.load(selected[0]['prediction']['path']) as data:
            self.assertEqual(set(data.files), {'relative', 'valid', 'raw_values'})

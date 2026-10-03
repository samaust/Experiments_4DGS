"""D7 publication accepts only an accounted native GPU result."""
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch, MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from vipe_benchmark.depth_d7_publish import publish_d7_after_gpu
from vipe_benchmark.files import file_record, write_json


class D7PublishTests(unittest.TestCase):
    def test_unaccounted_map_result_cannot_be_published(self):
        with tempfile.TemporaryDirectory() as directory:
            local = Path(directory)
            result = local / 'jobs/plan069-D7-maps-001/result.json'
            write_json(result, dict(schema='plan069-D7-maps-result/v1',
                                    status='complete', candidate='D7'))
            with self.assertRaisesRegex(ValueError, 'supervised D7 GPU result'):
                publish_d7_after_gpu(file_record(result),
                    local / 'jobs/plan069-D7-clips-001')
            self.assertFalse((local / 'jobs/plan069-D7-clips-001').exists())

    def test_completed_finish_uses_unique_reserved_admission_and_confirms_cleanup(self):
        with tempfile.TemporaryDirectory() as directory:
            local = Path(directory)
            job = 'plan069-D7-maps-001'
            maps = local / 'jobs' / job
            source = local / 'source.json'
            write_json(source, dict(fixture=True))
            record = file_record(source)
            fit = dict(role='fit', component='D7', status='passed', scale=3.)
            write_json(maps / 'scale-fit.json', fit)
            fit_record = file_record(maps / 'scale-fit.json')
            write_json(maps / 'scale-check.json', dict(role='selection', component='D7',
                status='passed', scale=3., frozen_fit=fit_record))
            keys = {(camera, frame) for camera in range(34) if camera not in (0, 10, 20, 30)
                    for frame in (100, 175)} | {(camera, frame) for camera in (1, 11, 21, 31)
                    for frame in range(150, 200)}
            rows = [dict(camera=camera, frame=frame,
                kind='anchor' if frame in (100, 175) else 'clip-extra',
                domain='camera_z_metres', grid='scale-opencv-integer',
                source_rgb=record, inputs=record, context=record, prediction=record)
                for camera, frame in sorted(keys)]
            write_json(maps / 'result.json', dict(schema='plan069-D7-maps-result/v1',
                status='complete', record_kind='actual', candidate='D7', job_id=job,
                rows=rows, inputs=record, context=record,
                scales=dict(fit=fit_record, check=file_record(maps / 'scale-check.json'))))
            result = file_record(maps / 'result.json')
            write_json(local / 'review.json', dict(proposals=[dict(candidate='D7',
                candidate_config={}, workload=dict(unique_published_maps=256, clips=4,
                    clip_frames=50, clip_fps=25), allocation=dict(cpu_seconds=100,
                    artifact_bytes=10**7))]))
            request = dict(admission=record, context=record, inputs=record,
                           review=file_record(local / 'review.json'))
            write_json(maps / 'request.json', request)
            write_json(local / 'requests' / (job + '.json'), request)
            finish = dict(event='finish', status='complete', result=result,
                          cleanup_confirmed=False)
            reservation = dict(event='reserve', job_id=job, evidence=dict(
                request=file_record(local / 'requests' / (job + '.json')), admission=record))
            ledger = MagicMock()
            ledger.states.return_value = {job: finish}
            ledger.events.return_value = [reservation, finish]
            ledger.totals.return_value = dict(cpu=dict(elapsed_seconds=0))
            output = local / 'jobs/plan069-D7-clips-001'
            def publish(*args, **kwargs):
                output.mkdir(parents=True)
                receipt = dict(clips=4, new_map_identities=196, record_kind='actual')
                write_json(output / 'result.json', receipt)
                return receipt
            with patch('vipe_benchmark.depth_d7_publish.Ledger', return_value=ledger), \
                 patch('vipe_benchmark.depth_d7_publish.publish_fixture_clips', side_effect=publish):
                with self.assertRaisesRegex(ValueError, 'supervised D7 GPU result'):
                    publish_d7_after_gpu(result, output)
                self.assertFalse(output.exists())
                finish['cleanup_confirmed'] = True
                receipt = publish_d7_after_gpu(result, output)
                self.assertEqual(receipt['clips'], 4)
                ledger.charge_cpu_preparation.assert_called_once()


if __name__ == '__main__':
    unittest.main()

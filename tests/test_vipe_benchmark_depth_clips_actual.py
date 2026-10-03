"""Actual clip lineage must resolve to a finished admitted map result."""

from pathlib import Path
import sys
import tempfile
import unittest

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from vipe_benchmark.config import load, training_cameras
from vipe_benchmark.depth_clips import validate_actual_depth_package, _validate_source_lineage
from vipe_benchmark.files import file_record, read_json, write_json
from vipe_benchmark.ledger import Ledger


class ActualDepthClipLineageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        local = self.root / 'jobs' / 'plan069-D9-maps-001'
        local.mkdir(parents=True)
        payload = self.root / 'payload.bin'
        payload.write_bytes(b'fixture evidence')
        record = file_record(payload)
        cameras = training_cameras(load())
        valid_path = self.root / 'valid.npy'
        np.save(valid_path, np.ones((2, 2), bool))
        samples_path = self.root / 'samples.npz'
        np.savez(samples_path, K=np.eye(3), valid=np.ones((2, 2), bool))
        valid, samples = file_record(valid_path), file_record(samples_path)
        rgb = [dict(identity=dict(branch='calibration', camera=camera, frame=frame),
                    rgb=record, source_video=record)
               for camera in cameras for frame in range(50, 200)]
        depth = [dict(identity=dict(branch='depth', camera=camera, frame=frame),
                      rgb=record, K=np.eye(3).tolist(), samples=samples)
                 for camera in cameras for frame in (100, 175)]
        inputs_path = self.root / 'inputs.json'
        write_json(inputs_path, dict(rgb=rgb, depth=depth))
        proofs = [dict(camera=camera, frame=frame, accepted_rgb=record,
                       source_rgb=record, samples=samples)
                  for camera in cameras for frame in (100, 175)]
        self.context_rows = [dict(camera=camera, frame=frame,
            source_rgb=record, decoded_source_rgb=record, source_video=record,
            source_rgb_grid='scale-opencv-integer' if frame in (100, 175)
                            else 'distorted-opencv-integer',
            accepted_anchor=frame in (100, 175), K=np.eye(3).tolist(), valid=valid)
                             for camera in cameras for frame in range(50, 200)]
        context_path = self.root / 'context.json'
        write_json(context_path, dict(schema='plan069-depth-context/v1',
            rows=self.context_rows, anchors=proofs, inputs=file_record(inputs_path)))
        self.context = file_record(context_path)
        self.result_rows = [dict(camera=camera, frame=frame,
                                 source_rgb=record, depth=record)
                            for camera in (1, 11, 21, 31)
                            for frame in range(150, 200)]
        result_path = local / 'result.json'
        write_json(result_path, dict(status='complete', record_kind='actual',
                                     schema='plan069-video-depth-result/v1', component='D9',
                                     context=self.context, rows=self.result_rows))
        self.result = file_record(result_path)
        admission_path = self.root / 'admission.json'
        write_json(admission_path, dict(schema='plan069-depth-admission-result/v1',
                                        status='passed', candidate='D9'))
        self.admission = file_record(admission_path)
        effective = dict(load(), new_download_gib_limit=110,
                         new_artifact_disk_gib_limit=210)
        ledger = Ledger(self.root / 'ledger.jsonl', effective)
        with ledger.locked() as (stream, events):
            ledger._append(stream, events, dict(event='reserve',
                job_id='plan069-D9-maps-001', resource='gpu', seconds=12000))
            finish = ledger._append(stream, events, dict(event='finish',
                job_id='plan069-D9-maps-001', resource='gpu', status='complete',
                elapsed_seconds=1., result=self.result))
        finish_path = self.root / 'finish.json'
        write_json(finish_path, finish)
        self.finish = file_record(finish_path)
        provenance = dict(source_result=self.result, ledger_outcome=self.finish,
                          admission=self.admission, configuration=record)
        source_media = []
        depth_media = []
        for camera in (1, 11, 21, 31):
            source_media.append(dict(camera_id=str(camera),
                source_images=[record] * 50))
            depth_media.append(dict(camera_id=str(camera),
                source_maps=[record] * 50))
        self.manifest = dict(id='D9-matched-clips-actual',
            bindings=dict(depth_context=self.context, depth_result=self.result,
                depth_admission=self.admission, depth_finish=self.finish,
                config=record),
            selections=[dict(camera_id=str(camera), frame_ids=list(range(150, 200)))
                        for camera in (1, 11, 21, 31)],
            candidates=[dict(id='source-rgb', provenance=provenance,
                             media=source_media),
                        dict(id='D9', provenance=provenance, media=depth_media)])

    def tearDown(self):
        self.temp.cleanup()

    def test_finished_map_rows_bind_all_four_actual_clips(self):
        validate_actual_depth_package(self.manifest)
        changed = dict(self.manifest)
        candidates = [dict(row, media=[dict(media) for media in row['media']])
                      for row in self.manifest['candidates']]
        candidates[1]['media'][0]['source_maps'] = [self.context] * 50
        changed['candidates'] = candidates
        with self.assertRaisesRegex(ValueError, 'map lineage'):
            validate_actual_depth_package(changed)

    def test_video_result_must_bind_the_packaged_context(self):
        from vipe_benchmark.files import read_json
        result = read_json(self.result['path'])
        result['context'] = self.admission
        Path(self.result['path']).unlink()
        write_json(self.result['path'], result)
        replacement = file_record(self.result['path'])
        changed = dict(self.manifest, bindings=dict(self.manifest['bindings'],
                                                   depth_result=replacement))
        with self.assertRaisesRegex(ValueError, 'context binding'):
            validate_actual_depth_package(changed)

    def test_unfinished_ledger_record_is_rejected(self):
        missing = dict(self.manifest)
        missing['bindings'] = dict(missing['bindings'], depth_finish=self.admission)
        with self.assertRaisesRegex(ValueError, 'finish absent'):
            validate_actual_depth_package(missing)

    def test_anchor_replacement_and_second_remap_are_rejected(self):
        context = read_json(self.context['path'])
        anchor = next(row for row in context['rows'] if row['frame'] == 175)
        anchor['source_rgb'] = self.admission
        with self.assertRaisesRegex(ValueError, 'accepted anchor binding'):
            _validate_source_lineage(context)
        context = read_json(self.context['path'])
        anchor = next(row for row in context['rows'] if row['frame'] == 175)
        anchor['source_rgb_grid'] = 'distorted-opencv-integer'
        with self.assertRaisesRegex(ValueError, 'decoded source lineage'):
            _validate_source_lineage(context)


if __name__ == '__main__':
    unittest.main()

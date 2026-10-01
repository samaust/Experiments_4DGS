"""The added temporal context must preserve the frozen scale-grid anchors."""
from pathlib import Path
import sys
import tempfile
import unittest

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from basketball_scale import undistortion
from vipe_benchmark.config import ROOT, load, training_cameras
from vipe_benchmark.files import file_record, read_json, write_json
from vipe_benchmark.depth_clips import prepare_context, publish_fixture_clips


class DepthContextTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.config = load()
        calibration = ROOT / 'docs/experiments/basketball-calibration-alternatives/calibration.json'
        cameras = {entry['camera_id']: entry for entry in read_json(calibration)['cameras']}
        image = np.full((540, 960, 3), [27, 100, 170], np.uint8)
        cv2.imwrite(str(self.root / 'distorted.png'), image)
        distorted = file_record(self.root / 'distorted.png')
        (self.root / 'source.mp4').write_bytes(b'fixture-video-identity')
        video = file_record(self.root / 'source.mp4')
        rgb, depth = [], []
        for camera in training_cameras(self.config):
            K, maps = undistortion(cameras[camera])
            remapped = cv2.remap(image, *maps, cv2.INTER_LINEAR,
                                 borderMode=cv2.BORDER_CONSTANT)
            anchor = self.root / f'camera{camera}-anchor.png'
            cv2.imwrite(str(anchor), remapped)
            for frame in range(50, 200):
                rgb.append(dict(identity=dict(branch='calibration', camera=camera, frame=frame),
                    rgb=distorted, source_video=video, role='fit' if frame <= 149 else 'selection',
                    grid='distorted-opencv-integer'))
            for frame in (100, 175):
                depth.append(dict(identity=dict(branch='depth', camera=camera, frame=frame),
                    rgb=file_record(anchor), K=K.tolist(), grid='scale-opencv-integer'))
        self.rows = rgb
        self.inputs = dict(schema='vipe-benchmark-inputs/v1', status='prepared',
            rgb=rgb, depth=depth, source_files=[file_record(calibration), video])
        write_json(self.root / 'inputs.json', self.inputs)
        self.record = file_record(self.root / 'inputs.json')

    def tearDown(self):
        self.temporary.cleanup()

    def test_context_matches_both_anchors_and_retains_all_frames(self):
        record = prepare_context(self.record, self.root / 'context', self.config)
        context = read_json(record['path'])
        self.assertEqual(context['schema'], 'plan069-depth-context/v1')
        self.assertEqual(context['inputs'], self.record)
        self.assertEqual(len(context['rows']), 30 * 150)
        self.assertEqual(len(context['anchors']), 60)
        self.assertEqual(context['roles']['fit'], [50, 149])
        self.assertEqual(context['roles']['check'], [150, 199])
        self.assertEqual({row['camera'] for row in context['rows']},
                         set(training_cameras(self.config)))
        self.assertEqual(context['anchors'][0]['remapped_sha256'],
                         context['anchors'][0]['accepted_rgb']['sha256'])

    def test_missing_context_and_changed_anchor_are_rejected(self):
        missing = dict(self.inputs, rgb=self.rows[:-1])
        write_json(self.root / 'missing.json', missing)
        with self.assertRaisesRegex(ValueError, 'context membership'):
            prepare_context(file_record(self.root / 'missing.json'), self.root / 'missing', self.config)
        final_window = dict(self.inputs, rgb=self.rows + [dict(self.rows[0],
            identity=dict(branch='calibration', camera=1, frame=200))])
        write_json(self.root / 'final-window.json', final_window)
        with self.assertRaisesRegex(ValueError, 'final-window'):
            prepare_context(file_record(self.root / 'final-window.json'),
                self.root / 'final-window', self.config)
        changed_depth = list(self.inputs['depth'])
        cv2.imwrite(str(self.root / 'wrong-anchor.png'), np.zeros((540, 960, 3), np.uint8))
        changed_depth[0] = dict(changed_depth[0], rgb=file_record(self.root / 'wrong-anchor.png'))
        write_json(self.root / 'changed.json', dict(self.inputs, depth=changed_depth))
        with self.assertRaisesRegex(ValueError, 'anchor bytes'):
            prepare_context(file_record(self.root / 'changed.json'), self.root / 'changed', self.config)

    def test_four_matched_clips_reuse_check_anchors_and_freeze_display(self):
        context = prepare_context(self.record, self.root / 'context', self.config)
        source_rows = {(r['camera'], r['frame']): r for r in read_json(context['path'])['rows']}
        depth = np.full((540, 960), 6., np.float32)
        valid = np.ones(depth.shape, bool)
        with (self.root / 'map.npz').open('xb') as stream:
            np.savez_compressed(stream, depth=depth, valid=valid, raw_values=depth)
        map_record = file_record(self.root / 'map.npz')
        rows = [dict(camera=camera, frame=frame, source_rgb=source_rows[camera, frame]['source_rgb'],
                     inputs=self.record, grid='scale-opencv-integer', domain='camera_z_metres',
                     prediction=map_record, settings='fixture-constant-z',
                     reused_anchor=(frame == 175))
                for camera in (1, 11, 21, 31) for frame in range(150, 200)]
        for name in ('source-result', 'ledger-outcome', 'configuration'):
            write_json(self.root / f'{name}.json', dict(id=name))
        origin = dict(source_result=file_record(self.root / 'source-result.json'),
            ledger_outcome=file_record(self.root / 'ledger-outcome.json'),
            configuration=file_record(self.root / 'configuration.json'))
        anchors = {camera: map_record for camera in (1, 11, 21, 31)}
        receipt = publish_fixture_clips(context, 'D5', 'camera_z_metres', rows, anchors,
            self.root / 'clips', origin, max_seconds=120)
        package = read_json(receipt['package']['path'])
        self.assertEqual(len(package['selections']), 4)
        self.assertEqual([len(s['frame_ids']) for s in package['selections']], [50] * 4)
        self.assertEqual([len(c['media']) for c in package['candidates']], [4, 4])
        self.assertEqual(package['settings']['depth_display']['range_metres'], [0, 20])
        self.assertEqual(len(package['settings']['detail_regions']), 3)
        self.assertEqual(receipt['new_map_identities'], 196)
        changed = list(rows)
        changed[25] = dict(changed[25], prediction=self.rows[0]['rgb'])
        with self.assertRaisesRegex(ValueError, 'anchor reuse'):
            publish_fixture_clips(context, 'D5', 'camera_z_metres', changed, anchors,
                self.root / 'bad-clips', origin, max_seconds=120)
        with self.assertRaisesRegex(ValueError, 'historical D2'):
            publish_fixture_clips(context, 'D2', 'camera_z_metres', rows, anchors,
                self.root / 'unbound-d2', origin, max_seconds=120)
        historical_rows = [dict(identity=dict(camera=camera, frame=175),
            depth=map_record, grid='scale-opencv-integer',
            source_rgb_sha256=source_rows[camera, 175]['source_rgb']['sha256'],
            K=source_rows[camera, 175]['K']) for camera in anchors]
        write_json(self.root / 'd2-history.json', dict(component='D2', status='complete',
            component_sha256='fixture-constant-z', configuration=origin['configuration'],
            rows=historical_rows))
        d2_origin = dict(origin, source_result=file_record(self.root / 'd2-history.json'))
        d2 = publish_fixture_clips(context, 'D2', 'camera_z_metres', rows, anchors,
            self.root / 'd2-clips', d2_origin, max_seconds=120)
        self.assertEqual(d2['new_map_identities'], 196)
        self.assertEqual(len(read_json(d2['package']['path'])['candidates'][1]['media']), 4)
        relative_records = []
        for index, value in enumerate((.2, .8)):
            array = np.full((540, 960), value, np.float32)
            with (self.root / f'relative-{index}.npz').open('xb') as stream:
                np.savez_compressed(stream, relative=array, valid=valid, raw_values=array)
            relative_records.append(file_record(self.root / f'relative-{index}.npz'))
        relative_rows = [dict(row, domain='relative_inverse',
                              prediction=relative_records[row['frame'] % 2],
                              settings='fixture-relative') for row in rows]
        relative_anchors = {camera: relative_records[1] for camera in anchors}
        relative_receipt = publish_fixture_clips(context, 'D9', 'relative_inverse',
            relative_rows, relative_anchors, self.root / 'relative-clips', origin,
            max_seconds=120)
        relative_package = read_json(relative_receipt['package']['path'])
        display = relative_package['settings']['depth_display']
        self.assertEqual(display['domain'], 'relative_inverse')
        self.assertEqual(display['units'], 'relative arbitrary values')
        self.assertEqual(display['direction'], 'larger means nearer')
        self.assertEqual(len({tuple(part['raw_range']) for part in display['per_clip'].values()}), 1)
        for part in display['per_clip'].values():
            self.assertAlmostEqual(part['raw_range'][0], .2)
            self.assertAlmostEqual(part['raw_range'][1], .8)


if __name__ == '__main__':
    unittest.main()

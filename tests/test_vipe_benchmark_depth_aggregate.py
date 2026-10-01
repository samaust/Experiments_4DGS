"""Synthetic CPU contracts only; these are not execution or authorization evidence."""

from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))

from vipe_benchmark.depth_aggregate import CANDIDATES, assemble, validate_actual_package
from vipe_benchmark.files import file_record, write_json


class AggregateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.rgb = self.root / 'rgb.png'
        self.rgb.write_bytes(b'synthetic image fixture; not valid media')
        self.image = file_record(self.rgb)
        self.cameras = [camera for camera in range(1, 34) if camera not in (10, 20, 30)]
        self.assertEqual(len(self.cameras), 30)
        self.config = self.record('config', {'training': 'synthetic CPU fixture'})
        self.inputs = self.record('inputs', {'source': 'synthetic CPU fixture'})
        self.amendment = self.record('amendment', {'scope': 'synthetic CPU fixture'})
        self.source = self.record('source', {'source': 'synthetic CPU fixture'})
        anchors = [dict(camera=camera, frame=frame, accepted_rgb=self.image)
                   for camera in self.cameras for frame in (100, 175)]
        self.context = self.record('context', dict(schema='plan069-depth-context/v1',
            inputs=self.inputs, anchors=anchors))
        provenance = dict(source_result=self.inputs, ledger_outcome=self.amendment,
                          configuration=self.config)
        self.request = dict(schema='plan069-depth-aggregate-request/v1',
            record_kind='actual', id='synthetic-contract-fixture',
            bindings=dict(config=self.config, inputs=self.inputs,
                          amendment=self.amendment, context=self.context,
                          source=self.source), source_provenance=provenance,
            candidates={candidate: dict(status='missing', reason='Synthetic pending slot',
                                        evidence={}) for candidate in CANDIDATES})
        self.camera_patch = mock.patch('vipe_benchmark.depth_aggregate.training_cameras',
                                       return_value=self.cameras)
        self.camera_patch.start()

    def tearDown(self):
        self.camera_patch.stop()
        self.temp.cleanup()

    def record(self, name, value):
        path = self.root / f'{name}.json'
        write_json(path, value)
        return file_record(path)

    def test_pending_slots_remain_visible_and_block_actual_publication(self):
        manifest = assemble(self.request)
        self.assertEqual(len(manifest['selections']), 64)
        self.assertEqual([candidate['id'] for candidate in manifest['candidates']],
                         ['source-rgb', *CANDIDATES])
        self.assertEqual(len(manifest['candidates'][0]['media']), 60)
        self.assertTrue(all(candidate['status'] == 'missing'
                            for candidate in manifest['candidates'][1:]))
        request_record = self.record('request', self.request)
        manifest['bindings']['depth_aggregate_request'] = request_record
        with self.assertRaisesRegex(ValueError, 'pending depth slots'):
            validate_actual_package(manifest)

    def test_sixty_exact_anchor_identities_and_domain_are_required(self):
        evidence = {name: self.record(f'evidence-{name}', {'synthetic': True})
                    for name in ('generation', 'runtime', 'assets', 'commercial',
                                 'ledger', 'resources')}
        rows = [dict(camera=camera, frame=frame, grid='scale-opencv-integer',
                     domain='camera_z_metres', source_rgb=self.image, record=self.image)
                for camera in self.cameras for frame in (100, 175)]
        provenance = dict(source_result=self.inputs, ledger_outcome=self.amendment,
                          configuration=self.config)
        self.request['candidates']['D0'] = dict(status='available', reason='',
            evidence=evidence, provenance=provenance, anchors=rows)
        self.assertEqual(len(assemble(self.request)['candidates'][1]['media']), 60)
        self.request['candidates']['D0']['anchors'] = rows[:-1]
        with self.assertRaisesRegex(ValueError, '60 anchors'):
            assemble(self.request)
        self.request['candidates']['D0']['anchors'] = rows
        rows[0] = dict(rows[0], domain='relative_inverse')
        with self.assertRaisesRegex(ValueError, 'grid/domain'):
            assemble(self.request)

    def test_terminal_state_requires_candidate_bound_authorization(self):
        self.request['candidates']['D5'] = dict(status='blocked',
            reason='Synthetic unavailable state', evidence={},
            terminal_authorization=self.record('wrong-terminal',
                dict(candidate='D6', status='blocked', authorized=True)))
        with self.assertRaisesRegex(ValueError, 'authorized terminal'):
            assemble(self.request)

    def test_complete_clip_arm_requires_four_matching_clips_and_anchor_reuse(self):
        evidence = {name: self.record(f'd2-{name}', {'synthetic': True})
                    for name in ('generation', 'runtime', 'assets', 'commercial',
                                 'ledger', 'resources')}
        anchors = [dict(camera=camera, frame=frame, grid='scale-opencv-integer',
                        domain='camera_z_metres', source_rgb=self.image,
                        record=self.image, prediction=self.image)
                   for camera in self.cameras for frame in (100, 175)]
        selections, source_media, depth_media, normal = [], [], [], {}
        for camera in (1, 11, 21, 31):
            frames = list(range(150, 200))
            selection = dict(id=f'camera{camera}-selection-150-199', kind='clip',
                role='selection', camera_id=str(camera), frame_ids=frames,
                timestamps=[frame / 25 for frame in frames])
            selections.append(selection)
            media = dict(selection_id=selection['id'], kind='clip',
                camera_id=str(camera), frame_ids=frames,
                timestamps=selection['timestamps'], resolution=[960, 540],
                record=self.image)
            source_media.append(dict(media, source_images=[self.image] * 50))
            depth_media.append(dict(media, source_maps=[self.image] * 50))
            normal[selection['id']] = dict(raw_range=[0, 20])
        package = self.record('d2-package', dict(schema='plan067-qualitative-package/v1',
            record_kind='actual', settings=dict(fps=25, resolution=[960, 540],
                depth_display=dict(domain='camera_z_metres', range_metres=[0, 20],
                    invalid_color='magenta', above_20_metres_color='red', per_clip=normal)),
            selections=selections, candidates=[
                dict(id='source-rgb', status='available', media=source_media),
                dict(id='D2', status='available', media=depth_media)]))
        receipt = self.record('d2-clips', dict(schema='plan069-depth-clips-result/v1',
            status='complete', record_kind='actual', candidate='D2', context=self.context,
            package=package, clips=4, new_map_identities=196))
        provenance = dict(source_result=self.inputs, ledger_outcome=self.amendment,
                          configuration=self.config)
        self.request['candidates']['D2'] = dict(status='available', reason='',
            evidence=evidence, provenance=provenance, anchors=anchors, clips=receipt)
        manifest = assemble(self.request)
        self.assertEqual(len(manifest['candidates'][0]['media']), 64)
        self.assertEqual(len(manifest['candidates'][3]['media']), 64)
        self.assertEqual(manifest['candidates'][3]['depth_display']['range_metres'], [0, 20])
        bad = list(anchors)
        bad[1] = dict(bad[1], prediction=self.config)
        self.request['candidates']['D2']['anchors'] = bad
        with self.assertRaisesRegex(ValueError, 'frame-175 map'):
            assemble(self.request)


if __name__ == '__main__':
    unittest.main()

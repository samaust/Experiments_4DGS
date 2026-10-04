"""Synthetic CPU contracts only; these are not execution or authorization evidence."""

from pathlib import Path
from copy import deepcopy
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))

from vipe_benchmark.depth_aggregate import CANDIDATES, assemble, validate_actual_package
from vipe_benchmark.files import file_record, read_json, write_json


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
        # Synthetic records exercise aggregate contracts only. Actual publication
        # independently requires the shared publisher's admission/live-ledger gate.
        self.publisher_patch = mock.patch('vipe_benchmark.depth_aggregate._verify_published_clips')
        self.publisher_patch.start()
        self.historical_patch = mock.patch('vipe_benchmark.depth_aggregate._verify_historical_anchors')
        self.historical_patch.start()
        self.charge_patch = mock.patch('vipe_benchmark.depth_aggregate._verify_preview_charge')
        self.charge_patch.start()

    def tearDown(self):
        self.camera_patch.stop()
        self.publisher_patch.stop()
        self.historical_patch.stop()
        self.charge_patch.stop()
        self.temp.cleanup()

    def record(self, name, value):
        path = self.root / f'{name}.json'
        write_json(path, value)
        return file_record(path)

    def previews(self, candidate):
        slot = self.request['candidates'][candidate]
        receipt = self.record(candidate + '-previews', dict(
            schema='plan069-depth-anchor-preview-result/v1', record_kind='actual', status='complete',
            candidate=candidate, preview_revision='002',
            context=self.context, inputs=self.inputs, config=self.config,
            anchors=slot['anchors'], rendered_frames=60, slot=deepcopy(slot), sources=dict(
                builder=file_record(Path(__file__).resolve().parents[1] / 'scripts/vipe_benchmark/depth_anchor_previews.py'),
                renderer=file_record(Path(__file__).resolve().parents[1] / 'scripts/vipe_benchmark/depth_extension.py'))))
        accounting = self.record(candidate + '-preview-accounting', dict(
            schema='plan069-depth-anchor-preview-accounting/v1', status='complete',
            candidate=candidate, result=receipt))
        slot['anchor_previews'] = receipt
        slot['evidence']['anchor_preview_accounting'] = accounting

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
        self.previews('D0')
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
        self.request['candidates']['D5']['terminal_authorization'] = self.record('right-terminal',
            dict(candidate='D5', status='blocked', authorized=True))
        candidate = next(row for row in assemble(self.request)['candidates'] if row['id'] == 'D5')
        self.assertEqual(candidate['engineering_eligibility'], 'unverified')
        self.assertEqual(candidate['media'], [])

    def clip_arm(self, candidate='D2', scale_status='passed'):
        domain = {'D9': 'relative_inverse', 'D11': 'relative_log'}.get(candidate, 'camera_z_metres')
        evidence = {name: self.record(f'd2-{name}', {'synthetic': True})
                    for name in ('generation', 'runtime', 'assets', 'commercial',
                                 'ledger', 'resources')}
        anchors = [dict(camera=camera, frame=frame, grid='scale-opencv-integer',
                        domain=domain, source_rgb=self.image,
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
        native_rows = [dict(camera=camera, frame=frame, domain=domain,
                            prediction=self.image, source_rgb=self.image,
                            reused_anchor=frame == 175)
                       for camera in (1, 11, 21, 31) for frame in range(150, 200)]
        if candidate != 'D2':
            keys = {(row['camera'], row['frame']) for row in native_rows}
            native_rows += [dict(camera=camera, frame=frame, domain=domain,
                                prediction=self.image, source_rgb=self.image)
                           for camera in self.cameras for frame in (100, 175)
                           if (camera, frame) not in keys]
        result = dict(schema={'D2': 'plan069-d2-maps-result/v1',
                              'D7': 'plan069-D7-maps-result/v1',
                              'D11': 'plan069-D11-maps-result/v1',
                              'D9': 'plan069-video-depth-result/v1',
                              'D10': 'plan069-video-depth-result/v1'}.get(
                                  candidate, 'plan069-depth-single-maps-result/v1'),
                      record_kind='actual', status='complete', candidate=candidate,
                      context=self.context, inputs=self.inputs, rows=native_rows)
        if candidate == 'D2':
            for role, frame in (('fit', 100), ('check', 175)):
                evidence['historical_' + role] = self.record('historical-' + role, dict(
                    component='D2', status='complete',
                    configuration=self.record('historical-config-' + role, dict(role=role)),
                    rows=[dict(identity=dict(camera=camera, frame=frame), depth=self.image,
                               grid='scale-opencv-integer', source_rgb_sha256=self.image['sha256'])
                          for camera in self.cameras]))
            result.update(historical_check=evidence['historical_check'], new_maps=196, reused_anchors=4)
        elif candidate not in ('D9', 'D11'):
            fit = self.record('scale-fit', dict(component=candidate, role='fit', status=scale_status))
            check = self.record('scale-check', dict(component=candidate, role='selection',
                status=scale_status, frozen_fit=fit))
            result.update(scales=dict(fit=fit, check=check), engineering_eligibility=scale_status)
            if candidate == 'D10':
                result['eligibility'] = dict(metric_scale=scale_status)
            evidence['scale'] = check
        if candidate in ('D9', 'D10'):
            result['component'] = result.pop('candidate')
            result['original_inputs'] = result.pop('inputs')
            if candidate == 'D10':
                result['scale'] = result.pop('scales')
            for row in result['rows']:
                row['depth'] = row.pop('prediction')
        source_result = self.record('native-result', result)
        evidence['generation'] = source_result
        provenance = dict(source_result=source_result, ledger_outcome=evidence['ledger'],
                          configuration=self.config)
        display = dict(domain=domain, range_metres=[0, 20], invalid_color='magenta',
                       above_20_metres_color='red', per_clip=normal)
        if candidate in ('D9', 'D11'):
            display = dict(domain=domain, normalization_scope='whole 50-frame clip',
                           units='relative arbitrary values', per_clip=normal)
        package = self.record('d2-package', dict(schema='plan067-qualitative-package/v1',
            bindings=dict(depth_context=self.context, depth_result=source_result,
                          depth_finish=evidence['ledger']),
            record_kind='actual', settings=dict(fps=25, resolution=[960, 540],
                depth_display=display),
            selections=selections, candidates=[
                dict(id='source-rgb', status='available', media=source_media),
                dict(id=candidate, status='available', media=depth_media)]))
        receipt = self.record('d2-clips', dict(schema='plan069-depth-clips-result/v1',
            status='complete', record_kind='actual', candidate=candidate, context=self.context,
            package=package, clips=4, new_map_identities=196))
        self.request['candidates'][candidate] = dict(status='available', reason='',
            evidence=evidence, provenance=provenance, anchors=anchors, clips=receipt)
        self.previews(candidate)
        return anchors

    def test_complete_clip_arm_requires_four_matching_clips_and_anchor_reuse(self):
        anchors = self.clip_arm()
        manifest = assemble(self.request)
        self.assertEqual(len(manifest['candidates'][0]['media']), 64)
        self.assertEqual(len(manifest['candidates'][3]['media']), 64)
        self.assertEqual(manifest['candidates'][3]['depth_display']['range_metres'], [0, 20])
        bad = list(anchors)
        bad[1] = dict(bad[1], prediction=self.config)
        self.request['candidates']['D2']['anchors'] = bad
        with self.assertRaisesRegex(ValueError, 'anchor differs'):
            assemble(self.request)

    def test_actual_single_and_video_result_contracts(self):
        # Each subtest gets fresh immutable synthetic receipt filenames.
        for candidate in ('D5', 'D6', 'D7', 'D8', 'D9', 'D10', 'D11'):
            with self.subTest(candidate=candidate):
                with tempfile.TemporaryDirectory() as temp:
                    previous = self.root
                    self.root = Path(temp)
                    try:
                        self.clip_arm(candidate)
                        item = next(row for row in assemble(self.request)['candidates'] if row['id'] == candidate)
                        self.assertEqual(len(item['media']), 64)
                        self.assertEqual(item['engineering_eligibility'],
                                         'ineligible' if candidate in ('D9', 'D11') else 'passed')
                        self.assertEqual(item['physical_accuracy'], 'unverified')
                    finally:
                        self.root = previous
                        self.request['candidates'][candidate] = dict(status='missing', reason='pending', evidence={})

    def test_shared_source_clips_use_input_lineage_not_encoded_movie_bytes(self):
        self.clip_arm('D2')
        original_root = self.root
        self.root = original_root / 'second-arm'
        self.root.mkdir()
        self.clip_arm('D5')
        self.root = original_root
        from vipe_benchmark.files import read_json
        slot = self.request['candidates']['D5']
        receipt = read_json(slot['clips']['path'])
        package = read_json(receipt['package']['path'])
        copied = self.root / 'different-encoded-source.mp4'
        copied.write_bytes(b'different lossy encoding, identical accepted source inputs')
        for item in package['candidates'][0]['media']:
            item['record'] = file_record(copied)
        receipt['package'] = self.record('alternate-source-package', package)
        slot['clips'] = self.record('alternate-source-receipt', receipt)
        # Rebuild this fixture's immutable preview linkage after changing its clips.
        slot.pop('anchor_previews')
        slot['evidence'].pop('anchor_preview_accounting')
        self.previews('D5')
        manifest = assemble(self.request)
        source = manifest['candidates'][0]
        self.assertEqual(source['media'][-4:][0]['record'], self.image)
        self.assertEqual(manifest['candidates'][6]['source_clip_receipt'], slot['clips'])
        package['candidates'][0]['media'][0]['source_images'][0] = self.config
        receipt['package'] = self.record('wrong-source-package', package)
        slot['clips'] = self.record('wrong-source-receipt', receipt)
        self.root = original_root / 'wrong-preview'
        self.root.mkdir()
        slot.pop('anchor_previews')
        slot['evidence'].pop('anchor_preview_accounting')
        self.previews('D5')
        with self.assertRaisesRegex(ValueError, 'source RGB input lineage differs'):
            assemble(self.request)

    def test_failed_fit_can_be_visible_without_manufacturing_a_pass(self):
        self.clip_arm('D7', scale_status='blocked')
        manifest = assemble(self.request)
        candidate = next(row for row in manifest['candidates'] if row['id'] == 'D7')
        self.assertEqual(candidate['status'], 'available')
        self.assertEqual(candidate['engineering_eligibility'], 'blocked')
        self.assertEqual(manifest['review_status'], 'awaiting_human_review')
        slot = self.request['candidates']['D7']
        original = slot['provenance']['source_result']
        from vipe_benchmark.files import read_json
        result = read_json(original['path'])
        result['engineering_eligibility'] = 'passed'
        substituted = self.record('substituted-result', result)
        slot['provenance']['source_result'] = substituted
        slot['evidence']['generation'] = substituted
        with self.assertRaisesRegex(ValueError, 'manufactures eligibility'):
            assemble(self.request)

    def test_fixture_native_result_and_incomplete_membership_are_rejected(self):
        self.clip_arm('D7')
        from vipe_benchmark.files import read_json
        slot = self.request['candidates']['D7']
        result = read_json(slot['provenance']['source_result']['path'])
        for name, altered, message in (
            ('fixture', dict(result, record_kind='fixture'), 'actual completed'),
            ('missing-map', dict(result, rows=result['rows'][:-1]), 'native map membership'),
            ('wrong-source', dict(result, rows=[dict(row, source_rgb=self.config)
                if row['camera'] == 2 and row['frame'] == 100 else row for row in result['rows']]),
             'native anchor source')):
            with self.subTest(name=name):
                substitute = self.record(name, altered)
                slot['provenance']['source_result'] = substitute
                slot['evidence']['generation'] = substitute
                with self.assertRaisesRegex(ValueError, message):
                    assemble(self.request)

    def test_shared_publisher_gate_and_every_clip_map_are_required(self):
        self.clip_arm()
        self.publisher_patch.stop()
        with mock.patch('vipe_benchmark.depth_aggregate._verify_published_clips',
                        side_effect=ValueError('live ledger finish missing')):
            with self.assertRaisesRegex(ValueError, 'live ledger finish missing'):
                assemble(self.request)
        self.publisher_patch.start()
        from vipe_benchmark.files import read_json
        slot = self.request['candidates']['D2']
        receipt = read_json(slot['clips']['path'])
        package = read_json(receipt['package']['path'])
        package['candidates'][1]['media'][0]['source_maps'][0] = self.config
        receipt['package'] = self.record('wrong-clip-map-package', package)
        slot['clips'] = self.record('wrong-clip-map-receipt', receipt)
        with self.assertRaisesRegex(ValueError, 'clip maps differ'):
            assemble(self.request)

    def test_historical_d2_anchors_require_two_accepted_ledger_finishes(self):
        self.historical_patch.stop()
        from vipe_benchmark.depth_aggregate import _verify_historical_anchors
        records = dict(fit=self.config, check=self.inputs)
        events = [dict(event='finish', status='complete', job_id='D2-' + role, result=record)
                  for role, record in records.items()]
        with mock.patch('vipe_benchmark.ledger.Ledger.events', return_value=events):
            _verify_historical_anchors(self.context, records)
        for incomplete in (events[:1], [dict(events[0], status='failed'), events[1]]):
            with mock.patch('vipe_benchmark.ledger.Ledger.events', return_value=incomplete):
                with self.assertRaisesRegex(ValueError, 'accepted ledger'):
                    _verify_historical_anchors(self.context, records)
        self.historical_patch.start()

    def test_identical_config_in_another_worktree_preserves_completed_previews(self):
        self.clip_arm('D7')
        relocated = self.root / 'other-worktree-config.json'
        relocated.write_bytes(Path(self.config['path']).read_bytes())
        self.request['bindings']['config'] = file_record(relocated)
        manifest = assemble(self.request)
        self.assertEqual(manifest['candidates'][8]['id'], 'D7')
        self.assertEqual(manifest['candidates'][8]['status'], 'available')
        self.request['bindings']['config']['bytes'] += 1
        with self.assertRaisesRegex(ValueError, 'config record bytes/path mismatch'):
            assemble(self.request)
        different = self.record('different-config', {'training': 'different configuration'})
        self.request['bindings']['config'] = different
        with self.assertRaisesRegex(ValueError, 'charged anchor preview receipt'):
            assemble(self.request)

    def test_historical_preview_revision_cannot_enter_corrected_aggregate(self):
        self.clip_arm('D7')
        slot = self.request['candidates']['D7']
        historical = read_json(slot['anchor_previews']['path'])
        historical['preview_revision'] = '001'
        slot['anchor_previews'] = self.record('historical-preview', historical)
        slot['evidence']['anchor_preview_accounting'] = self.record('historical-accounting', dict(
            schema='plan069-depth-anchor-preview-accounting/v1', status='complete',
            candidate='D7', result=slot['anchor_previews']))
        with self.assertRaisesRegex(ValueError, 'charged anchor preview receipt'):
            assemble(self.request)

    def test_anchor_images_require_actual_receipts_and_cpu_charges(self):
        self.clip_arm('D7')
        self.charge_patch.stop()
        with mock.patch('vipe_benchmark.depth_aggregate._verify_preview_charge',
                        side_effect=ValueError('anchor preview CPU charge absent')):
            with self.assertRaisesRegex(ValueError, 'CPU charge absent'):
                assemble(self.request)
        self.charge_patch.start()
        slot = self.request['candidates']['D7']
        slot.pop('anchor_previews')
        with self.assertRaisesRegex(ValueError, 'exact file record required'):
            assemble(self.request)


if __name__ == '__main__':
    unittest.main()

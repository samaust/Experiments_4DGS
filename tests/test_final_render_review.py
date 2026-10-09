"""Final-render review package (#34): matched held-out clips, viewer and human review import."""
import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))

import numpy as np
from PIL import Image

from vipe_benchmark.files import file_record, read_json, write_json

CAMERAS = (0, 10)
FRAMES = tuple(range(4))
ARMS = {'QF-B': dict(motion='M0', neighbors='N0'), 'QF-M1': dict(motion='M1', neighbors='N0'),
        'QF-N1': dict(motion='M0', neighbors='N1')}


def png(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(np.full((540, 960, 3), value, np.uint8)).save(path, format='PNG')
    return file_record(path)


class ReviewPackageTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        manifest = dict(cameras=[dict(id=str(c), frames=[dict(frame_id=f, path=f'rgb/{c}/{f:06d}.png',
            sha256=png(self.root/f'scene/rgb/{c}/{f:06d}.png', 10*f)['sha256']) for f in FRAMES]) for c in CAMERAS])
        write_json(self.root/'scene/manifest.json', manifest)
        self.request = dict(id='request-001', iterations=70000, render=dict(cameras=list(CAMERAS), frames=list(FRAMES), fps=25,
                            resolution=[960, 540]), compositions={a: dict(segmentation='S2', depth='D8', **c)
                                                                  for a, c in ARMS.items()},
                            bindings=dict(scene_manifest=file_record(self.root/'scene/manifest.json')))
        write_json(self.root/'request.json', self.request)
        self.results = {}
        for index, arm in enumerate(ARMS):
            frames = [dict(camera=c, frame=f, rgb=png(self.root/f'{arm}/camera{c}-frame{f:06d}.png', 40*index+f))
                      for c in CAMERAS for f in FRAMES]
            write_json(self.root/f'{arm}/result.json', dict(status='complete', phase='render', arm=arm,
                rendered_frames=frames, render_settings=self.request['render']))
            self.results[arm] = file_record(self.root/f'{arm}/result.json')

    def build(self, results=None, **kwargs):
        from final_render_review import build_package
        return build_package(file_record(self.root/'request.json'), self.results if results is None else results,
                             self.root/'package', **kwargs)

    def test_package_has_matched_reference_and_arm_clips_per_camera(self):
        from final_render_review import validate_package
        record = self.build()
        package = validate_package(record)
        self.assertEqual(package['schema'], 'plan069-final-render-review-package/v1')
        self.assertEqual([c['id'] for c in package['candidates']], ['reference', *ARMS])
        self.assertEqual(package['candidates'][0]['output_type'], 'reference')
        for candidate in package['candidates']:
            self.assertEqual(sorted(candidate['clips']), [str(c) for c in CAMERAS])
            for clip in candidate['clips'].values():
                self.assertEqual(clip['frame_ids'], list(FRAMES))
                probe = json.loads(subprocess.run(['ffprobe', '-v', 'error', '-count_frames', '-select_streams', 'v:0',
                    '-show_entries', 'stream=width,height,nb_read_frames,avg_frame_rate', '-of', 'json',
                    clip['record']['path']], capture_output=True, text=True, check=True).stdout)['streams'][0]
                self.assertEqual((probe['width'], probe['height'], int(probe['nb_read_frames']), probe['avg_frame_rate']),
                                 (960, 540, len(FRAMES), '25/1'))
        self.assertTrue((self.root/'package/index.html').read_text().count('<video') == 0)  # Built by script.
        self.assertIn('QF-M1', (self.root/'package/index.html').read_text())

    def test_failed_arm_is_listed_as_unavailable_with_reason(self):
        from final_render_review import validate_package
        results = dict(self.results, **{'QF-N1': dict(status='failed', reason='train phase exceeded its deadline')})
        package = validate_package(self.build(results))
        failed = next(c for c in package['candidates'] if c['id'] == 'QF-N1')
        self.assertEqual((failed['status'], failed['clips']), ('unavailable', {}))
        self.assertIn('deadline', failed['reason'])

    def test_changed_source_frame_or_clip_is_rejected(self):
        from final_render_review import validate_package
        record = self.build()
        png(self.root/'QF-M1/camera0-frame000002.png', 255)
        with self.assertRaisesRegex(ValueError, 'changed'):
            validate_package(record)

    def test_render_result_must_cover_every_held_out_frame(self):
        result = read_json(self.results['QF-B']['path'])
        result['rendered_frames'] = result['rendered_frames'][1:]
        write_json(self.root/'QF-B/short.json', result)
        with self.assertRaisesRegex(ValueError, 'coverage'):
            self.build(dict(self.results, **{'QF-B': file_record(self.root/'QF-B/short.json')}))


class ReviewImportTests(unittest.TestCase):
    def setUp(self):
        fixture = ReviewPackageTests('test_package_has_matched_reference_and_arm_clips_per_camera')
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        self.root = fixture.root
        self.package = fixture.build()
        self.review = dict(schema='plan069-final-render-review/v1', record_kind='human', reviewer='samaust',
            package=self.package, reviewed_at='2026-10-06', comparisons=dict(
                motion=dict(candidates=['QF-B', 'QF-M1'], preference='QF-M1',
                            observations=[dict(candidate='QF-M1', camera=10, frame=2,
                                               text='Less ghosting on the moving player.')]),
                neighbors=dict(candidates=['QF-B', 'QF-N1'], preference='tie', observations=[])),
            overall=dict(preference='unclear', tradeoffs=''))

    def imported(self, review):
        from final_render_review import import_review
        path = self.root/f'review-{len(list(self.root.iterdir()))}.json'
        write_json(path, review)
        return import_review(self.package, file_record(path), self.root/f'imported-{path.stem}.json')

    def test_human_review_bound_to_package_is_imported(self):
        record = self.imported(self.review)
        value = read_json(record['path'])
        self.assertEqual(value['status'], 'imported')
        self.assertEqual(value['review']['comparisons']['motion']['preference'], 'QF-M1')

    def test_review_must_reference_package_candidates_cameras_and_frames(self):
        for path, value, message in [
                (('comparisons', 'motion', 'preference'), 'QF-M2', 'preference'),
                (('comparisons', 'motion', 'observations', 0, 'camera'), 3, 'camera'),
                (('comparisons', 'motion', 'observations', 0, 'frame'), 99, 'frame'),
                (('record_kind',), 'fixture', 'human'), (('reviewer',), ' ', 'reviewer')]:
            review = copy.deepcopy(self.review)
            target = review
            for key in path[:-1]:
                target = target[key]
            target[path[-1]] = value
            with self.subTest(path=path), self.assertRaisesRegex(ValueError, message):
                self.imported(review)

    def test_review_of_another_package_is_rejected(self):
        review = dict(self.review, package=dict(self.package, sha256='0'*64))
        with self.assertRaisesRegex(ValueError, 'package'):
            self.imported(review)


if __name__ == '__main__':
    unittest.main()


class ViewerLabelTests(unittest.TestCase):
    def setUp(self):
        self.base = ReviewPackageTests()
        self.base.setUp()
        self.addCleanup(self.base.doCleanups)

    def test_captions_and_intro_explain_every_arm_in_words(self):
        from vipe_benchmark.files import read_json
        record = self.base.build()
        html = (self.base.root/'package'/'index.html').read_text()
        package = read_json(record['path'])
        labels = {c['id']: c['label'] for c in package['candidates']}
        self.assertIn('ground truth', labels['reference'])
        self.assertIn('9-frame median-background mask', labels['QF-M1'])
        self.assertIn('highest Jaccard co-visibility', labels['QF-N1'])
        self.assertIn('(baseline)', labels['QF-B'])
        self.assertIn('trained for 70,000 steps on all 50 frames', html)
        self.assertNotIn('5,000-step', html)

    def test_viewer_offers_deep_zoom_and_one_shared_pan_for_all_videos(self):
        self.base.build()
        html = (self.base.root/'package'/'index.html').read_text()
        for level in ('4', '8', '16'):
            self.assertIn(f'<option>{level}</option>', html)
        self.assertIn("grid.style.setProperty('--ox'", html)
        self.assertNotIn("v.style.setProperty('--ox'", html)
        self.assertIn('linkView(v)', html)

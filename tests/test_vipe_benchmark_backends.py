"""Native API wiring tests with CPU arrays and fake models; no model imports."""
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace
import os
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from vipe_benchmark.backends import (
    AssetBundle, BackendError, DA3Backend, DepthProBackend, GroundingDetector,
    LegacyStandaloneBackend, LegacyViPESegmentationBackend, Metric3DBackend, S1TrackerBridge,
    RTDetrDetector, SAM2Backend, SAM3Backend, SOURCE_PINS, UniDepthBackend,
    build_backend, detection_rows, normalize_phrase,
    _build_native, _sam2, _sam3_image_processor, _legacy_vipe_segmentation, _s1_aot_module, _s1_tracker,
)
from vipe_benchmark.files import file_record


class FakeTensor(np.ndarray):
    def to(self, *_args, **_kwargs):
        return self

    def sigmoid(self):
        return 1 / (1 + np.exp(-self))


class FakeRuntime:
    device = 'fake:cpu'

    def __init__(self):
        self.precisions = []

    def tensor(self, value, dtype='float32'):
        return np.array(value, dtype=dtype).view(FakeTensor)

    @contextmanager
    def inference(self, precision='float32'):
        self.precisions.append(precision)
        yield

    def resize(self, value, shape):
        import cv2
        return cv2.resize(np.asarray(value, np.float32), (shape[1], shape[0]), interpolation=cv2.INTER_LINEAR)


class HistoricalCacheBindingTests(unittest.TestCase):
    def test_fresh_trackers_reuse_stable_checkpoint_cache_keys(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            paths = {}
            for key in ('sam_checkpoint', 'aot_checkpoint', 'grounding_checkpoint', 'bert_snapshot'):
                paths[key] = root / key
                paths[key].write_text('fixture')
            hub = SimpleNamespace(get_dir=lambda: 'original', load_state_dict_from_url=lambda *a, **k: None)
            config = SimpleNamespace(text_encoder_type='original')
            trackers, caches, locations = [], [], []
            def factory(phrases, model_cache):
                folder = Path(hub.get_dir())
                for relative in ('sam/sam_vit_b_01ec64.pth', 'aot/R50_DeAOTL_PRE_YTB_DAV.pth'):
                    path = folder / relative
                    self.assertTrue(path.is_file())
                    model_cache.setdefault(str(path), object())
                locations.append(folder)
                caches.append(model_cache)
                tracker = object()
                trackers.append(tracker)
                return tracker
            modules = {'vipe.priors.track_anything': SimpleNamespace(TrackAnythingPipeline=factory),
                'vipe.streams.base': SimpleNamespace(VideoFrame=object),
                'vipe.utils.model_cache': SimpleNamespace(ModelCache=dict),
                'vipe.priors.track_anything.groundingdino.config': SimpleNamespace(config=config)}
            class Bundle:
                provenance = {}
                def __getitem__(self, key):
                    return str(paths[key])
                def module(self, name, source):
                    return modules[name]
            bundle = Bundle()
            bundle.paths = paths
            runtime = SimpleNamespace(torch=SimpleNamespace(hub=hub))
            backend = _legacy_vipe_segmentation(bundle, runtime)
            try:
                first, second = backend.factory(), backend.factory()
                self.assertIsNot(first, second)
                self.assertIs(caches[0], caches[1])
                self.assertEqual(locations[0], locations[1])
                self.assertEqual(len(caches[0]), 2)
                self.assertEqual(config.text_encoder_type, 'original')
                self.assertEqual(hub.get_dir(), 'original')
            finally:
                backend.asset_folder.cleanup()


def image(shape=(4, 6)):
    rgb = np.arange(np.prod(shape) * 3, dtype=np.uint8).reshape(*shape, 3)
    return rgb, np.ones(shape, bool)


def detector(rows):
    class Detector:
        metadata = {'fake': True}
        calls = 0

        def __call__(self, rgb):
            self.calls += 1
            return rows
    return Detector()


class AssetAndDetectorTests(unittest.TestCase):
    def test_missing_assets_fail_before_torch_import(self):
        with self.assertRaisesRegex(BackendError, 'missing explicit local assets'):
            build_backend('S3', {})

    def test_source_pin_and_snapshot_contents_are_not_inferred_from_directory_name(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            config = root / 'file.py'; config.write_text('source')
            checkpoint = root / 'depth_pro.pt'; checkpoint.write_bytes(b'fake')
            records = dict(depth_pro_source=dict(path=str(root), revision='0' * 40, files=[file_record(config)]),
                           depth_pro_checkpoint=file_record(checkpoint))
            with self.assertRaisesRegex(BackendError, 'wrong or missing revision'):
                AssetBundle('D4', records)
            records['depth_pro_source']['revision'] = SOURCE_PINS['depth_pro_source']
            bundle = AssetBundle('D4', records)
            self.assertEqual(bundle['depth_pro_checkpoint'], str(checkpoint))
            checkpoint.write_bytes(b'changed')
            with self.assertRaisesRegex(ValueError, 'changed file'):
                AssetBundle('D4', records)

    def test_phrase_ambiguity_and_capacity_fail_before_casting(self):
        for phrase in ('', 'person basketball', 'ball', 'player'):
            with self.subTest(phrase=phrase), self.assertRaises(BackendError):
                normalize_phrase(phrase)
        self.assertEqual(normalize_phrase('sports ball'), 'basketball')
        with self.assertRaisesRegex(BackendError, 'capacity'):
            detection_rows([[0, 0, 1, 1]] * 256, [.9] * 256, ['person'] * 256)

    def test_grounding_uses_native_caption_thresholds_and_float_boxes(self):
        runtime = FakeRuntime(); calls = []
        def predict(model, tensor, caption, box_threshold, text_threshold, device):
            calls.append((caption, box_threshold, text_threshold, device))
            model.forward(tensor)
            return np.array([[.5, .5, .2, .5]], np.float32), np.array([.8]), ['basketball']
        model = SimpleNamespace(forward=lambda image: dict(pred_logits=np.zeros((1, 1, 3)),
                                                          pred_boxes=np.ones((1, 1, 4))))
        gd = GroundingDetector(model, lambda im, _: (np.zeros((3, 8, 12)), None), predict, runtime, .25)
        rgb, _ = image()
        result = gd(rgb)
        np.testing.assert_allclose(result[0]['box'], [2.4, 1, 3.6, 3], atol=1e-6)
        self.assertEqual(calls, [('person.basketball.', .35, .25, 'fake:cpu')])
        self.assertEqual(gd.metadata['actual_processed_shape'], [8, 12])
        self.assertEqual(gd.diagnostics['detector_rgb'].shape, (3, 8, 12))
        self.assertEqual(gd.diagnostics['detector_raw_token_logits'].shape, (1, 3))

    def test_rtdetr_threshold_equality_label_names_and_processor(self):
        calls = {}
        class Processor:
            def __call__(self, **kwargs):
                calls['processor'] = kwargs
                return {'pixel_values': np.zeros((1, 3, 640, 640)).view(FakeTensor)}

            def post_process_object_detection(self, output, **kwargs):
                calls['post'] = kwargs
                return [dict(boxes=np.tile([0, 0, 2, 2], (4, 1)), scores=np.array([.35, .9, .349, .99]),
                             labels=np.array([0, 7, 7, 2]))]
        class Model:
            config = SimpleNamespace(id2label={0: 'person', 7: 'sports ball', 2: 'car'})
            def __call__(self, **kwargs):
                return kwargs
        rgb, _ = image()
        rows = RTDetrDetector(Processor(), Model(), FakeRuntime())(rgb)
        self.assertEqual([r['class'] for r in rows], ['person', 'basketball'])
        self.assertEqual([r['index'] for r in rows], [0, 1])
        self.assertEqual(calls['processor']['size'], {'height': 640, 'width': 640})
        self.assertFalse(calls['processor']['do_normalize'])
        self.assertEqual(calls['post']['threshold'], 0.)


class SAM2Tests(unittest.TestCase):
    def make_backend(self, missing_successor=False):
        shape = (4, 6)
        rows = detection_rows([[0, 0, 3, 3], [1, 0, 5, 3]], [.6, .8], ['person', 'basketball'])
        native_detector = detector(rows)
        class ImagePredictor:
            def set_image(self, rgb):
                self.shape = rgb.shape[:2]

            def predict(self, **kwargs):
                assert kwargs['multimask_output'] and kwargs['return_logits']
                masks = np.stack([np.full(shape, -1.), np.ones(shape), np.full(shape, -2.)])
                return masks, np.array([.1, .9, .2]), np.zeros((3, 2, 2))
        class VideoPredictor:
            starts = 0
            resets = 0
            masks = []

            def init_state(self, **kwargs):
                from PIL import Image
                self.starts += 1
                self.masks = []
                restored = np.array(Image.open(Path(kwargs['video_path']) / '00000.jpg'))
                np.testing.assert_array_equal(restored, image()[0])
                return {'number': self.starts}

            def add_new_mask(self, state, **kwargs):
                self.masks.append(kwargs)

            def propagate_in_video(self, state, **kwargs):
                assert kwargs == dict(start_frame_idx=0, max_frame_num_to_track=1, reverse=False)
                yield 0, [1, 2], np.ones((2, 1, *shape))
                if not missing_successor:
                    # ID order is deliberately reversed. Mask logit wins over
                    # detector score on successor; equal logits use score.
                    output = np.ones((2, 1, *shape))
                    output[1, 0, 1, 1] = 2
                    yield 1, [2, 1], output

            def reset_state(self, state):
                self.resets += 1
        video = VideoPredictor()
        return SAM2Backend('S2', native_detector, ImagePredictor(), video, FakeRuntime()), native_detector, video

    def test_pair_reset_highest_iou_original_grid_overlap_and_static(self):
        backend, det, video = self.make_backend()
        rgb, valid = image(); valid[0, 0] = False
        for start in (20, 21):
            rows = backend.segment([rgb, rgb], [valid, valid], frame_ids=[start, start + 1])
            self.assertTrue((rows[0].labels[valid] == 2).all())
            self.assertEqual(rows[1].labels[1, 1], 1)
            self.assertEqual(rows[0].labels[0, 0], -1)
            self.assertTrue((rows[0].static(np.zeros(valid.shape, bool)) == 0).all())
            self.assertEqual(rows[0].metadata['suppressed'][0]['pixels'], int(valid.sum()))
        self.assertEqual((det.calls, video.starts, video.resets), (2, 2, 2))
        self.assertTrue(all(m['mask'].all() for m in video.masks))

    def test_empty_keyframe_never_runs_successor_detector(self):
        backend, det, video = self.make_backend()
        backend.detector = detector([])
        rgb, valid = image()
        rows = backend.segment([rgb, rgb], [valid, valid], frame_ids=[0, 1])
        self.assertEqual(len(rows), 2)
        self.assertFalse(rows[1].labels.any())
        self.assertEqual(video.starts, 0)
        self.assertEqual(backend.detector.calls, 1)

    def test_incomplete_propagation_fails_and_resets(self):
        backend, _, video = self.make_backend(missing_successor=True)
        rgb, valid = image()
        with self.assertRaisesRegex(BackendError, 'successor'):
            backend.segment([rgb, rgb], [valid, valid], frame_ids=[0, 1])
        self.assertEqual(video.resets, 1)

    def test_native_postprocessing_skip_fails_pair_and_resets_before_export(self):
        import warnings
        message = ('CUDA kernel error\nsecond error line\n\n'
            "Skipping the post-processing step due to the error above. You can "
            "still use SAM 2 and it's OK to ignore the error above, although some post-processing "
            "functionality may be limited (which doesn't affect the results in most cases; see "
            "https://github.com/facebookresearch/sam2/blob/main/INSTALL.md).")
        for component in ('S2', 'S4'):
            with self.subTest(component=component):
                backend, _, video = self.make_backend()
                backend.component = component
                returned = []
                def propagate(state, **kwargs):
                    yield 0, [1, 2], np.ones((2, 1, 4, 6))
                    warnings.warn_explicit(message, UserWarning, filename='sam2/sam2_video_predictor.py',
                                           lineno=783, module='sam2.sam2_video_predictor')
                    returned.append('unfilled fallback')
                    yield 1, [1, 2], np.ones((2, 1, 4, 6))
                video.propagate_in_video = propagate
                rgb, valid = image()
                with self.assertRaisesRegex(UserWarning, 'Skipping the post-processing'):
                    backend.segment([rgb, rgb], [valid, valid], frame_ids=[20, 21])
                self.assertEqual(returned, [])
                self.assertEqual(video.resets, 1)

    def test_source_frames_not_internal_indices_or_cross_role_context(self):
        backend, det, _ = self.make_backend()
        rgb, valid = image()
        for frames in ([20, 22], [49, 50], [199, 200], [21, 20]):
            with self.subTest(frames=frames), self.assertRaises(ValueError):
                backend.segment([rgb, rgb], [valid, valid], frame_ids=frames)
        self.assertEqual(det.calls, 0)


class S1NativeBridgeTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.runtime = FakeRuntime()
        self.interpolations = []
        def interpolate(value, *, size, mode):
            self.interpolations.append(dict(shape=tuple(value.shape), size=size, mode=mode, dtype=value.dtype))
            self.assertEqual(mode, 'nearest')
            y = np.arange(size[0]) * value.shape[-2] // size[0]
            x = np.arange(size[1]) * value.shape[-1] // size[1]
            return value[..., y[:, None], x[None, :]]
        self.runtime.torch = SimpleNamespace(nn=SimpleNamespace(functional=SimpleNamespace(interpolate=interpolate)))
        self.arguments = dict(phase='PRE_YTB_DAV', model='r50_deaotl', long_term_mem_gap=9999,
                              max_len_long_term=9999, gpu_id=0, model_path=str(self.root / 'checkpoint.pth'))

    def make_module(self, *, changed_kwargs=None, fail=False):
        module = SimpleNamespace()
        calls, tracker = [], SimpleNamespace(engine=SimpleNamespace(input_size_2d=(2, 3)))
        tracker.restart = Mock()
        tracker.add_reference_frame = Mock()
        tracker.update_memory = Mock()
        tracker.track = Mock(return_value=np.arange(24, dtype=np.float32).reshape(1, 1, 4, 6) % 2)
        def build_engine(name, phase, *, aot_model, gpu_id, short_term_mem_skip, long_term_mem_gap):
            calls.append(dict(name=name, phase=phase, aot_model=aot_model, gpu_id=gpu_id,
                              short_term_mem_skip=short_term_mem_skip, long_term_mem_gap=long_term_mem_gap))
            return tracker.engine
        def get_aot(arguments):
            self.assertEqual(arguments, self.arguments)
            Path('result/model').mkdir(parents=True)
            Path('result/model/config.txt').write_text('native relative config directory')
            kwargs = dict(aot_model=tracker, gpu_id=0, short_term_mem_skip=1,
                          long_term_mem_gap=9999, max_len_long_term=9999)
            kwargs.update(changed_kwargs or {})
            module.build_engine('deaotengine', phase='eval', **kwargs)
            if fail:
                raise RuntimeError('native constructor failed')
            return tracker
        module.build_engine, module.get_aot = build_engine, get_aot
        return module, tracker, calls

    def build(self, module):
        with patch.dict(os.environ, {'TMPDIR': str(self.root)}):
            tracker = _s1_tracker(module, self.runtime, self.arguments)
        self.addCleanup(tracker._config_directory.cleanup)
        return tracker

    def test_constructor_removes_only_inert_argument_and_contains_native_config_writes(self):
        module, native, calls = self.make_module()
        original, cwd = module.build_engine, Path.cwd()
        bridge = self.build(module)
        self.assertIs(module.build_engine, original)
        self.assertEqual(Path.cwd(), cwd)
        self.assertEqual(calls, [dict(name='deaotengine', phase='eval', aot_model=native,
                                    gpu_id=0, short_term_mem_skip=1, long_term_mem_gap=9999)])
        directory = Path(bridge.metadata['config_working_directory'])
        self.assertTrue(directory.is_relative_to(self.root))
        self.assertEqual((directory / 'result/model/config.txt').read_text(), 'native relative config directory')
        self.assertEqual(bridge.metadata['engine_argument_bridge']['removed'], {'max_len_long_term': 9999})

    def test_constructor_failure_restores_cwd_and_native_builder(self):
        module, _, _ = self.make_module(fail=True)
        original, cwd = module.build_engine, Path.cwd()
        with patch.dict(os.environ, {'TMPDIR': str(self.root)}), self.assertRaisesRegex(RuntimeError, 'constructor failed'):
            _s1_tracker(module, self.runtime, self.arguments)
        self.assertEqual(Path.cwd(), cwd)
        self.assertIs(module.build_engine, original)
        self.assertEqual(list(self.root.iterdir()), [])

    def test_constructor_rejects_changed_arguments_and_unsupervised_temporary_root(self):
        module, _, calls = self.make_module()
        for altered in ({'max_len_long_term': 3}, {'long_term_mem_gap': 1}, {'gpu_id': 1}, {'gpu_id': False}):
            with self.subTest(altered=altered), self.assertRaisesRegex(BackendError, 'exact frozen'):
                _s1_tracker(module, self.runtime, dict(self.arguments, **altered))
        with patch.dict(os.environ, {}, clear=True), self.assertRaisesRegex(BackendError, 'TMPDIR'):
            _s1_tracker(module, self.runtime, self.arguments)
        self.assertEqual(calls, [])

    def test_native_wrapper_argument_drift_is_rejected_before_engine_construction(self):
        for altered in ({'max_len_long_term': 2}, {'long_term_mem_gap': 1}, {'short_term_mem_skip': 2}, {'extra': 1}):
            module, _, calls = self.make_module(changed_kwargs=altered)
            with self.subTest(altered=altered), patch.dict(os.environ, {'TMPDIR': str(self.root)}), \
                 self.assertRaisesRegex(BackendError, 'constructor contract'):
                _s1_tracker(module, self.runtime, self.arguments)
            self.assertEqual(calls, [])

    def test_memory_update_uses_exact_native_nearest_grid_and_keeps_original_export(self):
        module, native, _ = self.make_module()
        bridge = self.build(module)
        rgb, valid = image()
        prediction = native.track.return_value.copy()
        class SAM:
            def set_image(self, image):
                pass
            def predict(self, **kwargs):
                return np.ones((1, *valid.shape), bool), np.ones(1), np.zeros((1, 2, 2))
        backend = LegacyStandaloneBackend(detector(detection_rows([[0, 0, 2, 2]], [.7], ['person'])),
                                           SAM(), bridge, self.runtime)
        rows = backend.segment([rgb, rgb], [valid, valid], frame_ids=[20, 21])
        np.testing.assert_array_equal(native.update_memory.call_args.args[0], prediction[..., ::2, ::2])
        np.testing.assert_array_equal(rows[1].labels, prediction[0, 0])
        self.assertEqual(native.restart.call_count, 2)
        self.assertEqual(self.interpolations, [dict(shape=(1, 1, 4, 6), size=(2, 3), mode='nearest', dtype=np.dtype('float32'))])
        self.assertEqual(rows[1].metadata['tracker_bridge']['memory_update'],
                         dict(original_shape=[4, 6], internal_shape=[2, 3], mode='nearest'))

    def test_pair_bridge_rejects_extra_frames_reference_and_propagation(self):
        module, native, _ = self.make_module()
        bridge = self.build(module)
        rgb, valid = image()
        for ids in ([0, 1, 2], [20, 22], [49, 50], [200]):
            with self.subTest(ids=ids), self.assertRaises(BackendError), bridge.pair(ids):
                self.fail('invalid pair admitted')
        with self.assertRaisesRegex(BackendError, 'outside'):
            bridge.restart()
        with bridge.pair([20, 21]):
            bridge.restart()
            with self.assertRaisesRegex(BackendError, 'step zero'):
                bridge.add_reference_frame(rgb, valid, 1, 1)
            bridge.add_reference_frame(rgb, valid, 1, 0)
            with self.assertRaisesRegex(BackendError, 'one reference'):
                bridge.add_reference_frame(rgb, valid, 1, 0)
            value = bridge.track(rgb)
            with self.assertRaisesRegex(BackendError, 'exactly one successor'):
                bridge.track(rgb)
            bridge.update_memory(value)
            with self.assertRaisesRegex(BackendError, 'single tracked successor'):
                bridge.update_memory(value)
            bridge.restart()
        self.assertEqual(native.track.call_count, 1)

    def test_pair_bridge_rejects_missing_resets_and_singleton_tracking(self):
        module, _, _ = self.make_module()
        bridge = self.build(module)
        rgb, valid = image()
        with self.assertRaisesRegex(BackendError, 'both resets'), bridge.pair([20, 21]):
            bridge.restart()
        with bridge.pair([100]):
            bridge.restart()
            with self.assertRaisesRegex(BackendError, 'one reference'):
                bridge.add_reference_frame(rgb, valid, 1, 0)
            bridge.restart()

    def test_native_palette_import_preserves_seed_state_on_success_and_failure(self):
        original_state = np.random.get_state()
        self.addCleanup(np.random.set_state, original_state)
        for fail in (False, True):
            np.random.seed(0)
            expected = np.random.RandomState(0).random_sample(4)
            sentinel = object()
            def module(*args):
                np.random.seed(200)
                np.random.random(765)
                if fail:
                    raise RuntimeError('import failed')
                return sentinel
            if fail:
                with self.assertRaisesRegex(RuntimeError, 'import failed'):
                    _s1_aot_module(SimpleNamespace(module=module))
            else:
                self.assertIs(_s1_aot_module(SimpleNamespace(module=module)), sentinel)
            np.testing.assert_array_equal(np.random.random(4), expected)


class LegacyAndSAM3Tests(unittest.TestCase):
    def test_s1_native_box_refinement_tiny_masks_merge_and_tracking(self):
        rgb, valid = image(); calls = []
        rows = detection_rows([[.9, .9, 2.9, 2.9], [1, 1, 3, 3]], [.7, .8], ['person', 'basketball'])
        class SAM:
            def set_image(self, rgb):
                pass

            def predict(self, **kwargs):
                calls.append(kwargs)
                masks = np.zeros((2, *valid.shape), bool); masks[1, 1, 1] = True
                return masks, np.array([.1, .9]), np.zeros((2, 2, 2))
        class Tracker:
            restarts = 0
            def restart(self):
                self.restarts += 1
            def add_reference_frame(self, rgb, labels, objects, frame_step):
                self.labels = labels
                assert objects == 2 and frame_step == 0
            def track(self, rgb):
                return self.labels[None, None]
            def update_memory(self, value):
                pass
        tracker = Tracker(); det = detector(rows)
        backend = LegacyStandaloneBackend(det, SAM(), tracker, FakeRuntime())
        result = backend.segment([rgb, rgb], [valid, valid], frame_ids=[20, 21])
        self.assertEqual(result[0].labels[1, 1], 2)
        self.assertEqual(int((result[0].labels > 0).sum()), 1)  # not filtered by 200-pixel setting
        self.assertEqual(result[1].semantics['2']['class'], 'basketball')
        self.assertEqual(len(calls), 4)
        np.testing.assert_array_equal(calls[0]['box'], [0, 0, 2, 2])
        self.assertEqual((det.calls, tracker.restarts), (1, 2))

    def test_s0_observes_native_scores_without_changing_invocation(self):
        rgb, valid = image(); created = []
        class GD:
            def register_forward_hook(self, hook):
                self.hook = hook
                return SimpleNamespace(remove=lambda: created.append('hook removed'))
        class Tracker:
            def __init__(self):
                self.segtracker = SimpleNamespace(detector=SimpleNamespace(gd=GD(), run_grounding_tensor=self.detect))
                self.frames = []
            def detect(self):
                self.segtracker.detector.gd.hook(None, (np.zeros((1, 3, 8, 12)),), dict(
                    pred_logits=np.full((1, 1, 2), 2.).view(FakeTensor),
                    pred_boxes=np.array([[[.5, .5, .2, .2]]])))
                return valid.shape, np.array([[2.4, 1.6, 3.6, 2.4]], np.float32), ['person']
            def track(self, frame):
                self.frames.append(frame.raw_frame_idx)
                if len(self.frames) == 1:
                    self.segtracker.detector.run_grounding_tensor()
                return np.ones(valid.shape, np.uint8), {1: 'person'}
        def factory():
            native = Tracker(); created.append(native); return native
        backend = LegacyViPESegmentationBackend(factory, SimpleNamespace, FakeRuntime())
        result = backend.segment([rgb, rgb], [valid, valid], frame_ids=[20, 21])
        self.assertEqual(created[0].frames, [20, 21])
        self.assertEqual(created[1], 'hook removed')
        self.assertAlmostEqual(result[1].semantics['1']['score'], 1 / (1 + np.exp(-2)))
        self.assertEqual(result[0].diagnostics['detector_rgb'].shape, (3, 8, 12))
        self.assertEqual(result[0].diagnostics['detector_selected_boxes_xyxy'].dtype, np.float32)
        np.testing.assert_array_equal(result[0].diagnostics['detector_selected_boxes_xyxy'],
                                      np.array([[2.4, 1.6, 3.6, 2.4]], np.float32))
        self.assertEqual(result[1].diagnostics, {})

    def test_sam3_separate_concepts_native_births_and_score_ties(self):
        rgb, valid = image(); sessions = []
        class Video:
            def init_state(self, **kwargs):
                state = {}; sessions.append(state)
                self_images = kwargs['resource_path']
                np.testing.assert_array_equal(np.asarray(self_images[0]), rgb)
                return state
            def add_prompt(self, state, **kwargs):
                state['concept'] = kwargs['text_str']
            def propagate_in_video(self, state, **kwargs):
                assert kwargs['max_frame_num_to_track'] == 1
                for frame in (0, 1):
                    count = int(state['concept'] == 'person' or frame == 1)
                    yield frame, dict(out_obj_ids=np.array([7] * count), out_probs=np.array([.8] * count),
                        out_binary_masks=np.ones((count, *valid.shape), bool))
            def reset_state(self, state):
                state['reset'] = True
        backend = SAM3Backend(lambda: None, Video, FakeRuntime())
        result = backend.segment([rgb, rgb], [valid, valid], frame_ids=[20, 21])
        self.assertEqual(result[0].semantics['1']['class'], 'person')
        self.assertEqual(result[1].semantics['2']['class'], 'basketball')  # semantic name settles score tie
        self.assertEqual(result[1].metadata['births'], [2])
        self.assertEqual(len(sessions), 2)
        self.assertTrue(all(s['reset'] for s in sessions))


class DepthTests(unittest.TestCase):
    K = np.array([[1200, 0, 1.3], [900, 900, .7], [0, 0, 1]], np.float64)

    def test_unidepth_byte_nchw_K_and_actual_dimensions(self):
        rgb, valid = image(); calls = {}
        class Model:
            def encode_decode(self, **kwargs):
                return None
            def infer(self, pixels, K):
                calls.update(pixels=pixels, K=K.copy())
                processed_K = K.copy(); processed_K[:, :2] *= 2.3
                self.encode_decode(inputs={'image': np.zeros((1, 3, 28, 42)),
                                           'camera': SimpleNamespace(K=processed_K)})
                values = np.full((1, 1, *valid.shape), 4., np.float32); values[..., 0, 0] = 0
                return dict(depth=values, confidence=np.full_like(values, .7))
        model = Model(); original = model.encode_decode
        result = UniDepthBackend('D1', model, FakeRuntime()).predict(rgb, self.K, valid)
        self.assertEqual(calls['pixels'].dtype, np.uint8)
        self.assertEqual(calls['pixels'].shape, (1, 3, 4, 6))
        np.testing.assert_allclose(calls['K'][0], self.K)
        self.assertEqual(result.metadata['actual_processed_shape'], [28, 42])
        expected_K = self.K[None].copy(); expected_K[:, :2] *= 2.3
        np.testing.assert_allclose(result.metadata['native_processed_K'], expected_K)
        self.assertEqual(result.metadata['confidence']['direction'], 'lower is more confident')
        np.testing.assert_allclose(result.confidence[result.valid], .7)
        self.assertTrue(np.isnan(result.confidence[~result.valid]).all())
        self.assertEqual(result.metadata['focal_conversion_count'], 0)
        self.assertTrue(np.isnan(result.depth[0, 0]))
        self.assertEqual(model.encode_decode, original)

    def test_d0_preserves_native_centered_K_and_float_invocation(self):
        rgb, valid = image(); inputs = []
        inner = SimpleNamespace(encode_decode=lambda **kwargs: None)
        class Model:
            model = inner
            def estimate(self, src):
                inputs.append(src)
                self.model.encode_decode(inputs={'image': np.zeros((1, 3, 28, 42))})
                return SimpleNamespace(metric_depth=np.full(valid.shape, 5), confidence=np.ones(valid.shape))
        result = UniDepthBackend('D0', Model(), FakeRuntime(), legacy_input=SimpleNamespace).predict(rgb, self.K, valid)
        self.assertEqual(inputs[0].rgb.dtype, np.float32)
        self.assertEqual(result.metadata['native_input_K'], [[1200., 0., 3.], [0., 1200., 2.], [0., 0., 1.]])
        self.assertEqual(result.metadata['confidence']['direction'], 'lower is more confident')

    def test_da3_uses_processor_K_once_no_pose_alignment_and_missing_confidence(self):
        rgb, valid = image(); calls = {}
        processed_K = np.array([[[150, 0, .2], [0, 450, .4], [0, 0, 1]]], np.float32)
        class Model:
            def input_processor(self, images, **kwargs):
                calls['processor'] = kwargs
                return np.zeros((1, 3, 2, 3)), None, processed_K.copy()
            def _prepare_model_inputs(self, pixels, ext, K):
                return pixels[None], None, K[None]
            def forward(self, pixels, **kwargs):
                calls['forward'] = kwargs
                return {'raw': np.full((1, 2, 3), 8.)}
            def output_processor(self, output):
                return SimpleNamespace(depth=output['raw'], conf=None, is_metric=0)
        result = DA3Backend(Model(), FakeRuntime()).predict(rgb, self.K, valid)
        np.testing.assert_allclose(result.depth, 8.)  # mean(150,450)/300 = 1, not input focal/300
        self.assertEqual(result.metadata['focal_conversion_count'], 1)
        np.testing.assert_allclose(result.raw_depth, 8.)
        self.assertIsNone(result.confidence)
        self.assertIsNone(calls['forward']['extrinsics'])
        self.assertFalse(calls['forward']['infer_gs'])
        self.assertEqual(calls['processor']['process_res'], 504)
        self.assertTrue(calls['processor']['sequential'])

    def test_da3_invalid_support_is_not_interpolated_and_double_scaling_fails(self):
        rgb, valid = image()
        class Model:
            def input_processor(self, *args, **kwargs):
                return np.zeros((1, 3, 2, 3)), None, np.eye(3)[None] * [300, 300, 1]
            def _prepare_model_inputs(self, pixels, ext, K):
                return pixels[None], None, K[None]
            def forward(self, pixels, **kwargs):
                return {}
            def output_processor(self, out):
                raw = np.ones((2, 3), np.float32); raw[0, 0] = np.nan
                return SimpleNamespace(depth=raw, is_metric=0)
        model = Model()
        result = DA3Backend(model, FakeRuntime()).predict(rgb, self.K, valid)
        self.assertTrue(np.isnan(result.depth[1, 1]))
        self.assertFalse(result.valid[1, 1])
        model.output_processor = lambda _: SimpleNamespace(depth=np.ones((2, 3)), is_metric=1)
        with self.assertRaisesRegex(BackendError, 'already-metric'):
            DA3Backend(model, FakeRuntime()).predict(rgb, self.K, valid)

    def test_metric3d_resized_focal_unpad_and_native_clamp(self):
        rgb, valid = image((540, 960)); calls = {}
        class Model:
            def inference(self, inputs):
                calls['input'] = inputs['input']
                return np.full((1, 1, 616, 1064), 1000.), None, {}
        result = Metric3DBackend(Model(), FakeRuntime()).predict(rgb, self.K, valid)
        self.assertEqual(calls['input'].shape, (1, 3, 616, 1064))
        self.assertAlmostEqual(result.metadata['factor'], 1200 * (1064 / 960) / 1000)
        self.assertEqual(result.metadata['pad'], [9, 9, 0, 0])
        self.assertEqual(result.metadata['resized_shape'], [598, 1064])
        self.assertTrue((result.depth == 300).all())
        self.assertEqual(result.metadata['saturated_fraction'], 1.)
        self.assertIsNone(result.confidence)

    def test_depth_pro_focal_device_tensor_native_inversion_and_no_extra_factor(self):
        rgb, valid = image(); calls = {}
        class Model:
            def forward(self, x):
                return np.full((1, 1, 1536, 1536), .5, np.float32), None
            def infer(self, x, **kwargs):
                calls.update(kwargs)
                self.forward(np.zeros((1, 3, 1536, 1536), np.float32))
                return dict(depth=np.full(valid.shape, 23., np.float32))
        result = DepthProBackend(Model(), lambda x: np.array(x), FakeRuntime()).predict(rgb, self.K, valid)
        self.assertEqual(calls['f_px'].dtype, np.float32)
        self.assertEqual(float(calls['f_px']), 1200.)
        self.assertTrue((result.depth == 23).all())
        self.assertEqual(result.metadata['focal_conversion_count'], 0)
        self.assertEqual(result.metadata['actual_processed_shape'], [1536, 1536])
        self.assertIsNone(result.confidence)
        self.assertTrue((result.raw_depth == .5).all())


class FactoryTests(unittest.TestCase):
    def sam3_fixture(self, *, missing=(), unexpected=(), load_calls=1):
        calls = []
        class Model:
            def load_state_dict(self, state, *, strict):
                calls.append(('load', state, strict))
                return SimpleNamespace(missing_keys=list(missing), unexpected_keys=list(unexpected))
            def to(self, **kwargs):
                calls.append(('move', kwargs))
                return self
        model = Model()
        def native_load(model, checkpoint_path):
            calls.append(('native', checkpoint_path))
            for _ in range(load_calls):
                # Stand in for the native, already filtered detector subset.
                model.load_state_dict({'detector_weight': 'unchanged'}, strict=False)
        builders = SimpleNamespace(_load_checkpoint=native_load)
        def build(**kwargs):
            calls.append(('build', kwargs))
            builders._load_checkpoint(model, kwargs['checkpoint_path'])
            return model
        builders.build_sam3_image_model = build
        bundle = {'sam3_checkpoint': '/pinned/sam3.pt', 'bpe_vocabulary': '/pinned/bpe.gz'}
        processor = lambda model, **kwargs: SimpleNamespace(model=model, settings=kwargs)
        return calls, model, builders, bundle, processor, native_load

    def test_sam3_preserves_native_key_selection_records_extras_and_moves_cuda_index(self):
        calls, model, builders, bundle, processor, original = self.sam3_fixture(unexpected=['unused_weight'])
        result = _sam3_image_processor(bundle, SimpleNamespace(device='cuda:0'), builders, processor)
        self.assertIn(('load', {'detector_weight': 'unchanged'}, False), calls)
        self.assertIn(('move', {'device': 'cuda:0'}), calls)
        self.assertEqual(result.benchmark_checkpoint_loading['missing_keys'], [])
        self.assertEqual(result.benchmark_checkpoint_loading['unexpected_keys'], ['unused_weight'])
        self.assertEqual(result.benchmark_checkpoint_loading['calls'], 1)
        self.assertIs(builders._load_checkpoint, original)
        self.assertNotIn('load_state_dict', model.__dict__)
        self.assertEqual(result.settings, dict(resolution=1008, device='cuda:0', confidence_threshold=.5))
        settings = next(row[1] for row in calls if row[0] == 'build')
        self.assertFalse(settings['load_from_HF'])
        self.assertFalse(settings['enable_inst_interactivity'])
        self.assertFalse(settings['compile'])

    def test_sam3_missing_required_weight_stops_before_processor_and_restores_loader(self):
        calls, model, builders, bundle, processor, original = self.sam3_fixture(missing=['required_weight'])
        with self.assertRaisesRegex(BackendError, 'missing required keys: required_weight'):
            _sam3_image_processor(bundle, SimpleNamespace(device='cuda'), builders, processor)
        self.assertFalse(any(row[0] == 'move' for row in calls))
        self.assertIs(builders._load_checkpoint, original)
        self.assertNotIn('load_state_dict', model.__dict__)

    def test_sam3_unobserved_or_repeated_checkpoint_load_cannot_qualify(self):
        for load_calls in (0, 2):
            with self.subTest(load_calls=load_calls):
                _, model, builders, bundle, processor, original = self.sam3_fixture(load_calls=load_calls)
                with self.assertRaisesRegex(BackendError, 'not observed exactly once'):
                    _sam3_image_processor(bundle, SimpleNamespace(device='cuda'), builders, processor)
                self.assertIs(builders._load_checkpoint, original)
                self.assertNotIn('load_state_dict', model.__dict__)

    def test_sam3_serial_and_perflib_overrides_are_checked_without_fallback(self):
        native = SimpleNamespace(rank=0, world_size=1, detector=SimpleNamespace(rank=0, world_size=1))
        native.eval = lambda: native
        calls = []
        def build(**kwargs):
            calls.append(kwargs)
            return native
        perflib = SimpleNamespace(is_enabled=True)
        modules = {'sam3.model_builder': SimpleNamespace(build_sam3_video_model=build),
            'sam3.model.sam3_image_processor': SimpleNamespace(Sam3Processor=object),
            'sam3.perflib': perflib,
            'sam3.perflib.connected_components': SimpleNamespace(HAS_CC_TORCH=False),
            'sam3.perflib.nms': SimpleNamespace(GENERIC_NMS_AVAILABLE=False)}
        class Bundle:
            provenance = {}
            def __getitem__(self, name):
                return '/pinned/' + name
            def module(self, name, source):
                return modules[name]
        runtime = SimpleNamespace(torch=object(), device='cuda')
        backend = _build_native('S3', Bundle(), runtime)
        self.assertIs(backend.video_factory(), native)
        self.assertTrue(calls[0]['strict_state_dict_loading'])
        self.assertEqual(backend.provenance['cuda_nms'], 'bundled Triton')
        self.assertEqual(backend.provenance['cuda_connected_components'], 'bundled Triton')
        native.detector.world_size = 2
        with self.assertRaisesRegex(BackendError, 'serial allocation'):
            backend.video_factory()
        perflib.is_enabled = False
        with self.assertRaisesRegex(BackendError, 'inherited override'):
            _build_native('S3', Bundle(), runtime)

    def test_d1_native_constructor_only_uses_explicit_snapshot_and_bilinear(self):
        calls = []
        class Model:
            def to(self, **kwargs):
                calls.append(kwargs); return self
            def eval(self):
                return self
        model = Model()
        class Native:
            @classmethod
            def from_pretrained(cls, name, **kwargs):
                calls.append((name, kwargs)); return model
        class Bundle:
            provenance = {'assets_sha256': 'fake'}
            def __getitem__(self, name):
                return '/explicit/frozen/snapshot'
            def module(self, name, source):
                self.requested = (name, source)
                return SimpleNamespace(UniDepthV2=Native)
        bundle, runtime = Bundle(), FakeRuntime()
        runtime.torch = SimpleNamespace(float32=np.float32)
        backend = _build_native('D1', bundle, runtime)
        self.assertIs(backend.model, model)
        self.assertEqual(model.interpolation_mode, 'bilinear')
        self.assertEqual(calls[0], ('/explicit/frozen/snapshot', {'local_files_only': True}))
        self.assertFalse(hasattr(model, 'resolution_level'))

    def test_sam2_requires_native_extension_and_disables_build_compilation(self):
        calls = []
        def build(*args, **kwargs):
            calls.append((args, kwargs)); return object()
        class Bundle:
            provenance = {}
            def __getitem__(self, name):
                return '/explicit/sam2.1_hiera_large.pt'
            def module(self, name, source):
                calls.append(name)
                if name == 'sam2.build_sam':
                    return SimpleNamespace(build_sam2=build, build_sam2_video_predictor=build)
                if name == 'sam2._C':
                    return object()
                return SimpleNamespace(SAM2ImagePredictor=lambda model: model)
        _sam2(Bundle(), FakeRuntime(), detector([]), 'S4')
        self.assertIn('sam2._C', calls)
        build_calls = [c for c in calls if isinstance(c, tuple)]
        self.assertEqual(len(build_calls), 2)
        for args, kwargs in build_calls:
            self.assertEqual(args[0], 'configs/sam2.1/sam2.1_hiera_l.yaml')
            self.assertTrue(kwargs['apply_postprocessing'])
            self.assertIn('++model.compile_image_encoder=false', kwargs['hydra_overrides_extra'])
        self.assertFalse(build_calls[1][1]['vos_optimized'])

    def test_metric3d_hub_is_local_and_never_fetches_pretrained_URL(self):
        calls = []
        class Model:
            def load_state_dict(self, state, **kwargs):
                calls.append(('state', state, kwargs))
                return SimpleNamespace(missing_keys=[], unexpected_keys=[])
            def to(self, **kwargs):
                return self
            def eval(self):
                return self
        model = Model()
        def hub_load(*args, **kwargs):
            calls.append(('hub', args, kwargs)); return model
        class Bundle:
            provenance = {}
            def source(self, name):
                pass
            def __getitem__(self, name):
                return '/explicit/' + name
        runtime = FakeRuntime()
        runtime.torch = SimpleNamespace(float32=np.float32, hub=SimpleNamespace(load=hub_load),
            load=lambda *args, **kwargs: {'model_state_dict': 'exact checkpoint'})
        _build_native('D3', Bundle(), runtime)
        self.assertEqual(calls[0], ('hub', ('/explicit/metric3d_source', 'metric3d_vit_large'),
                                   {'source': 'local', 'pretrain': False}))
        self.assertEqual(calls[1][1], 'exact checkpoint')


if __name__ == '__main__':
    unittest.main()

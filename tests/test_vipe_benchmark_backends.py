"""Native API wiring tests with CPU arrays and fake models; no model imports."""
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace
import sys
import tempfile
import unittest

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from vipe_benchmark.backends import (
    AssetBundle, BackendError, DA3Backend, DepthProBackend, GroundingDetector,
    LegacyStandaloneBackend, LegacyViPESegmentationBackend, Metric3DBackend,
    RTDetrDetector, SAM2Backend, SAM3Backend, SOURCE_PINS, UniDepthBackend,
    build_backend, detection_rows, normalize_phrase,
    _build_native, _sam2, _legacy_vipe_segmentation,
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

    def test_source_frames_not_internal_indices_or_cross_role_context(self):
        backend, det, _ = self.make_backend()
        rgb, valid = image()
        for frames in ([20, 22], [49, 50], [199, 200], [21, 20]):
            with self.subTest(frames=frames), self.assertRaises(ValueError):
                backend.segment([rgb, rgb], [valid, valid], frame_ids=frames)
        self.assertEqual(det.calls, 0)


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
                self.encode_decode(inputs={'image': np.zeros((1, 3, 28, 42)), 'camera': K})
                values = np.full((1, 1, *valid.shape), 4., np.float32); values[..., 0, 0] = 0
                return dict(depth=values, confidence=np.ones_like(values))
        model = Model(); original = model.encode_decode
        result = UniDepthBackend('D1', model, FakeRuntime()).predict(rgb, self.K, valid)
        self.assertEqual(calls['pixels'].dtype, np.uint8)
        self.assertEqual(calls['pixels'].shape, (1, 3, 4, 6))
        np.testing.assert_allclose(calls['K'][0], self.K)
        self.assertEqual(result.metadata['actual_processed_shape'], [28, 42])
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

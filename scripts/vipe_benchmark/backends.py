"""Pinned native S0--S4 / D0--D4 adapters, loaded only inside admitted workers.

``build_backend(component, assets)`` accepts explicit local asset records. Files
have ``path`` and ``sha256``; source/snapshot directories additionally have a
``revision`` and a nonempty ``files`` list of verified file records. The caller
qualifies the runtime, revision checkout and complete dependency inventory, sets
the offline environment, and installs the standalone ViPE import/source guard
*before* calling this module's factory. No factory downloads assets.

An adapter returns arrays and native metadata; the worker owns immutable output
files, identities, RGB/config hashes, budget accounting and completion status.
Constructors accept native objects and a tensor runtime to allow CPU fake tests
without importing any model implementation or executing model inference.
"""
from contextlib import ExitStack, contextmanager, nullcontext
from dataclasses import dataclass, field
import importlib
import os
from pathlib import Path
import re
import sys
import tempfile
from unittest.mock import patch

import numpy as np

from . import contracts
from .files import object_hash, read_json, safe_path, verify_record


SOURCE_PINS = {
    'vipe_source': 'de50e6ab1066e32c96d32499a282ecaa2fbf2d90',
    'samtrack_source': '99ca4bd5074a6ed62db4664285073ab669503926',
    'aot_source': '601c138435a1764eb01404f3495b914e6e2e8eca',
    'sam_source': 'dca509fe793f601edb92606367a655c15ac00fdf',
    'grounding_source': '856dde20aee659246248e20734ef9ba5214f5e44',
    'sam2_source': '2b90b9f5ceec907a1c18123530e92e794ad901a4',
    'sam3_source': '660a5e9e1b8b4c02c0ad97229b88a09a6e4ff5b7',
    'unidepth_source': '8d8cfe4c7ee15297099983607febf0d4f32eb3d6',
    'da3_source': '3d835ec1a5802d64a8b8b15f817a1ab54809bfe4',
    'metric3d_source': 'eb5b6fac0dc155e4e52f576e304fbf11655ff339',
    'depth_pro_source': '9e65e4dbe9568d23c546fcec53302b10445e109e',
}
SNAPSHOT_PINS = {
    'rtdetr_snapshot': '282494075698cab9faa1096ae26856890030c817',
    'unidepth_snapshot': '52b349b514bd8b47642f67ac78cb7b5dc5c51dd9',
    'da3_snapshot': '4010e39f3634a45bc60553321fb49fb760bd594e',
}
REQUIRED_ASSETS = {
    'S0': ('vipe_source', 'sam_checkpoint', 'aot_checkpoint', 'grounding_checkpoint', 'bert_snapshot'),
    'S1': ('samtrack_source', 'aot_source', 'sam_source', 'grounding_source',
           'grounding_config', 'grounding_checkpoint', 'bert_snapshot', 'sam_checkpoint', 'aot_checkpoint'),
    'S2': ('grounding_source', 'grounding_config', 'grounding_checkpoint', 'bert_snapshot',
           'sam2_source', 'sam2_checkpoint'),
    'S3': ('sam3_source', 'sam3_checkpoint', 'bpe_vocabulary'),
    'S4': ('rtdetr_snapshot', 'sam2_source', 'sam2_checkpoint'),
    'D0': ('vipe_source', 'unidepth_snapshot'),
    'D1': ('unidepth_source', 'unidepth_snapshot'),
    'D2': ('da3_source', 'da3_snapshot'),
    'D3': ('metric3d_source', 'metric3d_checkpoint'),
    'D4': ('depth_pro_source', 'depth_pro_checkpoint'),
}
CHECKPOINT_NAMES = {
    'sam_checkpoint': 'sam_vit_b_01ec64.pth',
    'aot_checkpoint': 'R50_DeAOTL_PRE_YTB_DAV.pth',
    'grounding_checkpoint': 'groundingdino_swint_ogc.pth',
    'grounding_config': 'GroundingDINO_SwinT_OGC.py',
    'sam2_checkpoint': 'sam2.1_hiera_large.pt',
    'sam3_checkpoint': 'sam3.pt',
    'metric3d_checkpoint': 'metric_depth_vit_large_800k.pth',
    'depth_pro_checkpoint': 'depth_pro.pt',
}


class BackendError(RuntimeError):
    """A component is unusable; no sample may be marked complete."""


class AssetBundle:
    def __init__(self, component, records):
        if component not in REQUIRED_ASSETS:
            raise ValueError(f'unknown native component: {component}')
        missing = set(REQUIRED_ASSETS[component]) - set(records)
        if missing:
            raise BackendError(f'{component}: missing explicit local assets: {sorted(missing)}')
        self.records, self.paths = {}, {}
        for name in REQUIRED_ASSETS[component]:
            record = records[name]
            path = safe_path(record['path']).resolve()
            if name.endswith(('_source', '_snapshot')):
                if not path.is_dir() or not record.get('files'):
                    raise BackendError(f'{component}: {name} needs a local directory and file hashes')
                revision = record.get('revision', '')
                expected = SOURCE_PINS.get(name, SNAPSHOT_PINS.get(name))
                if not re.fullmatch('[0-9a-f]{40}', revision) or (expected and revision != expected):
                    raise BackendError(f'{component}: wrong or missing revision for {name}')
                listed = set()
                for item in record['files']:
                    item_path = safe_path(item['path']).absolute()
                    # HF snapshots commonly contain symlinks to adjacent blobs;
                    # lexical membership plus verified target bytes allows those.
                    if not item_path.is_relative_to(path):
                        raise BackendError(f'{name}: listed file is outside its declared directory')
                    verify_record(item)
                    listed.add(str(item_path.relative_to(path)))
                if name in SNAPSHOT_PINS and not {'config.json', 'model.safetensors'} <= listed:
                    raise BackendError(f'{name}: pinned config.json and model.safetensors required')
            else:
                verify_record(record)
                expected_name = CHECKPOINT_NAMES.get(name)
                if expected_name and safe_path(record['path']).name != expected_name:
                    raise BackendError(f'{component}: {name} must select {expected_name}')
            self.records[name] = record
            self.paths[name] = path
        self.provenance = dict(component=component, assets=self.records,
                               assets_sha256=object_hash(self.records))

    def __getitem__(self, name):
        return str(self.paths[name])

    def source(self, name):
        root = self.paths[name]
        for location in (root / 'src', root):
            if location.is_dir() and str(location) not in sys.path:
                sys.path.insert(0, str(location))
        return root

    def module(self, module_name, source_name):
        root = self.source(source_name)
        module = importlib.import_module(module_name)
        if not getattr(module, '__file__', None) or not safe_path(module.__file__).resolve().is_relative_to(root):
            raise BackendError(f'{module_name}: imported module does not belong to pinned {source_name}')
        return module


def _numpy(value):
    if hasattr(value, 'detach'):
        value = value.detach()
        if str(value.dtype) == 'torch.bfloat16':
            value = value.float()  # NumPy has no native bfloat16 dtype.
        value = value.cpu().numpy()
    return np.asarray(value)


def _plane(value, name='native depth'):
    array = _numpy(value)
    while array.ndim > 2 and array.shape[0] == 1:
        array = array[0]
    if array.ndim == 3 and array.shape[-1] == 1:
        array = array[..., 0]
    if array.ndim != 2:
        raise BackendError(f'{name}: expected one two-dimensional image, got {array.shape}')
    return array.astype(np.float32)


def _image(rgb, valid):
    if (not isinstance(valid, np.ndarray) or valid.ndim != 2 or not isinstance(rgb, np.ndarray)
            or rgb.dtype != np.uint8 or rgb.shape != (*valid.shape, 3)):
        raise ValueError('native adapters require byte HWC RGB on the supplied footprint grid')
    contracts.footprint(valid, valid.shape)


def _pair(images, valid, frame_ids):
    if len(images) not in (1, 2) or len(valid) != len(images) or len(frame_ids) != len(images):
        raise ValueError('one snapshot or exactly one two-frame pair is required')
    if any(type(i) is not int or not 0 <= i < 200 for i in frame_ids):
        raise ValueError('source frame IDs are required; final-window access is prohibited')
    if len(images) == 2 and frame_ids[1] != frame_ids[0] + 1:
        raise ValueError('tracker pair must contain adjacent source frames in chronological order')
    if len(images) == 2 and not 0 <= frame_ids[0] < frame_ids[1] <= 49:
        raise ValueError('two-frame tracking is restricted to the reconstruction role')
    for rgb, footprint in zip(images, valid):
        _image(rgb, footprint)
        if footprint.shape != valid[0].shape:
            raise ValueError('pair grids differ')


def _intrinsics(K):
    K = np.asarray(K, np.float64)
    if (K.shape != (3, 3) or not np.isfinite(K).all() or min(K[0, 0], K[1, 1]) <= 0
            or not np.allclose(K[2], [0, 0, 1], atol=1e-12, rtol=0)):
        raise ValueError('finite accepted pinhole K is required')
    return K


def normalize_phrase(phrase):
    normalized = ' '.join(str(phrase).lower().strip(' .').split())
    if normalized == 'person':
        return 'person'
    if normalized in ('basketball', 'sports ball'):
        return 'basketball'
    raise BackendError(f'unresolved native semantic phrase: {phrase!r}')


def detection_rows(boxes, scores, phrases):
    boxes, scores = np.asarray(boxes, np.float64), np.asarray(scores, np.float64)
    if boxes.size == 0:
        boxes = boxes.reshape(0, 4)
    if boxes.shape != (len(phrases), 4) or scores.shape != (len(phrases),):
        raise BackendError('native detection boxes/scores/phrases differ in length')
    if len(boxes) > 255:
        raise BackendError('255-object capacity exceeded before native integer casting')
    if not np.isfinite(boxes).all() or not np.isfinite(scores).all() or np.any(boxes[:, 2:] <= boxes[:, :2]):
        raise BackendError('native detector returned nonfinite or degenerate evidence')
    return [dict(id=i + 1, index=i, box=box.tolist(), score=float(score),
                 native_class=str(phrase), **{'class': normalize_phrase(phrase)})
            for i, (box, score, phrase) in enumerate(zip(boxes, scores, phrases))]


@dataclass
class SegmentationResult:
    labels: np.ndarray
    semantics: dict
    valid: np.ndarray
    metadata: dict
    diagnostics: dict = field(default_factory=dict)

    def __post_init__(self):
        contracts.instances(self.labels, self.semantics, self.valid, self.valid.shape)

    def static(self, changing):
        return contracts.static_mask(self.labels, self.semantics, changing, self.valid, self.valid.shape)


@dataclass
class DepthResult:
    depth: np.ndarray
    valid: np.ndarray
    confidence: np.ndarray | None
    raw_depth: np.ndarray
    metadata: dict


def _segmentation(labels, semantics, valid, metadata):
    raw = _numpy(labels)
    if raw.shape != valid.shape or not np.isfinite(raw).all() or not np.equal(raw, np.floor(raw)).all():
        raise BackendError('native labels must be finite integers on the original image grid')
    if np.any(raw < 0) or np.any(raw > 255):
        raise BackendError('native ID range violation; refusing lossy integer casting')
    labels = raw.astype(np.int32)
    labels[~valid] = -1
    ids = {str(i) for i in np.unique(labels) if i > 0}
    if not ids <= semantics.keys():
        raise BackendError('native tracker produced IDs without semantic evidence')
    return SegmentationResult(labels, {i: semantics[i].copy() for i in sorted(ids)}, valid.copy(), metadata)


def _finish_depth(values, image_valid, raw, metadata, confidence=None):
    values = _plane(values)
    if values.shape != image_valid.shape:
        raise BackendError('native metric depth was not restored to the original image grid')
    valid = image_valid & np.isfinite(values) & (values > 0)
    values[~valid] = np.nan
    if confidence is not None:
        confidence = _plane(confidence, 'native confidence')
        if confidence.shape != values.shape:
            raise BackendError('confidence grid was not restored with depth')
        confidence[~valid] = np.nan
    contracts.depth(values, valid, image_valid, confidence, image_valid.shape)
    return DepthResult(values, valid, confidence, _plane(raw), metadata)


class TorchRuntime:
    def __init__(self, torch, device):
        self.torch, self.device = torch, device

    def tensor(self, value, dtype='float32'):
        array = np.array(value, copy=True)
        return self.torch.from_numpy(array).to(device=self.device, dtype=getattr(self.torch, dtype))

    @contextmanager
    def inference(self, precision='float32'):
        with self.torch.inference_mode():
            with self.torch.autocast(device_type='cuda', dtype=self.torch.bfloat16,
                                     enabled=precision == 'bfloat16'):
                yield

    def resize(self, array, shape):
        tensor = self.tensor(array)[None, None]
        return _plane(self.torch.nn.functional.interpolate(
            tensor, size=shape, mode='bilinear', align_corners=False))


def _resize_valid(runtime, values, shape):
    """Native bilinear half-pixel restore, excluding any invalid contributor."""
    values = _plane(values)
    if values.shape == tuple(shape):
        return values.copy()
    good = np.isfinite(values) & (values > 0)
    restored = runtime.resize(np.where(good, values, 0).astype(np.float32), shape)
    invalid_weight = runtime.resize((~good).astype(np.float32), shape)
    restored[invalid_weight > 0] = np.nan
    return restored


@contextmanager
def _capture_method(obj, name, observer):
    """Observe one native call without changing its arguments or return value."""
    original = getattr(obj, name)
    def wrapped(*args, **kwargs):
        output = original(*args, **kwargs)
        observer(args, kwargs, output)
        return output
    with patch.object(obj, name, wrapped):
        yield


@contextmanager
def lossless_pair_files(images):
    """SAM 2 discovers JPG names but PIL decodes the lossless PNG payload."""
    from PIL import Image
    with tempfile.TemporaryDirectory(prefix='vipe-benchmark-pair-') as folder:
        for i, rgb in enumerate(images):
            Image.fromarray(rgb).save(Path(folder) / f'{i:05d}.jpg', format='PNG')
        yield folder


class GroundingDetector:
    def __init__(self, model, transform, predict, runtime, text_threshold):
        self.model, self.transform, self.native_predict = model, transform, predict
        self.runtime, self.text_threshold = runtime, text_threshold
        self.diagnostics = {}
        self.metadata = dict(processor='native PIL RandomResize([800], max_size=1333), ImageNet',
                             caption='person.basketball.', box_threshold=.35, text_threshold=text_threshold,
                             invocation_precision='float32')

    def __call__(self, rgb):
        from PIL import Image
        image, _ = self.transform(Image.fromarray(rgb), None)
        captured = {}
        def observe(_args, _kwargs, output):
            captured['detector_raw_token_logits'] = _numpy(output['pred_logits'])[0].copy()
            captured['detector_raw_boxes_cxcywh'] = _numpy(output['pred_boxes'])[0].copy()
        with _capture_method(self.model, 'forward', observe), self.runtime.inference():
            boxes, scores, phrases = self.native_predict(
                self.model, image, 'person.basketball.', .35, self.text_threshold,
                device=self.runtime.device)
        boxes = _numpy(boxes).astype(np.float64).reshape(-1, 4)
        h, w = rgb.shape[:2]
        boxes *= [w, h, w, h]
        center, size = boxes[:, :2].copy(), boxes[:, 2:].copy()
        boxes = np.concatenate((center - size / 2, center + size / 2), axis=1)
        self.metadata['actual_processed_shape'] = list(image.shape[-2:])
        self.diagnostics = dict(captured, detector_rgb=_numpy(image).copy(),
            detector_selected_boxes_xyxy=boxes.copy(), detector_selected_scores=_numpy(scores).reshape(-1).copy())
        return detection_rows(boxes, _numpy(scores).reshape(-1), phrases)


class RTDetrDetector:
    def __init__(self, processor, model, runtime):
        self.processor, self.model, self.runtime = processor, model, runtime
        self.metadata = dict(processor='RTDetrImageProcessor', size=[640, 640], rescale_factor=1 / 255,
                             do_normalize=False, threshold=.35, invocation_precision='float32')

    def __call__(self, rgb):
        inputs = self.processor(images=rgb, return_tensors='pt', do_resize=True,
                                size={'height': 640, 'width': 640}, do_rescale=True,
                                rescale_factor=1 / 255, do_normalize=False)
        inputs = {k: v.to(self.runtime.device) for k, v in inputs.items()}
        with self.runtime.inference():
            output = self.model(**inputs)
        # Native postprocessing uses > threshold; use zero here and implement
        # the preregistered >= .35 comparison explicitly, including its equality.
        result = self.processor.post_process_object_detection(
            output, target_sizes=self.runtime.tensor([rgb.shape[:2]], 'int64'), threshold=0.)[0]
        boxes, scores, labels = _numpy(result['boxes']), _numpy(result['scores']), _numpy(result['labels'])
        names = self.model.config.id2label
        selected = []
        for i, (box, score, label) in enumerate(zip(boxes, scores, labels)):
            native = names.get(int(label), names.get(str(int(label))))
            if native in ('person', 'sports ball') and float(score) >= .35:
                selected.append((i, box, score, native))
        rows = detection_rows([r[1] for r in selected], [r[2] for r in selected], [r[3] for r in selected])
        for row, item in zip(rows, selected):
            row['index'] = item[0]
        return rows


class SAM2Backend:
    def __init__(self, component, detector, image_predictor, video_predictor, runtime, provenance=None):
        self.component, self.detector = component, detector
        self.image_predictor, self.video_predictor = image_predictor, video_predictor
        self.runtime, self.provenance = runtime, provenance or {}

    def segment(self, images, valid, *, frame_ids):
        _pair(images, valid, frame_ids)
        detections = self.detector(images[0])
        shape = valid[0].shape
        metadata = dict(self.provenance, component=self.component, frame_ids=list(frame_ids),
            detector=self.detector.metadata.copy(), sam_config='configs/sam2.1/sam2.1_hiera_l.yaml',
            sam_input_shape=[1024, 1024], precision='bfloat16', compilation=False,
            pair_reset=True, successor_detector_rerun=False,
            keyframe_mask_choice='highest predicted IoU; first index on exact tie',
            postprocessing=dict(dynamic_multimask_via_stability=True, stability_delta=.05,
                stability_threshold=.98, video_fill_hole_area=8, binarize_mask_from_points_for_memory=True),
            pair_transport='PNG payload in native JPG-discovered temporary files; no lossy encoding')
        if not detections:
            return [_segmentation(np.zeros(shape, np.int32), {}, footprint,
                    dict(metadata, frame_id=f, detections=[], suppressed=[]))
                    for footprint, f in zip(valid, frame_ids)]
        logits, mask_scores = [], []
        with self.runtime.inference('bfloat16'):
            self.image_predictor.set_image(images[0])
            for d in detections:
                candidates, scores, _ = self.image_predictor.predict(
                    box=np.array(d['box'], np.float32), multimask_output=True, return_logits=True)
                candidates, scores = _numpy(candidates), _numpy(scores).reshape(-1)
                if candidates.shape != (len(scores), *shape) or not np.isfinite(scores).all():
                    raise BackendError('SAM 2 image logits/IoU scores have an unexpected grid')
                choice = int(np.argmax(scores))
                logits.append(candidates[choice]); mask_scores.append(float(scores[choice]))
        all_logits = [np.asarray(logits, np.float32)]
        if len(images) == 2:
            with lossless_pair_files(images) as folder, self.runtime.inference('bfloat16'):
                state = self.video_predictor.init_state(video_path=folder, async_loading_frames=False)
                try:
                    for d, logit in zip(detections, logits):
                        # The selected original-grid keyframe mask initializes
                        # the native tracker. Merge happens only at export.
                        self.video_predictor.add_new_mask(state, frame_idx=0, obj_id=d['id'], mask=logit > 0)
                    successor = None
                    for internal, ids, output in self.video_predictor.propagate_in_video(
                            state, start_frame_idx=0, max_frame_num_to_track=1, reverse=False):
                        if internal not in (0, 1):
                            raise BackendError('SAM 2 propagated outside the admitted pair')
                        if internal == 1:
                            ids = [int(i) for i in ids]
                            values = _numpy(output)
                            if values.ndim == 4 and values.shape[1] == 1:
                                values = values[:, 0]
                            if len(set(ids)) != len(ids) or set(ids) != {d['id'] for d in detections}:
                                raise BackendError('SAM 2 lost or invented object IDs during pair propagation')
                            successor = np.asarray([values[ids.index(d['id'])] for d in detections], np.float32)
                    if successor is None:
                        raise BackendError('SAM 2 did not return the successor frame')
                    all_logits.append(successor)
                finally:
                    self.video_predictor.reset_state(state)
        results = []
        for f, footprint, values in zip(frame_ids, valid, all_logits):
            labels, semantics, suppressed = contracts.merge_logits(values, detections, footprint)
            results.append(SegmentationResult(labels, semantics, footprint.copy(),
                dict(metadata, frame_id=f, detections=detections, mask_iou_scores=mask_scores, suppressed=suppressed)))
        return results


class S1TrackerBridge:
    """Bridge the pinned SAM-Track wrapper to AOT for one reset pair only."""
    def __init__(self, native, runtime, config_directory):
        self._native, self.runtime = native, runtime
        self._config_directory = config_directory  # Keep native config directories alive.
        self._active = False
        self.metadata = dict(
            engine_argument_bridge=dict(removed={'max_len_long_term': 9999},
                engine='deaotengine', phase='eval', long_term_mem_gap=9999, short_term_mem_skip=1,
                reason='memory truncation unreachable after reset and at most one successor'),
            contract=dict(maximum_frames=2, one_reference_at_step=0, resets_per_group=2),
            memory_grid_bridge=dict(mode='nearest', target='native engine.input_size_2d'),
            numpy_import_state_restored=True,
            config_working_directory=str(Path(config_directory.name).absolute()))

    @contextmanager
    def pair(self, frame_ids):
        ids = list(frame_ids)
        if (self._active or len(ids) not in (1, 2) or
                any(type(i) is not int or not 0 <= i < 200 for i in ids) or
                (len(ids) == 2 and (ids[1] != ids[0] + 1 or ids[1] > 49))):
            raise BackendError('S1 AOT bridge requires a fresh singleton or one reconstruction pair')
        self._active, self._frames, self._resets = True, len(ids), 0
        self._state, self._referenced, self._updated = 'new', False, False
        self.metadata['memory_update'] = None
        try:
            yield
            if self._resets != 2 or self._referenced != self._updated:
                raise BackendError('S1 AOT bridge requires both resets and one update per reference')
        finally:
            self._active = False

    def restart(self):
        if not self._active or self._resets >= 2:
            raise BackendError('S1 AOT reset is outside its admitted pair')
        self._native.restart()
        self._resets += 1
        self._state = 'ready' if self._resets == 1 else 'closed'

    def add_reference_frame(self, image, mask, obj_nums, frame_step, incremental=False):
        if (not self._active or self._frames != 2 or self._state != 'ready' or
                type(frame_step) is not int or frame_step != 0 or incremental or
                type(obj_nums) is not int or not 1 <= obj_nums <= 255):
            raise BackendError('S1 AOT bridge permits one reference at step zero after reset')
        self._native.add_reference_frame(image, mask, obj_nums, frame_step)
        self._original_shape = tuple(image.shape[:2])
        self._state, self._referenced = 'referenced', True

    def track(self, image):
        if (not self._active or self._state != 'referenced' or
                tuple(image.shape[:2]) != self._original_shape):
            raise BackendError('S1 AOT bridge permits exactly one successor on the reference grid')
        result = self._native.track(image)
        self._state = 'tracked'
        return result

    def update_memory(self, labels):
        if not self._active or self._state != 'tracked':
            raise BackendError('S1 AOT memory update requires its single tracked successor')
        if tuple(labels.shape) != (1, 1, *self._original_shape):
            raise BackendError('S1 AOT returned labels outside the original image grid')
        shape = tuple(self._native.engine.input_size_2d)
        if len(shape) != 2 or any(type(i) is not int or i <= 0 for i in shape):
            raise BackendError('S1 AOT engine has an invalid internal image grid')
        resized = self.runtime.torch.nn.functional.interpolate(labels, size=shape, mode='nearest')
        self._native.update_memory(resized)
        self.metadata['memory_update'] = dict(original_shape=list(labels.shape[-2:]),
                                             internal_shape=list(shape), mode='nearest')
        self._state, self._updated = 'updated', True


def _s1_aot_module(bundle):
    # Its palette initialization seeds NumPy to 200 as an import side effect.
    state = np.random.get_state()
    try:
        return bundle.module('aot_tracker', 'samtrack_source')
    finally:
        np.random.set_state(state)


def _s1_tracker(aot_module, runtime, arguments):
    prescribed = dict(phase='PRE_YTB_DAV', model='r50_deaotl', long_term_mem_gap=9999,
                      max_len_long_term=9999, gpu_id=0)
    if (set(arguments) != set(prescribed) | {'model_path'} or
            any(arguments.get(k) != v for k, v in prescribed.items()) or
            any(type(arguments[k]) is not int for k in ('long_term_mem_gap', 'max_len_long_term', 'gpu_id')) or
            not Path(arguments['model_path']).is_absolute()):
        raise BackendError('S1 AOT engine bridge requires the exact frozen tracker settings')
    temporary_root = os.environ.get('TMPDIR')
    if not temporary_root or not safe_path(temporary_root).is_dir():
        raise BackendError('S1 AOT construction requires the supervised job TMPDIR')
    original_builder = aot_module.build_engine
    builder_calls = 0
    def build_engine(name, phase='train', **kwargs):
        nonlocal builder_calls
        required = dict(gpu_id=0, short_term_mem_skip=1, long_term_mem_gap=9999, max_len_long_term=9999)
        if (builder_calls or name != 'deaotengine' or phase != 'eval' or
                set(kwargs) != set(required) | {'aot_model'} or
                any(type(kwargs[k]) is not int or kwargs[k] != v for k, v in required.items())):
            raise BackendError('S1 AOT wrapper changed its frozen engine constructor contract')
        builder_calls += 1
        del kwargs['max_len_long_term']
        return original_builder(name, phase=phase, **kwargs)
    directory = tempfile.TemporaryDirectory(prefix='s1-aot-config-', dir=Path(temporary_root).resolve())
    previous = Path.cwd()
    try:
        os.chdir(directory.name)
        with patch.object(aot_module, 'build_engine', build_engine):
            native = aot_module.get_aot(dict(arguments))
        if builder_calls != 1:
            raise BackendError('S1 AOT wrapper did not construct exactly one native engine')
        return S1TrackerBridge(native, runtime, directory)
    except BaseException:
        directory.cleanup()
        raise
    finally:
        os.chdir(previous)


class LegacyStandaloneBackend:
    """Native upstream detector + SAM box refinement + DeAOT, SegTracker merge."""
    def __init__(self, detector, sam_predictor, tracker, runtime, provenance=None):
        self.detector, self.sam, self.tracker = detector, sam_predictor, tracker
        self.runtime, self.provenance = runtime, provenance or {}

    def segment(self, images, valid, *, frame_ids):
        _pair(images, valid, frame_ids)
        rows = self.detector(images[0])
        labels = np.zeros(valid[0].shape, np.int32)
        semantics, skipped = {}, []
        h, w = labels.shape
        pair_scope = self.tracker.pair(frame_ids) if isinstance(self.tracker, S1TrackerBridge) else nullcontext()
        with self.runtime.inference(), pair_scope:
            self.tracker.restart()
            try:
                object_id = 0
                for d in rows:
                    # Upstream Detector.transfer_boxes_format truncates to int.
                    box = np.asarray(d['box']).astype(np.int64)
                    if (box[2] - box[0]) * (box[3] - box[1]) > h * w:
                        skipped.append(d['index']); continue
                    object_id += 1
                    if object_id > 255:
                        raise BackendError('255-object capacity exceeded before SAM-Track merge')
                    self.sam.set_image(images[0])  # historical reset_image=True
                    masks, scores, logits = self.sam.predict(
                        point_coords=None, point_labels=None, box=box, multimask_output=True)
                    scores = _numpy(scores).reshape(-1)
                    if not len(scores) or not np.isfinite(scores).all():
                        raise BackendError('SAM-B returned invalid mask IoU scores')
                    selected = int(np.argmax(scores))
                    masks, scores, _ = self.sam.predict(point_coords=None, point_labels=None,
                        box=box[None], mask_input=_numpy(logits)[selected][None], multimask_output=True)
                    scores = _numpy(scores).reshape(-1)
                    if not len(scores) or not np.isfinite(scores).all():
                        raise BackendError('SAM-B returned invalid refined mask IoU scores')
                    mask = _numpy(masks)[int(np.argmax(scores))]
                    if mask.shape != labels.shape:
                        raise BackendError('SAM-B mask grid changed')
                    labels[mask > 0] = object_id  # native later masks overwrite
                    semantics[str(object_id)] = dict(d, id=object_id, box=box.tolist())
                outputs = [labels.copy()]
                if len(images) == 2:
                    if labels.any():
                        self.tracker.add_reference_frame(images[0], labels.astype(np.uint8),
                                                         int(labels.max()), 0)
                        native = self.tracker.track(images[1])
                        self.tracker.update_memory(native)
                        outputs.append(_plane(native, 'DeAOT labels'))
                    else:
                        outputs.append(labels.copy())
            finally:
                self.tracker.restart()
        metadata = dict(self.provenance, component='S1', detector=self.detector.metadata.copy(),
            precision='float32', pair_reset=True, frame_ids=list(frame_ids), sam_gap=10,
            min_area=200, automatic_min_mask_region_area=200, first_box_masks_area_filtered=False,
            merge='upstream SegTracker: later box masks overwrite earlier masks',
            sam_box_refinement_passes=2, skipped_box_indices=skipped,
            detections=rows, diagnostics_source_frame=frame_ids[0],
            successor_detector_rerun=False, empty_keyframe='empty successor; native zero-object tracker skipped')
        if isinstance(self.tracker, S1TrackerBridge):
            metadata['tracker_bridge'] = self.tracker.metadata.copy()
        results = [_segmentation(output, semantics, footprint, dict(metadata, frame_id=f))
                   for output, footprint, f in zip(outputs, valid, frame_ids)]
        results[0].diagnostics = getattr(self.detector, 'diagnostics', {}).copy()
        return results


def merge_sam3(masks, scores, native_ids, semantic, mapping, valid):
    """Return merge candidates; (semantic, native ID) is the session namespace."""
    masks, scores, native_ids = _numpy(masks), _numpy(scores).reshape(-1), _numpy(native_ids).reshape(-1)
    if masks.ndim == 4 and masks.shape[1] == 1:
        masks = masks[:, 0]
    if masks.shape != (len(scores), *valid.shape) or len(native_ids) != len(scores):
        raise BackendError('SAM 3 mask/score/ID shapes differ from the original grid')
    if len(native_ids) > 255:
        raise BackendError('255-object native SAM 3 capacity exceeded')
    if not np.isfinite(scores).all() or not np.isfinite(native_ids).all():
        raise BackendError('SAM 3 returned nonfinite scores or IDs')
    if len(set(native_ids.tolist())) != len(native_ids) or not np.equal(native_ids, np.floor(native_ids)).all():
        raise BackendError('SAM 3 returned duplicate or fractional native IDs')
    rows = []
    for i in np.argsort(native_ids, kind='stable'):
        mask, score, native_id = masks[i], scores[i], native_ids[i]
        if mask.dtype != np.bool_:
            # A binary output is required here; these are not raw logits.
            if not np.isin(mask, [0, 1]).all():
                raise BackendError('SAM 3 did not return binary original-grid masks')
        if score < .5:
            continue
        key = (semantic, int(native_id))
        if key not in mapping:
            mapping[key] = len(mapping) + 1
        if mapping[key] > 255:
            raise BackendError('255-object capacity exceeded across SAM 3 concept sessions')
        rows.append((mask.astype(bool), dict(id=mapping[key], native_id=int(native_id),
                     native_class=semantic, score=float(score), **{'class': semantic})))
    return rows


def _sam3_frame(rows, valid, metadata):
    labels = np.zeros(valid.shape, np.int32)
    # Higher returned instance score wins; semantic and native ID settle ties.
    ordered = sorted(rows, key=lambda r: (-r[1]['score'], r[1]['class'], r[1]['native_id']))
    for mask, data in ordered:
        take = valid & mask & (labels == 0)
        labels[take] = data['id']
    suppressed = [dict(id=data['id'], pixels=int((valid & mask & (labels != data['id'])).sum()))
                  for mask, data in rows]
    semantics = {str(data['id']): data for _, data in rows}
    return _segmentation(labels, semantics, valid, dict(metadata, suppressed=suppressed))


class SAM3Backend:
    def __init__(self, image_factory, video_factory, runtime, provenance=None):
        self.image_factory, self.video_factory = image_factory, video_factory
        self.runtime, self.provenance = runtime, provenance or {}
        self.image_processor, self.video_model = None, None

    def segment(self, images, valid, *, frame_ids):
        from PIL import Image
        _pair(images, valid, frame_ids)
        metadata = dict(self.provenance, component='S3', frame_ids=list(frame_ids),
            concepts=['person', 'basketball'], confidence_threshold=.5,
            image_size=[1008, 1008], precision='bfloat16', compilation=False,
            builder='original SAM 3 image/video; no multiplex',
            pair_reset=True, merge='returned score, semantic name, native ID',
            native_video_births=True, video_storage_precision='float16 in native PIL resource loader')
        mapping, rows_by_frame, native_sets = {}, [[] for _ in images], []
        with self.runtime.inference('bfloat16'):
            if len(images) == 1:
                if self.image_processor is None:
                    self.image_processor = self.image_factory()
                for semantic in ('person', 'basketball'):
                    state = self.image_processor.set_image(Image.fromarray(images[0]))
                    output = self.image_processor.set_text_prompt(prompt=semantic, state=state)
                    scores = _numpy(output['scores']).reshape(-1)
                    rows_by_frame[0].extend(merge_sam3(output['masks'], scores, np.arange(len(scores)),
                                                    semantic, mapping, valid[0]))
            else:
                if self.video_model is None:
                    self.video_model = self.video_factory()
                model = self.video_model
                for semantic in ('person', 'basketball'):
                    # Each native semantic prompt resets the model state. Separate
                    # states make that behavior explicit and keep both results.
                    state = model.init_state(resource_path=[Image.fromarray(im) for im in images],
                        offload_video_to_cpu=False, offload_state_to_cpu=False, async_loading_frames=False)
                    seen, local_sets = set(), []
                    try:
                        model.add_prompt(state, frame_idx=0, text_str=semantic)
                        for internal, output in model.propagate_in_video(
                                state, start_frame_idx=0, max_frame_num_to_track=1, reverse=False):
                            if internal not in (0, 1) or internal in seen:
                                raise BackendError('SAM 3 returned duplicate or out-of-pair frames')
                            seen.add(internal)
                            rows = merge_sam3(output['out_binary_masks'], output['out_probs'],
                                             output['out_obj_ids'], semantic, mapping, valid[internal])
                            rows_by_frame[internal].extend(rows)
                            local_sets.append((internal, {r[1]['id'] for r in rows}))
                        if seen != {0, 1}:
                            raise BackendError('SAM 3 did not return both pair frames')
                        native_sets.append(dict(concept=semantic, frame_ids={i: sorted(ids) for i, ids in local_sets}))
                    finally:
                        model.reset_state(state)
        first = {r[1]['id'] for r in rows_by_frame[0]}
        second = {r[1]['id'] for r in rows_by_frame[-1]}
        metadata.update(births=sorted(second - first), disappearances=sorted(first - second),
                        native_concept_ids=native_sets,
                        id_mapping=[dict(semantic=k[0], native_id=k[1], id=v) for k, v in sorted(mapping.items())])
        return [_sam3_frame(rows, footprint, dict(metadata, frame_id=f))
                for rows, footprint, f in zip(rows_by_frame, valid, frame_ids)]


class LegacyViPESegmentationBackend:
    def __init__(self, factory, video_frame, runtime, provenance=None):
        self.factory, self.video_frame, self.runtime = factory, video_frame, runtime
        self.provenance = provenance or {}

    def segment(self, images, valid, *, frame_ids):
        _pair(images, valid, frame_ids)
        tracker = self.factory()  # fresh per snapshot/pair; factory shares only weights
        captured, diagnostics = [], {}
        def detector_output(_module, _inputs, output):
            logits = _numpy(output['pred_logits'].sigmoid())[0]
            boxes = _numpy(output['pred_boxes'])[0]
            scores = logits.max(axis=1)
            captured[:] = [float(v) for v in scores[scores > .35]]
            diagnostics.update(detector_rgb=_numpy(_inputs[0])[0].copy(),
                detector_raw_token_logits=_numpy(output['pred_logits'])[0].copy(),
                detector_raw_boxes_cxcywh=boxes.copy())
        def selected_output(_args, _kwargs, output):
            (height, width), native_boxes, _phrases = output
            boxes = _numpy(native_boxes)
            if boxes.shape != (len(captured), 4):
                raise BackendError('S0 native box/score association changed')
            kept = (boxes[:, 2] - boxes[:, 0]) * (boxes[:, 3] - boxes[:, 1]) <= height * width
            if int(kept.sum()) > 255:
                raise BackendError('S0 exceeds 255 IDs before the historical uint8 merge')
            captured[:] = np.asarray(captured)[kept].tolist()
            diagnostics.update(detector_returned_boxes_xyxy=boxes.copy(),
                detector_selected_boxes_xyxy=boxes[kept].copy(),
                detector_selected_scores=np.asarray(captured, np.float32))
        handle = tracker.segtracker.detector.gd.register_forward_hook(detector_output)
        results = []
        try:
            with _capture_method(tracker.segtracker.detector, 'run_grounding_tensor', selected_output), self.runtime.inference():
                for rgb, footprint, frame_id in zip(images, valid, frame_ids):
                    frame = self.video_frame(raw_frame_idx=frame_id,
                        rgb=self.runtime.tensor(rgb.astype(np.float32) / 255))
                    labels, phrases = tracker.track(frame)
                    semantics = {}
                    for native_id, phrase in phrases.items():
                        native_id = int(native_id)
                        if native_id == 0:
                            continue
                        if native_id > len(captured):
                            raise BackendError('S0 detector-score/instance association could not be established')
                        semantics[str(native_id)] = dict(id=native_id, native_class=phrase,
                            score=captured[native_id - 1], **{'class': normalize_phrase(phrase)})
                    metadata = dict(self.provenance, component='S0', frame_id=frame_id,
                        frame_ids=list(frame_ids), precision='float32', pair_reset=True,
                        detector_score='native max token sigmoid before fork phrase assignment',
                        detector_boxes='captured native float32 XYXY return; native area eligibility before merge',
                        detector_preprocess='fork tensor bilinear, antialias=True, ImageNet, 800/max1333',
                        phrase_policy='native best phrase from token logits; nominal text=.5 unused',
                        merge='unchanged ViPE SegTracker native overlap order',
                        successor_detector_rerun=False, native_instance_scores=captured.copy(),
                        native_phrases={str(k): v for k, v in getattr(tracker, 'instance_phrase', phrases).items()},
                        actual_processed_shape=list(diagnostics['detector_rgb'].shape[-2:]),
                        diagnostics_source_frame=frame_ids[0])
                    results.append(_segmentation(labels, semantics, footprint, metadata))
        finally:
            handle.remove()
            del tracker
        results[0].diagnostics = diagnostics
        return results


class UniDepthBackend:
    def __init__(self, component, model, runtime, provenance=None, legacy_input=None):
        self.component, self.model, self.runtime = component, model, runtime
        self.provenance, self.legacy_input = provenance or {}, legacy_input

    def predict(self, rgb, K, valid):
        _image(rgb, valid); K = _intrinsics(K)
        native = self.model.model if self.component == 'D0' else self.model
        processing = {}
        def observe(args, kwargs, _output):
            inputs = kwargs.get('inputs', args[0] if args else None)
            processing['actual_processed_shape'] = list(inputs['image'].shape[-2:])
            processing['native_processed_rgb_dtype'] = str(inputs['image'].dtype)
        with _capture_method(native, 'encode_decode', observe), self.runtime.inference():
            if self.component == 'D0':
                output = self.model.estimate(self.legacy_input(
                    rgb=self.runtime.tensor(rgb.astype(np.float32) / 255),
                    intrinsics=self.runtime.tensor([K[0, 0], K[1, 1], K[0, 2], K[1, 2]])))
                raw, confidence = _plane(output.metric_depth), _plane(output.confidence)
            else:
                output = native.infer(self.runtime.tensor(rgb.transpose(2, 0, 1)[None], 'uint8'),
                                      self.runtime.tensor(K[None]))
                raw, confidence = _plane(output['depth']), _plane(output['confidence'])
        if 'actual_processed_shape' not in processing:
            raise BackendError('UniDepth native processing dimensions were not observed')
        converted, _, conversion = contracts.metric_depth(raw, self.component, already_metric=True)
        h, w = valid.shape
        native_K = np.array([[K[0, 0], 0, w / 2], [0, K[0, 0], h / 2], [0, 0, 1]])
        metadata = dict(self.provenance, **processing, **conversion, component=self.component,
            input_K=K.tolist(), native_input_K=(native_K if self.component == 'D0' else K).tolist(),
            invocation_precision='float32', interpolation='bilinear',
            native_autocast=('upstream infer float16 decorator' if self.component == 'D1' else
                             'historical fork infer float16 decorator'),
            resolution_policy='checkpoint default bounds; no resolution_level override',
            depth_type='camera-z metres', grid_restore='native camera-aware infer postprocess',
            confidence=dict(meaning='native within-image relative confidence', direction='higher is more confident',
                            calibration='uncalibrated; never used to filter scale support'))
        return _finish_depth(converted, valid, raw, metadata, confidence)


class DA3Backend:
    def __init__(self, model, runtime, provenance=None):
        self.model, self.runtime, self.provenance = model, runtime, provenance or {}

    def predict(self, rgb, K, valid):
        _image(rgb, valid); K = _intrinsics(K)
        processed, exts, intrinsics = self.model.input_processor(
            [rgb], extrinsics=None, intrinsics=K[None].copy(), process_res=504,
            process_res_method='upper_bound_resize', num_workers=1, sequential=True)
        if exts is not None or intrinsics is None:
            raise BackendError('DA3 processor did not preserve the no-extrinsics/supplied-K contract')
        processed_K = _numpy(intrinsics)
        if processed_K.shape != (1, 3, 3):
            raise BackendError('DA3 input processor returned unexpected intrinsics')
        processed_K = _intrinsics(processed_K[0])
        shape = tuple(processed.shape[-2:])
        images_t, exts_t, K_t = self.model._prepare_model_inputs(processed, None, intrinsics)
        if exts_t is not None:
            raise BackendError('DA3 unexpectedly constructed extrinsics')
        with self.runtime.inference('bfloat16'):
            raw_output = self.model.forward(images_t, extrinsics=None, intrinsics=K_t,
                export_feat_layers=[], infer_gs=False, use_ray_pose=False, ref_view_strategy='saddle_balanced')
        prediction = self.model.output_processor(raw_output)
        if bool(getattr(prediction, 'is_metric', False)):
            raise BackendError('DA3 output reports already-metric depth; canonical scaling would be ambiguous')
        raw = _plane(prediction.depth)
        if raw.shape != shape:
            raise BackendError('DA3 canonical output grid differs from its input processor')
        values, _, conversion = contracts.metric_depth(raw, 'D2', processed_K=processed_K)
        restored = _resize_valid(self.runtime, values, valid.shape)
        confidence = getattr(prediction, 'conf', None)
        if confidence is not None:
            confidence = self.runtime.resize(_plane(confidence), valid.shape)
        metadata = dict(self.provenance, **conversion, component='D2', process_res=504,
            process_res_method='upper_bound_resize', native_processed_K=processed_K.tolist(),
            actual_processed_shape=list(shape), input_K=K.tolist(), precision='bfloat16',
            native_K_convention='processor scales fx,cx by width ratio and fy,cy by height ratio; no extra half-pixel correction',
            normalization='native ImageNet', input_extrinsics=None, pose_scale_alignment=False,
            infer_gs=False, export=False, depth_type='camera-z metres',
            grid_restore='validity-aware bilinear, align_corners=False',
            confidence=None if confidence is None else dict(meaning='native depth_conf', direction='higher is more confident',
                calibration='uncalibrated; never used to filter scale support'))
        return _finish_depth(restored, valid, raw, metadata, confidence)


class Metric3DBackend:
    def __init__(self, model, runtime, provenance=None):
        self.model, self.runtime, self.provenance = model, runtime, provenance or {}

    def predict(self, rgb, K, valid):
        import cv2
        _image(rgb, valid); K = _intrinsics(K)
        h, w = valid.shape
        target = (616, 1064)
        scale = min(target[0] / h, target[1] / w)
        resized = cv2.resize(rgb, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_LINEAR)
        rh, rw = resized.shape[:2]
        pad_h, pad_w = target[0] - rh, target[1] - rw
        top, left = pad_h // 2, pad_w // 2
        padded = cv2.copyMakeBorder(resized, top, pad_h - top, left, pad_w - left,
            cv2.BORDER_CONSTANT, value=[123.675, 116.28, 103.53])
        tensor = ((padded.astype(np.float32) - [123.675, 116.28, 103.53]) /
                  [58.395, 57.12, 57.375]).astype(np.float32).transpose(2, 0, 1)[None]
        with self.runtime.inference():
            native_depth, native_confidence, _ = self.model.inference({'input': self.runtime.tensor(tensor)})
        raw = _plane(native_depth)
        if raw.shape != target:
            raise BackendError('Metric3D output does not match the native padded input grid')
        restored_raw = _resize_valid(self.runtime, raw[top:top + rh, left:left + rw], (h, w))
        processed_K = K.copy(); processed_K[:2] *= scale
        # Native hub example uses the continuous scale, including when integer
        # raster dimensions truncate. Record both to avoid a hidden K correction.
        values, _, conversion = contracts.metric_depth(restored_raw, 'D3', processed_K=processed_K)
        saturated = np.isfinite(values) & (values >= 300)
        below = np.isfinite(values) & (values <= 0)
        values = np.clip(values, 0, 300)
        confidence = None
        if native_confidence is not None:
            confidence = _plane(native_confidence)
            if confidence.shape != target:
                raise BackendError('Metric3D confidence grid differs from canonical depth')
            confidence = self.runtime.resize(confidence[top:top + rh, left:left + rw], (h, w))
        metadata = dict(self.provenance, **conversion, component='D3', precision='float32',
            actual_processed_shape=list(target), resized_shape=[rh, rw], native_resize_scale=scale,
            native_processed_K=processed_K.tolist(), pad=[top, pad_h - top, left, pad_w - left],
            native_K_convention='hub example scales intrinsic four-vector by continuous fit scale',
            normalization=dict(mean=[123.675, 116.28, 103.53], std=[58.395, 57.12, 57.375]),
            native_canonical_nonfinite=int((~np.isfinite(raw)).sum()),
            native_canonical_nonpositive=int((np.isfinite(raw) & (raw <= 0)).sum()),
            native_clamp_metres=[0, 300], saturated_pixels=int(saturated.sum()),
            saturated_fraction=float(saturated[valid].mean()), native_below_clamp_pixels=int(below.sum()),
            confidence=None if confidence is None else dict(meaning='native depth confidence; not normal confidence',
                direction='native score, unqualified', calibration='uncalibrated; never used to filter scale support'))
        return _finish_depth(values, valid, raw, metadata, confidence)


class DepthProBackend:
    def __init__(self, model, transform, runtime, provenance=None):
        self.model, self.transform, self.runtime = model, transform, runtime
        self.provenance = provenance or {}

    def predict(self, rgb, K, valid):
        from PIL import Image
        _image(rgb, valid); K = _intrinsics(K)
        captured = {}
        def observe(args, _kwargs, output):
            captured['raw'] = _plane(output[0])
            captured['actual_processed_shape'] = list(args[0].shape[-2:])
        with _capture_method(self.model, 'forward', observe), self.runtime.inference():
            output = self.model.infer(self.transform(Image.fromarray(rgb)),
                f_px=self.runtime.tensor(np.float32(K[0, 0])), interpolation_mode='bilinear')
        if 'raw' not in captured or captured['actual_processed_shape'] != [1536, 1536]:
            raise BackendError('Depth Pro canonical inverse-depth/native 1536-square inference was not observed')
        raw = captured['raw']
        # Diagnostic reconstruction only: exported depth is native infer's
        # already-restored inversion. Never multiply its output by focal again.
        inverse = self.runtime.resize(raw * (rgb.shape[1] / K[0, 0]), valid.shape)
        low, high = inverse <= 1e-4, inverse >= 1e4
        values, _, conversion = contracts.metric_depth(_plane(output['depth']), 'D4', already_metric=True)
        metadata = dict(self.provenance, **conversion, component='D4', precision='float32',
            actual_processed_shape=captured['actual_processed_shape'], input_fx=float(K[0, 0]),
            f_px_dtype='float32 device tensor', depth_type='native camera-z metres',
            raw_depth_type='canonical inverse depth before focal conversion and clamp',
            native_inverse_depth_clamp=[1e-4, 1e4], inverse_clamp_low_pixels=int(low.sum()),
            inverse_clamp_high_pixels=int(high.sum()), saturated_fraction=float((low | high)[valid].mean()),
            native_raw_nonfinite=int((~np.isfinite(raw)).sum()),
            native_raw_nonpositive=int((np.isfinite(raw) & (raw <= 0)).sum()),
            confidence=None, grid_restore='native bilinear inverse-depth restore followed by clamp/inversion')
        return _finish_depth(values, valid, raw, metadata)


def _grounding(bundle, runtime, text_threshold):
    source = 'grounding_source'
    models = bundle.module('groundingdino.models', source)
    config = bundle.module('groundingdino.util.slconfig', source).SLConfig.fromfile(bundle['grounding_config'])
    config.device = runtime.device
    config.text_encoder_type = bundle['bert_snapshot']
    model = models.build_model(config)
    utils = bundle.module('groundingdino.util.utils', source)
    checkpoint = runtime.torch.load(bundle['grounding_checkpoint'], map_location='cpu', weights_only=True)
    incompatible = model.load_state_dict(utils.clean_state_dict(checkpoint['model']), strict=False)
    # The official loader uses strict=False. Keep the exact policy and disclose
    # every mismatch, instead of hiding it or selecting alternate weights.
    model = model.to(device=runtime.device, dtype=runtime.torch.float32).eval()
    transforms = bundle.module('groundingdino.datasets.transforms', source)
    transform = transforms.Compose([transforms.RandomResize([800], max_size=1333), transforms.ToTensor(),
        transforms.Normalize([.485, .456, .406], [.229, .224, .225])])
    predict = bundle.module('groundingdino.util.inference', source).predict
    detector = GroundingDetector(model, transform, predict, runtime, text_threshold)
    detector.metadata['state_dict_missing_keys'] = list(incompatible.missing_keys)
    detector.metadata['state_dict_unexpected_keys'] = list(incompatible.unexpected_keys)
    return detector


def _sam2(bundle, runtime, detector, component):
    builders = bundle.module('sam2.build_sam', 'sam2_source')
    # The native package otherwise catches missing connected-components kernels
    # and silently omits some of its default mask postprocessing.
    bundle.module('sam2._C', 'sam2_source')
    config = 'configs/sam2.1/sam2.1_hiera_l.yaml'
    model = builders.build_sam2(config, bundle['sam2_checkpoint'], device=runtime.device,
        mode='eval', apply_postprocessing=True, hydra_overrides_extra=['++model.compile_image_encoder=false'])
    predictor = bundle.module('sam2.sam2_image_predictor', 'sam2_source').SAM2ImagePredictor(model)
    video = builders.build_sam2_video_predictor(config, bundle['sam2_checkpoint'], device=runtime.device,
        mode='eval', apply_postprocessing=True, vos_optimized=False,
        hydra_overrides_extra=['++model.compile_image_encoder=false'])
    return SAM2Backend(component, detector, predictor, video, runtime, bundle.provenance)


def _legacy_vipe_segmentation(bundle, runtime):
    module = bundle.module('vipe.priors.track_anything', 'vipe_source')
    frame_type = bundle.module('vipe.streams.base', 'vipe_source').VideoFrame
    cache = bundle.module('vipe.utils.model_cache', 'vipe_source').ModelCache()
    config = bundle.module('vipe.priors.track_anything.groundingdino.config', 'vipe_source').config
    # Historical ModelCache keys include checkpoint paths. Stable bindings share
    # immutable weights; the factory still creates fresh per-pair tracker state.
    asset_folder = tempfile.TemporaryDirectory(prefix='vipe-benchmark-legacy-assets-')
    root = Path(asset_folder.name)
    for subdir, key in [('sam', 'sam_checkpoint'), ('aot', 'aot_checkpoint')]:
        (root / subdir).mkdir()
        (root / subdir / CHECKPOINT_NAMES[key]).symlink_to(bundle.paths[key])
    def factory():
        # Keep the historical constructor and invocation. Its fixed cache names
        # are bound to verified explicit files for the duration of construction.
        def local_state(url, *args, **kwargs):
            expected = 'https://huggingface.co/ShilongLiu/GroundingDINO/resolve/main/groundingdino_swint_ogc.pth'
            if url != expected:
                raise BackendError(f'unadmitted historical URL requested: {url}')
            return runtime.torch.load(bundle['grounding_checkpoint'], map_location='cpu', weights_only=True)
        original_encoder = config.text_encoder_type
        try:
            config.text_encoder_type = bundle['bert_snapshot']
            with patch.object(runtime.torch.hub, 'get_dir', lambda: asset_folder.name), \
                 patch.object(runtime.torch.hub, 'load_state_dict_from_url', local_state):
                return module.TrackAnythingPipeline(['person', 'basketball'], model_cache=cache)
        finally:
            config.text_encoder_type = original_encoder
    provenance = dict(bundle.provenance, asset_loading='only cache/path bindings changed; native inference unchanged')
    backend = LegacyViPESegmentationBackend(factory, frame_type, runtime, provenance)
    backend.asset_folder = asset_folder
    return backend


def _build_native(component, bundle, runtime):
    torch = runtime.torch
    if component in ('S0', 'D0'):
        device_module = bundle.module('vipe.utils.device', 'vipe_source')
        device_module.configure_device(runtime.device)
    if component == 'S0':
        return _legacy_vipe_segmentation(bundle, runtime)
    if component == 'S1':
        detector = _grounding(bundle, runtime, .5)
        sam = bundle.module('segment_anything', 'sam_source')
        predictor = sam.SamPredictor(sam.sam_model_registry['vit_b'](
            checkpoint=bundle['sam_checkpoint']).to(device=runtime.device, dtype=torch.float32).eval())
        # Setup preserves SAM-Track's vendored tree and exposes the separate
        # prescribed AOT revision through its package namespace.
        bundle.source('aot_source')
        bundle.source('samtrack_source')
        aot_module = _s1_aot_module(bundle)
        aot_package = importlib.import_module('aot')
        locations = [safe_path(p).resolve() for p in getattr(aot_package, '__path__', [])]
        if bundle.paths['aot_source'] not in locations:
            raise BackendError('SAM-Track aot import is not the declared pinned AOT source')
        gpu_id = 0 if runtime.device == 'cuda' else int(runtime.device.split(':')[1])
        tracker = _s1_tracker(aot_module, runtime, dict(phase='PRE_YTB_DAV', model='r50_deaotl',
            model_path=bundle['aot_checkpoint'], long_term_mem_gap=9999, max_len_long_term=9999,
            gpu_id=gpu_id))
        attention = bundle.module('networks.layers.attention', 'aot_source')
        if not attention.enable_corr:
            raise BackendError('AOT native correlation extension is unavailable; implicit fallback is prohibited')
        return LegacyStandaloneBackend(detector, predictor, tracker, runtime, bundle.provenance)
    if component in ('S2', 'S4'):
        if component == 'S2':
            detector = _grounding(bundle, runtime, .25)
        else:
            transformers = importlib.import_module('transformers')
            processor = transformers.RTDetrImageProcessor.from_pretrained(
                bundle['rtdetr_snapshot'], local_files_only=True)
            model = transformers.RTDetrV2ForObjectDetection.from_pretrained(
                bundle['rtdetr_snapshot'], local_files_only=True, use_safetensors=True,
                torch_dtype=torch.float32).to(runtime.device).eval()
            detector = RTDetrDetector(processor, model, runtime)
        return _sam2(bundle, runtime, detector, component)
    if component == 'S3':
        builders = bundle.module('sam3.model_builder', 'sam3_source')
        processor_type = bundle.module('sam3.model.sam3_image_processor', 'sam3_source').Sam3Processor
        def image_factory():
            model = builders.build_sam3_image_model(checkpoint_path=bundle['sam3_checkpoint'],
                bpe_path=bundle['bpe_vocabulary'], device=runtime.device, load_from_HF=False,
                eval_mode=True, enable_segmentation=True, enable_inst_interactivity=False, compile=False)
            return processor_type(model, resolution=1008, device=runtime.device, confidence_threshold=.5)
        def video_factory():
            return builders.build_sam3_video_model(checkpoint_path=bundle['sam3_checkpoint'],
                bpe_path=bundle['bpe_vocabulary'], load_from_HF=False, device=runtime.device,
                strict_state_dict_loading=True, apply_temporal_disambiguation=True, compile=False).eval()
        return SAM3Backend(image_factory, video_factory, runtime, bundle.provenance)
    if component == 'D0':
        module = bundle.module('vipe.priors.depth.unidepth', 'vipe_source')
        native_class = module.UniDepthV2
        original = native_class.from_pretrained
        def local_model(name, **kwargs):
            if name != 'lpiccinelli/unidepth-v2-vitl14':
                raise BackendError(f'unadmitted historical UniDepth model requested: {name}')
            return original(bundle['unidepth_snapshot'], local_files_only=True)
        with patch.object(native_class, 'from_pretrained', local_model):
            model = module.UniDepth2Model(type='l')
        input_type = bundle.module('vipe.priors.depth.base', 'vipe_source').DepthEstimationInput
        return UniDepthBackend(component, model, runtime, bundle.provenance, input_type)
    if component == 'D1':
        model_class = bundle.module('unidepth.models', 'unidepth_source').UniDepthV2
        model = model_class.from_pretrained(bundle['unidepth_snapshot'], local_files_only=True)
        model = model.to(device=runtime.device, dtype=torch.float32).eval()
        model.interpolation_mode = 'bilinear'
        if hasattr(model, 'resolution_level'):
            raise BackendError('UniDepth checkpoint introduced a resolution override outside the frozen settings')
        return UniDepthBackend(component, model, runtime, bundle.provenance)
    if component == 'D2':
        model_class = bundle.module('depth_anything_3.api', 'da3_source').DepthAnything3
        model = model_class.from_pretrained(bundle['da3_snapshot'], local_files_only=True)
        if model.model_name != 'da3metric-large':
            raise BackendError('DA3 snapshot did not construct DA3METRIC-LARGE')
        return DA3Backend(model.to(device=runtime.device, dtype=torch.float32).eval(), runtime, bundle.provenance)
    if component == 'D3':
        # source='local', pretrain=False avoids the hub's resolve/main URL.
        bundle.source('metric3d_source')
        model = torch.hub.load(bundle['metric3d_source'], 'metric3d_vit_large', source='local', pretrain=False)
        state = torch.load(bundle['metric3d_checkpoint'], map_location='cpu')
        incompatible = model.load_state_dict(state['model_state_dict'], strict=False)
        provenance = dict(bundle.provenance, state_dict_missing_keys=list(incompatible.missing_keys),
            state_dict_unexpected_keys=list(incompatible.unexpected_keys), config='vit.raft5.large.py')
        return Metric3DBackend(model.to(device=runtime.device, dtype=torch.float32).eval(), runtime, provenance)
    if component == 'D4':
        from dataclasses import replace
        native = bundle.module('depth_pro.depth_pro', 'depth_pro_source')
        config = replace(native.DEFAULT_MONODEPTH_CONFIG_DICT, checkpoint_uri=bundle['depth_pro_checkpoint'])
        model, transform = native.create_model_and_transforms(config=config,
            device=torch.device(runtime.device), precision=torch.float32)
        return DepthProBackend(model.eval(), transform, runtime, bundle.provenance)
    raise BackendError(f'unimplemented native component: {component}')


def build_backend(component, assets, *, device='cuda'):
    """Build one pinned backend from verified local files in an admitted worker.

    This constructs models and allocates their requested GPU resources; it must
    be called inside the component job's budget, never by setup/import probes.
    ``REQUIRED_ASSETS`` describes the public asset-name contract.
    """
    bundle = AssetBundle(component, assets)
    if not re.fullmatch(r'cuda(?::0)?', str(device)):
        raise BackendError('Plan 031 permits one CUDA device; CPU fallback is prohibited')
    if any(os.environ.get(name) != '1' for name in ('HF_HUB_OFFLINE', 'TRANSFORMERS_OFFLINE')):
        raise BackendError('native worker must set HF_HUB_OFFLINE=1 and TRANSFORMERS_OFFLINE=1 before imports')
    torch = importlib.import_module('torch')
    if not torch.cuda.is_available():
        raise BackendError('CUDA unavailable; no CPU fallback')
    if component in ('S2', 'S3', 'S4', 'D2') and not torch.cuda.is_bf16_supported():
        raise BackendError('native bfloat16 inference is required; precision fallback is prohibited')
    runtime = TorchRuntime(torch, str(device))
    def no_download(*args, **kwargs):
        raise BackendError('native backend attempted an unadmitted download; supply the exact local asset')
    # The caller's network guard must remain installed throughout the worker.
    # These constructor guards make accidental auxiliary torch hub downloads
    # explicit failures, including pretrained backbone requests.
    with ExitStack() as stack:
        stack.enter_context(patch.object(torch.hub, 'download_url_to_file', no_download))
        stack.enter_context(patch.object(torch.hub, 'load_state_dict_from_url', no_download))
        backend = _build_native(component, bundle, runtime)
    import random
    random.seed(0); np.random.seed(0); torch.manual_seed(0); torch.cuda.manual_seed_all(0)
    settings_path = Path(__file__).resolve().parents[2] / 'configs/vipe-alternatives/components-v1.json'
    settings = read_json(settings_path)['settings'][component]
    backend.provenance.update(settings=settings, settings_sha256=object_hash(settings),
                              seed=0, batch_size=1, device=str(device))
    return backend

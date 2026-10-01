"""D9/D10 native offline sequence boundary and complete-context accounting."""
from types import SimpleNamespace
from pathlib import Path
import math
import time

import numpy as np

from .config import ROOT, training_cameras
from .depth_clips import materialize_role, publish_fixture_clips
from .files import file_record, object_hash, read_json, verify_record, write_json


INFER_LEN = 32
OVERLAP = 10
KEYFRAMES = [0, 12, 24, 25, 26, 27, 28, 29, 30, 31]
INTERP_LEN = 8


def native_window_plan(length, *, metric=False):
    """Audit the pinned native 32/10 offline work, including repeated tail frames."""
    if type(length) is not int or length <= 0:
        raise ValueError('nonempty native offline sequence required')
    stride = INFER_LEN - OVERLAP
    pad = (stride - length % stride) % stride + OVERLAP
    windows = []
    for index, start in enumerate(range(0, length, stride)):
        source_offsets = [min(start + i, length - 1) for i in range(INFER_LEN)]
        windows.append(dict(start=start, source_offsets=source_offsets,
            padded_inputs=sum(start + i >= length for i in range(INFER_LEN)),
            reused_previous_keyframes=KEYFRAMES if index else [],
            relative_alignment=index > 0 and not metric,
            interpolated_overlap_frames=INTERP_LEN if index else 0))
    return dict(native_infer_len=INFER_LEN, overlap=OVERLAP, stride=stride,
        keyframes=KEYFRAMES, interpolation_len=INTERP_LEN, pad_frames=pad,
        padded_length=length + pad, windows=windows)


class VideoDepthAdapter:
    """One native offline inference per camera/role, without framewise refitting."""
    component = 'D9'
    domain = 'relative_inverse'
    metric = False

    def __init__(self, runtime, *, device):
        if (getattr(runtime, 'encoder', None) != 'vits' or
                getattr(runtime, 'metric', None) is not self.metric or
                getattr(runtime, 'training', False)):
            raise ValueError(f'{self.component} requires eval-mode '
                f'{"metric" if self.metric else "relative"} Video Depth Anything Small')
        if device not in ('cpu', 'cuda'):
            raise ValueError('explicit native inference device required')
        self.runtime = runtime
        self.device = device

    def infer_context(self, frames, footprint, rows, *, camera, role):
        expected = list(range(50, 150)) if role == 'fit' else (
            list(range(150, 200)) if role == 'check' else None)
        if expected is None or len(rows) != len(expected) or not all(
                row.get('camera') == camera and row.get('frame') == frame and
                row.get('role') == role and row.get('timestamp') == frame / 25 and
                isinstance(row.get('source_rgb'), dict) and
                isinstance(row.get('source_video'), dict)
                for row, frame in zip(rows, expected)):
            raise ValueError('video context identity/camera/role/timestamps changed')
        videos = {row['source_video']['sha256'] for row in rows}
        if len(videos) != 1:
            raise ValueError('video context source membership changed')
        frames = np.asarray(frames)
        footprint = np.asarray(footprint)
        if (frames.shape != (len(expected), 540, 960, 3) or frames.dtype != np.uint8 or
                footprint.shape != (540, 960) or footprint.dtype != np.bool_):
            raise ValueError('native video input grid/footprint changed')
        if hasattr(self.runtime, 'reset'):
            self.runtime.reset(camera, role)
        raw, fps = self.runtime.infer_video_depth(frames, 25, input_size=518,
            device=self.device, fp32=False)
        raw = np.asarray(raw)
        if fps != 25 or raw.shape != frames.shape[:3] or raw.dtype != np.float32:
            raise ValueError('native video output count/grid/fps/dtype changed')
        accepted = np.broadcast_to(footprint, raw.shape)
        if self.metric:
            if not np.isfinite(raw[accepted]).all() or (raw[accepted] <= 0).any():
                raise ValueError('metric camera-z output has nonfinite/nonpositive accepted pixels')
        elif not np.isfinite(raw[accepted]).all() or (raw[accepted] < 0).any():
            raise ValueError('relative inverse output has nonfinite/negative accepted pixels')
        values = raw.copy()
        values[:, ~footprint] = np.nan
        return SimpleNamespace(domain=self.domain, values=values,
            valid=accepted.copy(), raw_values=raw.copy(),
            metadata=dict(component=self.component,
                native_depth_type='camera-z metres' if self.metric else 'relative inverse depth',
                native_mode='offline sequence', native_precision='fp16 autocast',
                native_input_size=518, native_fps=25,
                window_plan=native_window_plan(len(expected), metric=self.metric),
                camera=camera, role=role, context_frames=expected,
                context_sha256=object_hash(rows), reset_boundary=f'camera{camera}-{role}',
                metric_scale='eligible-after-frozen-fit' if self.metric else 'ineligible',
                sparse_alignment='none', conversion_count=0,
                native_metric_overlap_alignment='identity' if self.metric else None,
                native_relative_overlap_alignment='scale-and-shift' if not self.metric else None))


class MetricVideoDepthAdapter(VideoDepthAdapter):
    """Exact metric Small release: native output is camera-z, no overlap fit."""
    component = 'D10'
    domain = 'camera_z_metres'
    metric = True


def run_video_fixture(request, output, config, *, backend, ledger):
    """CPU-only D9/D10 sequences through accepted context and clip package."""
    component = request.get('component')
    if (request.get('schema') != 'plan069-video-depth-request/v1' or
            request.get('record_kind') != 'fixture' or component not in ('D9', 'D10') or
            request.get('id') != f'{component}-video-fixture-001' or
            backend.component != component or
            backend.device != 'cpu'):
        raise ValueError('video fixture identity/CPU mode required')
    seconds = request.get('max_seconds')
    if type(seconds) not in (int, float) or not math.isfinite(seconds) or not 0 < seconds <= 600:
        raise ValueError('bounded CPU video fixture deadline required')
    cameras = request.get('cameras')
    if (not isinstance(cameras, list) or cameras != sorted(set(cameras)) or
            not set(cameras) <= set(training_cameras(config)) or
            not {1, 11, 21, 31} <= set(cameras)):
        raise ValueError('video fixture must include the four clip cameras')
    if component == 'D10' and set(cameras) != set(training_cameras(config)):
        raise ValueError('D10 metric scale requires every training camera')
    for key in ('context', 'configuration', 'extension_configuration'):
        verify_record(request[key])
    context = read_json(request['context']['path'])
    if context.get('schema') != 'plan069-depth-context/v1':
        raise ValueError('accepted context required')
    if (read_json(request['configuration']['path']) != config or
            request['extension_configuration'] != file_record(
                ROOT / 'configs/vipe-alternatives/depth-extension-v1.json') or
            ledger.config != config):
        raise ValueError('frozen extension/config/ledger binding differs')
    extension = read_json(request['extension_configuration']['path'])
    domain = 'camera_z_metres' if component == 'D10' else 'relative_inverse'
    candidate = extension['candidates'][component]
    if candidate['domain'] != domain or backend.domain != domain:
        raise ValueError('video candidate native domain changed')
    if component == 'D10' and candidate.get('convention') != dict(kind='camera_z',
            conversion_count=0,
            evidence='https://github.com/DepthAnything/Video-Depth-Anything/blob/'
                '4f5ae23172ba60fd7bc11ef671cca678842c7072/run.py#L76-L86'):
        raise ValueError('D10 camera-z convention evidence unverified')
    events = ledger.events()
    if (any(row['event'] == 'reserve' for row in ledger.states(events).values()) or
            ledger.totals(events)['cpu']['elapsed_seconds'] + seconds >
            config['cpu_prepare_score_report_seconds_limit']):
        raise ValueError('CPU video fixture allocation unavailable')
    for event in events:
        if event['event'] == 'cpu_preparation_charge':
            evidence = read_json(verify_record(event['evidence'])['path'])
            if evidence.get('id') == request['id']:
                raise ValueError('video fixture identity already consumed')
    output = Path(output)
    if output.name != request['id'] or output.exists():
        raise ValueError('immutable video fixture output identity changed or exists')
    start = time.monotonic()
    output.mkdir(parents=True, exist_ok=False)
    write_json(output / 'request.json', request)
    (output / 'source.py').write_bytes(Path(__file__).read_bytes())
    charged_elapsed = 0.
    try:
        map_rows, result_rows, sequences, anchors = [], [], [], {}
        settings = object_hash(candidate)
        schedule = ([(camera, role) for role in ('fit', 'check') for camera in cameras]
                    if component == 'D10' else
                    [(camera, role) for camera in cameras for role in ('fit', 'check')])
        fit_predictions, check_predictions = {}, {}
        for camera, role in schedule:
            if time.monotonic() - start >= seconds:
                raise TimeoutError('video fixture deadline exceeded')
            frames, footprint, context_rows = materialize_role(request['context'], camera, role)
            prediction = backend.infer_context(frames, footprint, context_rows,
                camera=camera, role=role)
            sequence = dict(camera=camera, role=role, context_sha256=prediction.metadata['context_sha256'],
                context_frames=prediction.metadata['context_frames'],
                window_plan=prediction.metadata['window_plan'],
                source_video=context_rows[0]['source_video'])
            sequences.append(sequence)
            for index, row in enumerate(context_rows):
                frame = row['frame']
                if frame not in (100, 175) and not (role == 'check' and camera in (1, 11, 21, 31)):
                    continue
                path = output / f'camera{camera}-frame{frame}.npz'
                with path.open('xb') as stream:
                    np.savez_compressed(stream,
                        **({'depth': prediction.values[index]} if component == 'D10'
                           else {'relative': prediction.values[index]}),
                        valid=prediction.valid[index], raw_values=prediction.raw_values[index])
                record = file_record(path)
                if component == 'D10' and frame in (100, 175):
                    (fit_predictions if role == 'fit' else check_predictions)[camera] = record
                result_rows.append(dict(camera=camera, frame=frame,
                    role=role, depth=record, source_rgb=row['source_rgb'],
                    context_sha256=sequence['context_sha256'], domain=domain))
                if role == 'check' and camera in (1, 11, 21, 31):
                    if frame == 175:
                        anchors[camera] = record
                    map_rows.append(dict(camera=camera, frame=frame,
                        source_rgb=row['source_rgb'], inputs=context['inputs'],
                        grid='scale-opencv-integer', domain=domain,
                        prediction=record, settings=settings,
                        reused_anchor=frame == 175))
        scales = {}
        if component == 'D10':
            from .scale import evaluate
            source_inputs = read_json(context['inputs']['path'])
            depth_rows = source_inputs['depth']
            provenance = dict(inputs=context['inputs'], component_sha256=settings,
                              component='D10')
            fit_rows = [row for row in depth_rows if row['identity']['frame'] == 100]
            check_rows = [row for row in depth_rows if row['identity']['frame'] == 175]
            fit = evaluate(fit_rows, fit_predictions, config, provenance=provenance)
            fit['component'] = 'D10'
            write_json(output / 'scale-fit.json', fit)
            scales['fit'] = file_record(output / 'scale-fit.json')
            if fit['status'] == 'passed':
                check = evaluate(check_rows, check_predictions, config,
                    provenance=provenance, frozen_fit=scales['fit'])
            else:
                admission = request.get('qualitative_admission')
                if not isinstance(admission, dict):
                    raise ValueError('failed D10 scale fit requires separate qualitative admission')
                verify_record(admission)
                proof = read_json(admission['path'])
                if proof != dict(schema='plan069-depth-qualitative-admission/v1',
                        record_kind='fixture', component='D10', inputs=context['inputs'],
                        purpose='qualitative-only', status='admitted'):
                    raise ValueError('D10 qualitative admission binding changed')
                check = dict(status='blocked', role='selection', scale=None,
                    blockers=['No passing frozen fit; qualitative-only admission'],
                    fit_blockers=fit.get('blockers', []), frozen_fit=scales['fit'],
                    provenance=provenance, cameras=[])
            check['component'] = 'D10'
            write_json(output / 'scale-check.json', check)
            scales['check'] = file_record(output / 'scale-check.json')
        result = dict(schema='plan069-video-depth-result/v1', id=request['id'],
            status='complete', record_kind='fixture', component=component,
            domain=domain, sequences=sequences, rows=result_rows, scale=scales,
            context=request['context'], original_inputs=context['inputs'],
            eligibility=dict(metric_scale=check['status'] if component == 'D10'
                else 'ineligible', downstream='blocked',
                             commercial='unverified', runtime='fixture-only'))
        write_json(output / 'result.json', result)
        inference_elapsed = time.monotonic() - start
        if inference_elapsed > seconds:
            raise TimeoutError('video fixture deadline exceeded')
        charge = ledger.charge_cpu_preparation(inference_elapsed,
            file_record(output / 'result.json'))
        charged_elapsed = inference_elapsed
        write_json(output / 'ledger-outcome.json', charge)
        clips = publish_fixture_clips(request['context'], component, domain,
            map_rows, anchors, output / 'clips', dict(
                source_result=file_record(output / 'result.json'),
                ledger_outcome=file_record(output / 'ledger-outcome.json'),
                configuration=file_record(output / 'request.json')),
            max_seconds=max(.001, seconds - charged_elapsed))
        elapsed = time.monotonic() - start
        if elapsed > seconds:
            raise TimeoutError('video fixture deadline exceeded')
        receipt = dict(schema='plan069-video-depth-transaction/v1', id=request['id'],
            status='complete', worker=file_record(output / 'result.json'),
            package=clips['package'], elapsed_seconds=elapsed)
        write_json(output / 'transaction.json', receipt)
        ledger.charge_cpu_preparation(elapsed - charged_elapsed,
            file_record(output / 'transaction.json'))
        return receipt
    except BaseException as error:
        elapsed = time.monotonic() - start
        write_json(output / 'failure.json', dict(schema='plan069-video-depth-failure/v1',
            id=request['id'], status='failed', error=f'{type(error).__name__}: {error}',
            elapsed_seconds=elapsed))
        ledger.charge_cpu_preparation(max(0., elapsed - charged_elapsed),
            file_record(output / 'failure.json'))
        raise

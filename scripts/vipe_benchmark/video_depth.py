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


def _check_support(rows, predictions):
    """Report check-frame support without fitting a replacement metric scale."""
    from .contracts import depth as validate_depth, sample_depth
    from .files import load_array
    cameras = []
    blockers = ['No passing frozen fit; check scale is unavailable']
    for row in sorted(rows, key=lambda row: row['identity']['camera']):
        camera = row['identity']['camera']
        with load_array(row['samples']) as geometry, load_array(predictions[camera]) as output:
            image_valid = geometry['valid'] > 0
            validate_depth(output['depth'], output['valid'], image_valid)
            if not np.array_equal(geometry['K'], row['K']):
                raise ValueError('check support intrinsic provenance mismatch')
            _, good = sample_depth(output['depth'], output['valid'], geometry['uv'])
            good &= np.isfinite(geometry['camera_z']) & (geometry['camera_z'] > 0)
            cells = np.floor(geometry['uv'][good] / [240, 135]).astype(int)
            cameras.append(dict(camera_id=camera, points=int(good.sum()),
                occupied_grid_cells=len(set(map(tuple, cells))),
                positive_depth_fraction=float(output['valid'][image_valid].mean())))
            if not good.any():
                blockers.append(f'camera {camera}: zero valid depth support')
    return dict(status='blocked', role='selection', scale=None,
                blockers=blockers, cameras=cameras, estimator='not invoked')


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
    return _run_video(request, output, config, backend=backend, ledger=ledger,
                      record_kind='fixture')


def run_video_actual(request, output, config, *, backend, ledger, request_path):
    """Run one GPU-reserved native video attempt with exact admission evidence."""
    admitted_video_request(request, output, config, ledger=ledger,
                           request_path=request_path)
    if backend.device != 'cuda' or backend.component != request['component']:
        raise ValueError('exact CUDA video backend required')
    return _run_video(request, output, config, backend=backend, ledger=ledger,
                      record_kind='actual')


def validate_runtime_interpreter(runtime, executable, *, executable_record=None):
    """Keep the qualified virtual environment path, including its invocation spelling."""
    qualification = read_json(verify_record(runtime['receipt'])['path'])
    if qualification.get('python_executable') != str(Path(executable).absolute()):
        raise ValueError('video qualified virtual environment interpreter differs')
    if executable_record is not None and executable_record != file_record(executable):
        raise ValueError('video resolved executable record differs')


def admitted_video_request(request, output, config, *, ledger, request_path):
    """Recheck the exact live reservation before importing model code or CUDA."""
    from .depth_setup import _active_reservation
    import sys
    if (request.get('schema') != 'plan069-video-depth-request/v1' or
            request.get('record_kind') != 'actual' or
            request.get('component') not in ('D9', 'D10') or
            request.get('candidate') != request.get('component') or
            request.get('id') != f"plan069-{request.get('component')}-maps-001" or
            request.get('job_id') != request.get('id')):
        raise ValueError('actual D9/D10 video request required')
    run_root, effective = _active_reservation(request, request_path, Path(output))
    if config != effective or ledger.path != Path(request['ledger_path']).resolve():
        raise ValueError('actual video ledger/configuration binding changed')
    if request['component'] == 'D9':
        from .depth_d9_continuation import protected_continuation
        protected_continuation(ledger.events(), config, run_root, phase='worker')
    state = ledger.states().get(request['id'], {})
    admission = read_json(verify_record(request['admission'])['path'])
    qualification = admission.get('qualification', admission.get('runtime', {}).get('receipt'))
    if (request.get('source_review') != admission.get('source_review') or
            not isinstance(qualification, dict) or
            request.get('qualification') != qualification):
        raise ValueError('video source review or qualification binding changed')
    verify_record(request['source_review'])
    verify_record(qualification)
    validate_runtime_interpreter(admission['runtime'], sys.executable)
    if (state.get('event') != 'reserve' or state.get('resource') != 'gpu' or
            state.get('evidence', {}).get('admission') != request['admission'] or
            request.get('max_seconds', 10**30) > state.get('seconds', 0) or
            admission.get('candidate') != request['component'] or
            admission.get('status') != 'passed' or
            admission.get('schema') != 'plan069-depth-admission-result/v1'):
        raise ValueError('passed exact video admission and GPU reservation required')
    setup = read_json(verify_record(request['setup'])['path'])
    recovery = setup.get('schema') in ('plan069-video-setup-recovery-result/v1', 'plan069-video-setup-recovery-result/v2')
    if ((recovery and request['component'] != 'D9') or
            setup.get('schema') not in ('plan069-video-setup-result/v1', 'plan069-video-setup-recovery-result/v1', 'plan069-video-setup-recovery-result/v2') or
            setup.get('status') != 'complete' or
            setup.get('record_kind') != 'actual' or
            setup.get('candidate') != request['component'] or
            setup.get('review') != request['review'] or
            setup.get('authorization') != request['authorization']):
        raise ValueError('exact completed native video setup required')
    if recovery:
        from .depth_recovery_lineage import JOBS
        if setup.get('job_id') not in JOBS:
            raise ValueError('exact approved recovery job required')
    setup_job = setup['job_id'] if recovery else f"plan069-{request['component']}-setup-001"
    setup_state = ledger.states().get(setup_job, {})
    if (setup_state.get('event') != 'finish' or
            setup_state.get('status') != 'complete' or
            setup_state.get('result') != request['setup']):
        raise ValueError('video setup is not ledger-complete')
    if Path(output).resolve().parent != (run_root / 'jobs').resolve():
        raise ValueError('actual video output outside shared run')
    video_slot_guard(request, ledger)
    return setup


def video_slot_guard(request, ledger):
    """Verify setup lineage once, then check unchanged caps without rehashing weights."""
    from .budgets import budget_snapshot
    from .depth_map_allowance import remaining_map_allocation, check_slot_byte_budget
    events = ledger.events()
    grants = [event for event in events if event.get('event') == 'depth_attempt_authorized'
              and event.get('candidate') == request['component']]
    if len(grants) != 1 or not grants[0].get('slot_byte_budget'):
        raise ValueError('video whole-slot byte proof required')
    grant = grants[0]
    admission = read_json(verify_record(request['admission'])['path'])
    review = read_json(verify_record(request['review'])['path'])
    proposal = next(row for row in review['proposals'] if row['candidate'] == request['component'])
    if (admission.get('completed_setup') != request['setup'] or
            grant.get('admission') != request['admission'] or
            grant.get('review') != request['review'] or
            grant.get('authorization') != request['authorization'] or
            grant.get('source_review') != request['source_review'] or
            grant.get('proposal_sha256') != object_hash(proposal) or
            request.get('max_seconds') != proposal['allocation']['gpu_seconds']):
        raise ValueError('video whole-slot admission binding changed')
    stage = remaining_map_allocation(proposal, request['setup'], events,
                                    ledger.path.parent, admission['assets'],
                                    active_map_admission=request['admission'])
    budget = grant['slot_byte_budget']
    setup_grants = [event for event in events if event.get('event') == 'depth_setup_authorized'
                    and event.get('candidate') == request['component']]
    if len(setup_grants) != 1 or budget.get('setup_baseline') != setup_grants[0].get('resource_snapshot'):
        raise ValueError('video whole-slot setup baseline changed')
    if (grant.get('map_stage_allowance') != stage or budget.get('setup') != stage['setup'] or
            budget.get('setup_finish_event_sha256') != stage['setup_finish_event_sha256'] or
            budget.get('recovery_lineage') != stage.get('recovery_lineage')):
        raise ValueError('video whole-slot setup lineage changed')
    def guard():
        check_slot_byte_budget(proposal, budget, ledger.path.parent,
                               budget_snapshot(ledger.path.parent))
    guard()
    return guard


def _run_video(request, output, config, *, backend, ledger, record_kind):
    """Process every fit/check context before publishing 60 anchors and clips."""
    component = request.get('component')
    if (request.get('schema') != 'plan069-video-depth-request/v1' or
            request.get('record_kind') != record_kind or component not in ('D9', 'D10') or
            request.get('id') != (f'{component}-video-fixture-001' if record_kind == 'fixture'
                                 else f'plan069-{component}-maps-001') or
            backend.component != component or
            backend.device != ('cpu' if record_kind == 'fixture' else 'cuda')):
        raise ValueError('video request identity/device mode required')
    seconds = request.get('max_seconds')
    ceiling = 600 if record_kind == 'fixture' else 12000
    if type(seconds) not in (int, float) or not math.isfinite(seconds) or not 0 < seconds <= ceiling:
        raise ValueError('bounded video deadline required')
    cameras = request.get('cameras')
    if (not isinstance(cameras, list) or cameras != training_cameras(config)):
        raise ValueError('video fixture requires every training camera')
    for key in ('context', 'configuration', 'extension_configuration'):
        verify_record(request[key])
    context = read_json(request['context']['path'])
    if context.get('schema') != 'plan069-depth-context/v1':
        raise ValueError('accepted context required')
    frozen_config = read_json(request['configuration']['path'])
    expected_config = (frozen_config if record_kind == 'fixture' else
        dict(frozen_config, new_download_gib_limit=110,
             new_artifact_disk_gib_limit=210))
    if (expected_config != config or
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
    if record_kind == 'fixture':
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
        raise ValueError('immutable video output identity changed or exists')
    slot_guard = video_slot_guard(request, ledger) if record_kind == 'actual' else lambda: None
    slot_guard()
    start = time.monotonic()
    output.mkdir(parents=True, exist_ok=False)
    write_json(output / 'request.json', request)
    (output / 'source.py').write_bytes(Path(__file__).read_bytes())
    slot_guard()
    charged_elapsed = 0.
    try:
        map_rows, result_rows, sequences, anchors = [], [], [], {}
        anchor_rows = []
        settings = object_hash(candidate)
        schedule = ([(camera, role) for role in ('fit', 'check') for camera in cameras]
                    if component == 'D10' else
                    [(camera, role) for camera in cameras for role in ('fit', 'check')])
        fit_predictions: dict[int, dict] = {}
        check_predictions: dict[int, dict] = {}
        fit = None
        if component == 'D10':
            from .scale import evaluate
            source_inputs = read_json(context['inputs']['path'])
            depth_rows = source_inputs['depth']
            provenance = dict(inputs=context['inputs'], component_sha256=settings,
                              component='D10')
            fit_rows = [row for row in depth_rows if row['identity']['frame'] == 100]
            check_rows = [row for row in depth_rows if row['identity']['frame'] == 175]
        for camera, role in schedule:
            slot_guard()
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
                slot_guard()
                with path.open('xb') as stream:
                    np.savez_compressed(stream,
                        **({'depth': prediction.values[index]} if component == 'D10'
                           else {'relative': prediction.values[index]}),
                        valid=prediction.valid[index], raw_values=prediction.raw_values[index])
                slot_guard()
                record = file_record(path)
                if component == 'D10' and frame in (100, 175):
                    (fit_predictions if role == 'fit' else check_predictions)[camera] = record
                result_rows.append(dict(camera=camera, frame=frame,
                    role=role, depth=record, source_rgb=row['source_rgb'],
                    context_sha256=sequence['context_sha256'], domain=domain))
                if frame in (100, 175):
                    anchor_rows.append(dict(camera=camera, frame=frame,
                        role=role, depth=record,
                        context_sha256=sequence['context_sha256']))
                if role == 'check' and camera in (1, 11, 21, 31):
                    if frame == 175:
                        anchors[camera] = record
                    map_rows.append(dict(camera=camera, frame=frame,
                        source_rgb=row['source_rgb'], inputs=context['inputs'],
                        grid='scale-opencv-integer', domain=domain,
                        prediction=record, settings=settings,
                        reused_anchor=frame == 175))
            if component == 'D10' and role == 'fit' and camera == cameras[-1]:
                fit = evaluate(fit_rows, fit_predictions, config, provenance=provenance)
                fit['component'] = 'D10'
                slot_guard()
                write_json(output / 'scale-fit.json', fit)
                slot_guard()
                if fit['status'] != 'passed':
                    qualitative = request.get('qualitative_admission')
                    if not isinstance(qualitative, dict):
                        raise ValueError('failed D10 scale fit requires separate qualitative admission')
                    verify_record(qualitative)
                    proof = read_json(qualitative['path'])
                    if proof != dict(schema='plan069-depth-qualitative-admission/v1',
                            record_kind=record_kind, component='D10', inputs=context['inputs'],
                            purpose='qualitative-only', status='admitted'):
                        raise ValueError('D10 qualitative admission binding changed')
                # The complete fit decision and any qualitative-only authority
                # precede the first check-context inference and publication.
                slot_guard()
                write_json(output / 'fit-gate.json', dict(
                    schema='plan069-video-fit-gate/v1', component='D10',
                    status=fit['status'], qualitative_admission=
                        request.get('qualitative_admission') if fit['status'] != 'passed' else None,
                    fit=file_record(output / 'scale-fit.json')))
                slot_guard()
        expected_anchors = {(camera, frame) for camera in cameras for frame in (100, 175)}
        if (len(anchor_rows) != 60 or
                {(row['camera'], row['frame']) for row in anchor_rows} != expected_anchors or
                len(result_rows) != 256 or len(sequences) != 60):
            raise ValueError('all 30 camera fit/check anchors and context sequences required')
        scales = {}
        if component == 'D10':
            if fit is None:
                raise ValueError('complete D10 metric fit required before check')
            scales['fit'] = file_record(output / 'scale-fit.json')
            if fit['status'] == 'passed':
                check = evaluate(check_rows, check_predictions, config,
                    provenance=provenance, frozen_fit=scales['fit'])
            else:
                diagnostics = _check_support(check_rows, check_predictions)
                check = dict(status='blocked', role='selection', scale=None,
                    blockers=['No passing frozen fit; qualitative-only admission'],
                    fit_blockers=fit.get('blockers', []), frozen_fit=scales['fit'],
                    fit_cameras=fit.get('cameras', []),
                    check_blockers=diagnostics.get('blockers', []),
                    provenance=provenance, cameras=diagnostics['cameras'],
                    check_diagnostics=diagnostics)
            check['component'] = 'D10'
            slot_guard()
            write_json(output / 'scale-check.json', check)
            slot_guard()
            scales['check'] = file_record(output / 'scale-check.json')
        result = dict(schema='plan069-video-depth-result/v1', id=request['id'],
            status='complete', record_kind=record_kind, component=component,
            domain=domain, sequences=sequences, rows=result_rows,
            anchor_rows=anchor_rows, scale=scales,
            context=request['context'], original_inputs=context['inputs'],
            eligibility=dict(metric_scale=check['status'] if component == 'D10'
                else 'ineligible', downstream='blocked',
                             commercial='unverified' if record_kind == 'fixture' else 'admitted',
                             runtime='fixture-only' if record_kind == 'fixture' else 'actual-native'))
        map_result_path = output / 'result.json'
        slot_guard()
        write_json(map_result_path, result)
        slot_guard()
        inference_elapsed = time.monotonic() - start
        if inference_elapsed > seconds:
            raise TimeoutError('video fixture deadline exceeded')
        if record_kind == 'actual':
            # The supervisor must finish the GPU attempt before a separate CPU
            # stage may publish an actual package with trusted finish evidence.
            return result
        if record_kind == 'fixture':
            charge = ledger.charge_cpu_preparation(inference_elapsed,
                file_record(map_result_path))
            charged_elapsed = inference_elapsed
            write_json(output / 'ledger-outcome.json', charge)
        provenance = dict(source_result=file_record(map_result_path),
            configuration=file_record(output / 'request.json'))
        provenance['ledger_outcome'] = file_record(output / 'ledger-outcome.json')
        clips = publish_fixture_clips(request['context'], component, domain,
            map_rows, anchors, output / 'clips', provenance,
            max_seconds=max(.001, seconds - inference_elapsed), resource_guard=slot_guard)
        elapsed = time.monotonic() - start
        if elapsed > seconds:
            raise TimeoutError('video fixture deadline exceeded')
        receipt = dict(schema='plan069-video-depth-transaction/v1', id=request['id'],
            status='complete', record_kind=record_kind,
            worker=file_record(map_result_path),
            package=clips['package'], elapsed_seconds=elapsed)
        slot_guard()
        write_json(output / 'transaction.json', receipt)
        slot_guard()
        ledger.charge_cpu_preparation(elapsed - charged_elapsed,
            file_record(output / 'transaction.json'))
        return receipt
    except BaseException as error:
        elapsed = time.monotonic() - start
        write_json(output / 'failure.json', dict(schema='plan069-video-depth-failure/v1',
            id=request['id'], status='failed', error=f'{type(error).__name__}: {error}',
            elapsed_seconds=elapsed))
        if record_kind == 'fixture':
            ledger.charge_cpu_preparation(max(0., elapsed - charged_elapsed),
                file_record(output / 'failure.json'))
        raise

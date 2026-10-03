"""Bounded fixture and guarded actual training/render worker controls.

Actual paths require registered DO admission and the fixed native runtime class.
Only the separate child entry constructs native factories; no ledger is mutated.
"""
import math
import time
import json
import copy
from contextlib import contextmanager

import numpy as np

from .extended_final_render_contract import parse_request, validate_scene_bindings
from .files import file_record, object_hash, read_json, safe_path, verify_record, write_json
from .final_render_adapter import prepare_model_input
from .final_render_pipeline import validate_worker_result
from .final_render_contract import PHASES

_RESULT_RESERVE = 2**20


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def _bound(record):
    _require(type(record) is dict and set(record) == {'path','sha256','bytes'} and
        verify_record(record) == record, 'exact immutable worker input required')
    return read_json(record['path'])


def _prepare(request, arm, parent, initializer, runtime, phase, invocation_record=None, output=None):
    actual = request.get('record_kind') == 'actual'
    if actual:
        _require(invocation_record is not None, 'actual worker requires bound invocation')
        from .final_render_admission import worker_binding
        from .final_render_native import NativeFreeTimeRuntime
        binding = worker_binding(invocation_record,request,arm,phase)
        _require(type(runtime) is NativeFreeTimeRuntime and
            binding['invocation'].get('parent_result') == parent and
            binding['invocation'].get('initializer') == initializer and
            binding['invocation'].get('output') == str(safe_path(output).resolve()),
            'fixed actual native runtime and invocation inputs required')
    else:
        _require(invocation_record is None and request.get('record_kind') == getattr(runtime,'record_kind',None) == 'fixture',
            'fixture-only worker; actual DO adapter is unqualified')
    _require(runtime.is_fresh is True, 'fresh runtime instance required')
    request = parse_request(request)
    validate_scene_bindings(request)
    preceding = 'initializer' if phase == 'train' else 'train'
    previous = _validate_result(request, arm, preceding, _bound(parent))
    _require(previous['status'] == 'complete', 'complete predecessor required')
    if phase == 'render':
        _require('terminal_publication' in previous, 'published training completion required')
    bundle = _bound(initializer)
    _require(bundle.get('schema') == 'plan069-final-render-prepared-initializer/v1' and
        bundle.get('record_kind') == request['record_kind'] and bundle.get('arm') == arm and
        bundle.get('request_sha256') == object_hash(request) and
        bundle.get('execution_authorized') is False and bundle.get('native_adapter_qualified') is False,
        'bound same-arm initializer bundle required')
    if phase == 'train':
        _require(initializer in previous['artifacts'] and bundle['archive'] in previous['artifacts'],
            'initializer must be published by the exact predecessor')
    _require(verify_record(bundle['archive']) == bundle['archive'], 'initializer archive changed')
    with np.load(safe_path(bundle['archive']['path']), allow_pickle=False) as archive:
        arrays = {name:archive[name].copy() for name in archive.files}
    data, receipt = prepare_model_input(request, arm, bundle['initializer_receipt'], arrays)
    provenance = dict(schema='plan069-final-render-checkpoint-provenance/v1',record_kind=request['record_kind'],
        request_sha256=object_hash(request),arm=arm,composition=request['compositions'][arm],
        initializer=initializer,native_input_sha256=object_hash(receipt),seed=0,
        bindings=request['bindings'],normalization=request['initializer_contract']['normalization'])
    return request, previous, data, receipt, provenance


def _validate_result(request, arm, phase, result, *, published=True):
    if request['record_kind'] == 'actual':
        from .final_render_actual_result import validate_actual_worker_result
        return validate_actual_worker_result(request,arm,phase,result,published=published)
    return validate_worker_result(request,arm,phase,result)


class _Budget:
    def __init__(self, request, phase, output, clock, start, invocation_record=None):
        self.request, self.phase, self.output, self.clock = request, phase, output, clock
        self.invocation_record = invocation_record
        self.actual = request['record_kind'] == 'actual'
        _require(type(start) in (float,int) and math.isfinite(start), 'finite monotonic clock required')
        self.start = self.last = start
        self.usage = dict(peak_device_bytes=0,cpu_workers_used=0)
        self.completed_iterations = self.rendered_frames = 0
        self.cleanup_confirmed = False

    def check(self, reserve):
        now = self.clock()
        _require(type(now) in (float,int) and math.isfinite(now) and now >= self.last,
            'finite nondecreasing monotonic clock required')
        self.last = now
        if now-self.start+reserve >= PHASES[self.phase][1]:
            raise RuntimeError('phase deadline reserve exhausted')

    def artifacts(self):
        return [file_record(path) for path in sorted(self.output.rglob('*')) if path.is_file()]

    def resources(self, runtime):
        usage = runtime.resource_usage()
        for name,limit in [('peak_device_bytes',self.request['device_bytes_limit']),
                ('cpu_workers_used',self.request['cpu_workers_limit'])]:
            value = usage.get(name)
            if type(value) is int and value >= 0:
                self.usage[name] = max(self.usage[name],value)
            _require(type(value) is int and 0 <= value <= limit, 'invalid/excessive '+name)
        _require(sum(path.stat().st_size for path in self.output.rglob('*') if path.is_file())+_RESULT_RESERVE <=
            self.request['artifact_bytes_limit'], 'artifact storage limit exhausted')

    def failure(self, arm, error):
        receipt = dict(schema='plan069-final-render-worker-failure/v1',
            record_kind=self.request['record_kind'],status='failed',arm=arm,phase=self.phase,
            request_sha256=object_hash(self.request),reason=type(error).__name__+': '+str(error),
            completed_iterations=self.completed_iterations,rendered_frames=self.rendered_frames,
            cleanup_confirmed=self.cleanup_confirmed,elapsed_seconds=self.last-self.start,
            artifacts=self.artifacts(),resource_usage=self.usage,
            execution_authorized=self.actual,native_adapter_qualified=self.actual)
        if self.actual:
            receipt['invocation'] = self.invocation_record
        error.worker_failure = receipt
        current = sum(path.stat().st_size for path in self.output.rglob('*') if path.is_file())
        size = len((json.dumps(receipt,indent=2,allow_nan=False)+'\n').encode())
        if current+size <= self.request['artifact_bytes_limit']:
            write_json(self.output/'failure.json',receipt)


@contextmanager
def _managed_runtime(runtime, budget, arm):
    failure = None
    try:
        yield
    except BaseException as error:
        failure = error
    try:
        runtime.close()
        budget.cleanup_confirmed = True
    except BaseException as error:
        if failure is not None:
            failure.add_note('cleanup: '+str(error))
        else:
            failure = error
    try:
        budget.check(0.)
    except BaseException as error:
        if failure is not None:
            failure.add_note('post-cleanup budget: '+str(error))
        else:
            failure = error
    if failure is not None:
        budget.failure(arm,failure)
        raise failure


def _publish(request, arm, parent, budget, extra, *, proofs=()):
    """Finish validation/publication under the same failure and clock checks."""
    try:
        budget.check(0.)
        artifacts = budget.artifacts()
        checkpoint = extra.get('checkpoint')
        if checkpoint is not None:
            _require(verify_record(checkpoint) == checkpoint, 'checkpoint changed during cleanup/publication')
        for record in proofs:
            _require(verify_record(record) == record, 'restoration proof changed during cleanup/publication')
        result = dict(schema='plan069-final-render-actual-worker-result/v1' if budget.actual else 'plan069-final-render-worker-result/v1',
            record_kind=request['record_kind'],status='complete',
            arm=arm,phase=budget.phase,composition=request['compositions'][arm],request_sha256=object_hash(request),
            allocation_id=request['id']+'/'+arm+'/'+budget.phase,parent_result=parent,
            elapsed_seconds=budget.last-budget.start,peak_device_bytes=budget.usage['peak_device_bytes'],
            artifact_bytes=sum(r['bytes'] for r in artifacts)+_RESULT_RESERVE,
            cpu_workers_used=budget.usage['cpu_workers_used'],execution_authorized=budget.actual,
            native_adapter_qualified=budget.actual,artifacts=artifacts,**extra)
        if budget.actual:
            result['invocation'] = budget.invocation_record
        _validate_result(request,arm,budget.phase,result,published=False)
        budget.check(1.)
        result['elapsed_seconds'] = budget.last-budget.start
        result['terminal_publication'] = str(budget.output/'completion.json')
        result_size = len((json.dumps(result,indent=2,allow_nan=False)+'\n').encode())
        _require(result_size+4096 <= _RESULT_RESERVE and result['artifact_bytes'] <= request['artifact_bytes_limit'],
            'terminal result storage reserve exceeded')
        path = budget.output/'result.json'
        write_json(path,result)
        published = file_record(path)
        budget.check(1.)
        completion = dict(schema='plan069-final-render-actual-worker-completion/v1' if budget.actual else 'plan069-final-render-worker-completion/v1',
            record_kind=request['record_kind'],status='complete',
            arm=arm,phase=budget.phase,request_sha256=object_hash(request),result=published,
            elapsed_seconds=budget.last-budget.start,cleanup_confirmed=budget.cleanup_confirmed,
            artifact_bytes=result['artifact_bytes'],execution_authorized=budget.actual,native_adapter_qualified=budget.actual)
        if budget.actual:
            completion['invocation'] = budget.invocation_record
        completion_size = len((json.dumps(completion,indent=2,allow_nan=False)+'\n').encode())
        _require(result_size+completion_size <= _RESULT_RESERVE, 'completion storage reserve exceeded')
        write_json(budget.output/'completion.json',completion)
        budget.check(0.)
        return result
    except BaseException as error:
        budget.failure(arm,error)
        raise


def train(request, arm, parent, initializer, output, runtime, *, clock=time.monotonic, invocation_record=None):
    """Exercise sequential native updates and immutable checkpoint publication."""
    _require(request.get('record_kind') != 'actual' or clock is time.monotonic,
        'actual worker requires native monotonic clock')
    start = clock()
    request, _, data, receipt, provenance = _prepare(request,arm,parent,initializer,runtime,'train',invocation_record,output)
    output = safe_path(output).resolve()
    output.mkdir(parents=True,exist_ok=False)
    budget = _Budget(request,'train',output,clock,start,invocation_record)
    with _managed_runtime(runtime,budget,arm):
        budget.check(150.)
        budget.resources(runtime)
        runtime.prepare_training(copy.deepcopy(request),arm,data,copy.deepcopy(receipt),copy.deepcopy(provenance))
        for iteration in range(5000):
            budget.check(150.)
            budget.resources(runtime)
            metrics = runtime.training_step(iteration)
            _require(type(metrics.get('loss')) in (float,int) and math.isfinite(metrics['loss']),
                'nonfinite native loss')
            budget.completed_iterations = iteration+1
            budget.resources(runtime)
        budget.check(150.)
        checkpoint = output/'checkpoint-005000.pt'
        runtime.save_checkpoint(checkpoint,5000)
        metadata = runtime.checkpoint_metadata(checkpoint)
        _require(type(metadata.get('iteration')) is int and
            metadata == dict(iteration=5000,provenance=provenance),
            'checkpoint endpoint/provenance differs')
        artifact = file_record(checkpoint)
        budget.resources(runtime)
    return _publish(request,arm,parent,budget,dict(completed_iterations=5000,checkpoint=artifact))


def render(request, arm, parent, initializer, output, runtime, *, clock=time.monotonic, invocation_record=None):
    """Reload a complete fake endpoint and publish all matched held-out PNGs."""
    from PIL import Image
    _require(request.get('record_kind') != 'actual' or clock is time.monotonic,
        'actual worker requires native monotonic clock')
    start = clock()
    request, previous, data, receipt, provenance = _prepare(request,arm,parent,initializer,runtime,'render',invocation_record,output)
    checkpoint = previous['checkpoint']
    _require(verify_record(checkpoint) == checkpoint, 'consumed checkpoint bytes changed')
    output = safe_path(output).resolve()
    output.mkdir(parents=True,exist_ok=False)
    budget = _Budget(request,'render',output,clock,start,invocation_record)
    frames = []
    with _managed_runtime(runtime,budget,arm):
        budget.check(150.)
        budget.resources(runtime)
        restored = output/'restored-checkpoint.pt'
        reload = runtime.reload_checkpoint(copy.deepcopy(checkpoint),copy.deepcopy(request),arm,data,
            copy.deepcopy(receipt),copy.deepcopy(provenance),restored)
        _require(type(reload.get('iteration')) is int and reload['iteration'] == 5000 and
            reload.get('provenance') == provenance and reload.get('restored_state_equal') is True,
            'exact native checkpoint restoration differs')
        restored_record = file_record(restored)
        restored_metadata = runtime.checkpoint_metadata(restored_record['path'])
        _require(type(restored_metadata.get('iteration')) is int and
            restored_metadata == dict(iteration=5000,provenance=provenance),
            'published restored snapshot differs from endpoint')
        budget.completed_iterations = 5000
        _require(verify_record(checkpoint) == checkpoint, 'consumed checkpoint changed during reload')
        reload_path = output/'reload-validation.json'
        reload_receipt = dict(schema='plan069-final-render-actual-reload/v1' if budget.actual else 'plan069-final-render-fixture-reload/v1',
            record_kind=request['record_kind'],status='passed',checkpoint=checkpoint,iteration=5000,request_sha256=object_hash(request),arm=arm)
        if budget.actual:
            reload_receipt.update(restored_state_equal=True,restored_checkpoint=restored_record)
        write_json(reload_path,reload_receipt)
        reload_record = file_record(reload_path)
        for camera in request['render']['cameras']:
            for frame in request['render']['frames']:
                budget.check(30.)
                budget.resources(runtime)
                image = runtime.render_frame(camera,frame)
                _require(isinstance(image,np.ndarray) and image.dtype == np.float32 and
                    image.shape == (540,960,3) and np.isfinite(image).all(), 'finite native RGB frame required')
                # Frozen conversion: RGB, clamp [0,1], nearest-even uint8, lossless PNG.
                pixels = np.rint(np.clip(image,0,1)*255).astype(np.uint8)
                path = output/f'camera{camera}-frame{frame:06d}.png'
                with path.open('xb') as stream:
                    Image.fromarray(pixels).save(stream,format='PNG')
                frames.append(dict(camera=camera,frame=frame,rgb=file_record(path)))
                budget.rendered_frames = len(frames)
        budget.resources(runtime)
    return _publish(request,arm,parent,budget,dict(checkpoint=checkpoint,reload_validation=reload_record,
        iteration=5000,render_settings=request['render'],rendered_frames=frames),proofs=(restored_record,reload_record))

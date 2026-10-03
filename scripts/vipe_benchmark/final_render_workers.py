"""Bounded CPU fixture workers over the prospective native runtime boundary.

Actual jobs require a future qualified DO dispatcher. These entrypoints never
instantiate a native runtime, reserve a ledger identity or admit actual requests.
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


def _prepare(request, arm, parent, initializer, runtime, phase):
    _require(request.get('record_kind') == getattr(runtime,'record_kind',None) == 'fixture',
        'fixture-only worker; actual DO adapter is unqualified')
    _require(runtime.is_fresh is True, 'fresh runtime instance required')
    request = parse_request(request)
    validate_scene_bindings(request)
    preceding = 'initializer' if phase == 'train' else 'train'
    previous = validate_worker_result(request, arm, preceding, _bound(parent))
    _require(previous['status'] == 'complete', 'complete predecessor required')
    bundle = _bound(initializer)
    _require(bundle.get('schema') == 'plan069-final-render-prepared-initializer/v1' and
        bundle.get('record_kind') == 'fixture' and bundle.get('arm') == arm and
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
    provenance = dict(schema='plan069-final-render-checkpoint-provenance/v1',record_kind='fixture',
        request_sha256=object_hash(request),arm=arm,composition=request['compositions'][arm],
        initializer=initializer,native_input_sha256=object_hash(receipt),seed=0,
        bindings=request['bindings'],normalization=request['initializer_contract']['normalization'])
    return request, previous, data, receipt, provenance


class _Budget:
    def __init__(self, request, phase, output, clock, start):
        self.request, self.phase, self.output, self.clock = request, phase, output, clock
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
            record_kind='fixture',status='failed',arm=arm,phase=self.phase,
            request_sha256=object_hash(self.request),reason=type(error).__name__+': '+str(error),
            completed_iterations=self.completed_iterations,rendered_frames=self.rendered_frames,
            cleanup_confirmed=self.cleanup_confirmed,elapsed_seconds=self.last-self.start,
            artifacts=self.artifacts(),resource_usage=self.usage,
            execution_authorized=False,native_adapter_qualified=False)
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


def train(request, arm, parent, initializer, output, runtime, *, clock=time.monotonic):
    """Exercise sequential native updates and immutable checkpoint publication."""
    start = clock()
    request, _, data, receipt, provenance = _prepare(request,arm,parent,initializer,runtime,'train')
    output = safe_path(output).resolve()
    output.mkdir(parents=True,exist_ok=False)
    budget = _Budget(request,'train',output,clock,start)
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
        budget.resources(runtime)
        usage = budget.usage
    artifact = file_record(checkpoint)
    artifacts = budget.artifacts()
    result = dict(schema='plan069-final-render-worker-result/v1',record_kind='fixture',status='complete',
        arm=arm,phase='train',composition=request['compositions'][arm],request_sha256=object_hash(request),
        allocation_id=request['id']+'/'+arm+'/train',parent_result=parent,elapsed_seconds=budget.last-start,
        peak_device_bytes=usage['peak_device_bytes'],artifact_bytes=sum(r['bytes'] for r in artifacts)+_RESULT_RESERVE,
        cpu_workers_used=usage['cpu_workers_used'],execution_authorized=False,native_adapter_qualified=False,
        artifacts=artifacts,completed_iterations=5000,checkpoint=artifact)
    validate_worker_result(request,arm,'train',result)
    _require(len((json.dumps(result,indent=2,allow_nan=False)+'\n').encode()) <= _RESULT_RESERVE,
        'terminal result storage reserve exceeded')
    write_json(output/'result.json',result)
    return result


def render(request, arm, parent, initializer, output, runtime, *, clock=time.monotonic):
    """Reload a complete fake endpoint and publish all matched held-out PNGs."""
    from PIL import Image
    start = clock()
    request, previous, data, receipt, provenance = _prepare(request,arm,parent,initializer,runtime,'render')
    checkpoint = previous['checkpoint']
    _require(verify_record(checkpoint) == checkpoint, 'consumed checkpoint bytes changed')
    output = safe_path(output).resolve()
    output.mkdir(parents=True,exist_ok=False)
    budget = _Budget(request,'render',output,clock,start)
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
        write_json(reload_path,dict(schema='plan069-final-render-fixture-reload/v1',record_kind='fixture',
            status='passed',checkpoint=checkpoint,iteration=5000,request_sha256=object_hash(request),arm=arm))
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
    artifacts = budget.artifacts()
    result = dict(schema='plan069-final-render-worker-result/v1',record_kind='fixture',status='complete',
        arm=arm,phase='render',composition=request['compositions'][arm],request_sha256=object_hash(request),
        allocation_id=request['id']+'/'+arm+'/render',parent_result=parent,elapsed_seconds=budget.last-start,
        peak_device_bytes=budget.usage['peak_device_bytes'],artifact_bytes=sum(r['bytes'] for r in artifacts)+_RESULT_RESERVE,
        cpu_workers_used=budget.usage['cpu_workers_used'],execution_authorized=False,native_adapter_qualified=False,
        artifacts=artifacts,checkpoint=checkpoint,reload_validation=file_record(reload_path),iteration=5000,
        render_settings=request['render'],rendered_frames=frames)
    validate_worker_result(request,arm,'render',result)
    _require(len((json.dumps(result,indent=2,allow_nan=False)+'\n').encode()) <= _RESULT_RESERVE,
        'terminal result storage reserve exceeded')
    write_json(output/'result.json',result)
    return result

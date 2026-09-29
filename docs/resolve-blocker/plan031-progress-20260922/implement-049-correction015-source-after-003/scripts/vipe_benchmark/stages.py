"""Explicit component workers for the frozen Plan 031 matrix."""
from pathlib import Path
import random
import time

import numpy as np

from .access import Identity, RGBLoader, output_identities, validate_membership
from .config import training_cameras
from .contracts import depth as validate_depth, instances as validate_instances, validate_static
from .files import file_record, load_array, object_hash, read_json, verify_record, write_json


def array_file(path, value, *, deadline=None):
    from .s1_progress import before, operation, DeadlineSink
    if deadline is not None:before(deadline)
    from .s1_progress import checked_mkdir
    operation(checked_mkdir,path.parent,parents=True,exist_ok=True,deadline=deadline)
    if deadline is not None:before(deadline)
    from .s1_progress import acquire,retire
    import os
    stream=acquire(path.open,lambda opened:opened.close(),'xb',buffering=0)
    try:
        operation(np.save,DeadlineSink(stream,deadline),value,allow_pickle=False,deadline=deadline)
        operation(stream.flush,deadline=deadline);operation(os.fsync,stream.fileno(),deadline=deadline);operation(stream.close,deadline=deadline)
    finally:
        if not stream.closed:retire(stream.close)
    from .s1_progress import checked_file_record
    return operation(checked_file_record,path,deadline=deadline)


def png_file(path, value, *, deadline=None):
    from .s1_progress import before, operation
    if deadline is not None:before(deadline)
    import cv2
    from .s1_progress import checked_mkdir
    operation(checked_mkdir,path.parent,parents=True,exist_ok=True,deadline=deadline)
    if operation(path.exists,deadline=deadline):raise ValueError('static mask output exists or cannot be serialized')
    encoded,buffer=operation(cv2.imencode,'.png',value,deadline=deadline)
    if not encoded:raise ValueError('static mask output exists or cannot be serialized')
    from .s1_progress import write_exclusive
    raw=operation(buffer.tobytes,deadline=deadline)
    return write_exclusive(path,raw,deadline=deadline)


def source_row(identity, parent):
    return dict(identity=identity.record(), source_rgb_sha256=parent['rgb']['sha256'],
                K=parent['K'], grid=parent['grid'], valid=parent['valid'])


def cpu_runtime(request, output):
    if not request.get('runtime'):
        return {}
    import importlib.metadata
    import sys
    from .runtime_capture import loaded_runtime
    expected = request['runtime']['versions']
    actual = dict(python=f'{sys.version_info.major}.{sys.version_info.minor}')
    actual.update({key: importlib.metadata.version(key) for key in expected if key != 'python'})
    if actual != expected:
        raise ValueError('CPU worker runtime differs from its frozen inventory')
    return dict(versions=actual, inventory=verify_record(request['runtime']['inventory']),
                loaded_files=loaded_runtime(output / 'loaded-runtime.json'))


def _model_runtime(request):
    from .s1_progress import operation,before
    gated=request.get('job_id')=='S1-calibration-recovery-001'
    run=operation if gated else lambda function,*args,**kwargs:function(*args,**kwargs)
    if gated:before()
    import torch
    if gated:before()
    import torchvision
    if gated:before()
    import sys
    import socket
    from .isolation import deny_vipe
    component = request['component']
    if not run(torch.cuda.is_available):
        raise PermissionError('CUDA device access unavailable for allocated candidate job; no CPU fallback')
    try:
        run(torch.cuda.init)
    except RuntimeError as error:
        raise PermissionError(f'CUDA driver/device initialization failed: {error}') from error
    if 'RTX 4090' not in run(torch.cuda.get_device_name):
        raise ValueError('candidate runtime is not the planned RTX 4090')
    required = request['runtime']['versions']
    actual = dict(python=f'{sys.version_info.major}.{sys.version_info.minor}', torch=torch.__version__,
                  torchvision=torchvision.__version__, numpy=np.__version__)
    for key, expected in required.items():
        if actual.get(key) != expected:
            raise ValueError(f'{key}: required {expected}, found {actual.get(key)}')
    run(random.seed,0)
    run(np.random.seed,0)
    run(torch.manual_seed,0)
    run(torch.cuda.manual_seed_all,0)
    run(torch.cuda.reset_peak_memory_stats)
    def deny_network(*args, **kwargs):
        raise RuntimeError('candidate inference must use frozen offline assets')
    socket.create_connection = deny_network
    socket.socket.connect = deny_network
    socket.socket.connect_ex = deny_network
    helpers = None
    if component == 'S3':
        import importlib.util
        import os
        from .native_helpers import NativeHelpers
        helpers = NativeHelpers(Path(importlib.util.find_spec('triton').origin).parent,
                                os.environ['TMPDIR'], request['forbidden_vipe_roots'])
    if gated:deny_vipe=_s1_deny_vipe
    isolation = (dict(reference_vipe_access=True) if component in ('S0', 'D0') else
                 deny_vipe(request['forbidden_vipe_roots'], native_helpers=helpers))
    return dict(versions=actual, cuda=torch.version.cuda, device=run(torch.cuda.get_device_name), isolation=isolation)



def _s1_deny_vipe(source_roots,native_helpers=None):
    """S1-local isolation equivalent; its audit resolution cannot cross W."""
    import os,sys
    from .isolation import NoViPE
    from .s1_progress import before,operation
    if native_helpers is not None:raise ValueError('S1 has no native subprocess helpers')
    if any(name.split('.')[0] in ('vipe','vipe_ext') for name in sys.modules):
        raise ValueError('ViPE already loaded before standalone isolation')
    roots=[operation(Path(path).resolve) for path in source_roots]
    sys.meta_path.insert(0,NoViPE())
    def audit(event,args):
        if event in ('open','os.listdir','os.scandir','ctypes.dlopen') and args:
            before()
            value=args[0]
            if isinstance(value,(str,bytes,os.PathLike)):
                path=Path(os.fsdecode(value));lexical=Path(os.path.abspath(path))
                before();resolved=lexical.resolve();before()
                if ('prompts' in lexical.parts or 'prompts' in resolved.parts or
                        any(resolved.is_relative_to(root) or lexical.is_relative_to(root) for root in roots)):
                    raise PermissionError('standalone worker attempted prohibited source/extension access')
            before()
        if event=='subprocess.Popen':raise PermissionError('standalone model worker subprocesses are prohibited')
        if event in ('os.system','os.posix_spawn','os.exec','os.fork','os.forkpty'):
            raise PermissionError('standalone worker process escape is prohibited')
    before();sys.addaudithook(audit);before()
    return dict(import_guard=True,source_roots=[str(path) for path in roots],subprocesses=False,native_helpers=None,
        limitation='Python audit guard; native runtime qualification still required')

def segment(request, output, config, *, clock=None):
    from .s1_progress import operation,checked_require_clock
    if request.get('job_id')=='S1-calibration-recovery-001':
        if clock is not None:
            from .s1_progress import before
            before(clock.work_deadline)
        checked_require_clock(clock)
        from .s1_progress import backend_resource_scope
        with backend_resource_scope():
            return operation(_segment,request,output,config,clock=clock,deadline=clock.work_deadline)
    return _segment(request,output,config,clock=clock)


def _segment(request, output, config, *, clock=None):
    from .files import file_record,load_array,read_json,verify_record,write_json
    from .access import RGBLoader
    if request.get('job_id')=='S1-calibration-recovery-001':
        from .s1_progress import checked_file_record as file_record,checked_read_json as read_json,checked_verify_record as verify_record,checked_write_json as write_json
        from .s1_evidence import load_array,S1RGBLoader as RGBLoader
    from .s1_progress import operation, DeadlineSink
    deadline = None
    if request.get('job_id') == 'S1-calibration-recovery-001':
        from .s1_progress import checked_require_clock as require_clock
        require_clock(clock).observe()
        deadline = clock.work_deadline
        import json, os
        from .s1_progress import Publisher
        progress=Publisher(json.loads(os.environ['VIPE_S1_PROGRESS_CONTEXT']),'worker',1,clock=clock,request=request)
    import torch
    from .backends import build_backend
    inputs = operation(read_json,operation(verify_record,request['inputs'],deadline=deadline)['path'],deadline=deadline)
    loader = RGBLoader(inputs['rgb'], config)
    component = request['component']
    branch = request['branch']
    identities = output_identities(config, branch)
    from .sam3_memory import MemoryObserver, CLEANUP, DIAGNOSTIC, compare_partial
    diagnostic = request['job_id'] == DIAGNOSTIC
    if diagnostic:
        if component != 'S3' or branch != 'reconstruction' or request.get('memory_cleanup') != CLEANUP:
            raise ValueError('memory diagnostic must use the prescribed S3 reconstruction cleanup')
        identities = identities[:96]
    repeat = request['job_id'] == 'R-S'
    if repeat:
        if component != 'S1' or branch != 'reconstruction':
            raise ValueError('R-S is fixed to S1 reconstruction')
        identities = [i for i in identities if i.camera == 1 and i.pair_start == 20]
    runtime = operation(_model_runtime,request,deadline=deadline)
    output = Path(output)
    from .s1_progress import checked_mkdir
    operation(checked_mkdir,output,parents=True,exist_ok=False,deadline=deadline)
    write_json(output / 'config.json', request)
    observer = None
    if request.get('memory_cleanup'):
        if component != 'S3' or branch != 'reconstruction' or request['memory_cleanup'] != CLEANUP:
            raise ValueError('unadmitted memory cleanup recipe')
        observer = MemoryObserver(torch, output, diagnostic=diagnostic)
    if request['job_id'] == 'S1-calibration-recovery-001':
        write_json(output / 'initial-runtime.json', runtime)
    if deadline is None:
        adapter = build_backend(component, request['assets'], device='cuda')
    else:
        from .s1_progress import backend_operation
        def backend_gate(function,*args,**kwargs):return backend_operation(function,*args,cleanup_deadline=clock.total_deadline,**kwargs)
        backend_gate.cleanup_deadline=clock.total_deadline
        adapter = operation(build_backend,component,request['assets'],device='cuda',s1_gate=backend_gate,deadline=deadline)
    if observer:
        adapter.memory_observer = observer
    rows, native_seconds = [], 0.
    from .s1_evidence import FirstResultHandoff
    first_result_handoff=FirstResultHandoff()
    size = 1 if branch == 'calibration' else 2
    for offset in range(0, len(identities), size):
        group = identities[offset:offset + size]
        prediction = None
        failure_stage = 'input_load'
        if component == 'S1' and hasattr(getattr(adapter, 'detector', None), 'reset_capture'):
            adapter.detector.reset_capture()
        try:
            if request['job_id'] == 'S1-calibration-recovery-001':
                clock.observe()  # Every input, including a delayed loop transition.
            rgbs = [operation(loader.load,i,deadline=deadline) for i in group]
            footprints = [operation(load_array,loader.row(i)['valid'],deadline=deadline) for i in group]
            torch.cuda.synchronize()
            tick = time.monotonic()
            if observer:
                observer.pair = offset//2+1
                observer.phase('before_pair')
            failure_stage = 'adapter'
            predictions = adapter.segment(rgbs, footprints, frame_ids=[i.frame for i in group])
            if request['job_id'] == 'S1-calibration-recovery-001':
                clock.observe()  # No new serialization after native return at W.
            if observer:
                observer.cleanup()
                observer.phase('after_pair_cleanup')
            torch.cuda.synchronize()
            elapsed = time.monotonic() - tick
            native_seconds += elapsed
            failure_stage = 'output_contract'
            if len(predictions) != size:
                raise ValueError('missing singleton/pair output')
            for identity, prediction, valid in zip(group, predictions, footprints):
                parent = loader.row(identity)
                validate_instances(prediction.labels, prediction.semantics, valid)
                usable = prediction.static(np.zeros_like(valid))
                validate_static(usable, valid)
                stem = output / identity.key()
                row = source_row(identity, parent)
                failure_stage = 'serialization'
                if request['job_id'] == 'S1-calibration-recovery-001':clock.observe()
                row.update(instances=array_file(stem.with_suffix('.npy'), prediction.labels,deadline=deadline),
                    semantics=prediction.semantics, semantic_static=png_file(stem.with_suffix('.png'), usable,deadline=deadline),
                    metadata=prediction.metadata, final_static='assembled once in mask aggregation with M0',
                    native_group_wall_seconds=elapsed, group_size=size)
                if getattr(prediction, 'diagnostics', None):
                    path = stem.with_name(stem.name + '-intermediates.npz')
                    arrays = prediction.diagnostics
                    if any(np.asarray(v).dtype.hasobject for v in arrays.values()):
                        raise ValueError('native intermediates must be non-pickled numeric arrays')
                    if request['job_id'] == 'S1-calibration-recovery-001':clock.observe()
                    if deadline is not None:
                        from .s1_evidence import numeric_file
                        row['diagnostics']=numeric_file(path,arrays,deadline=deadline)
                    else:
                        with path.open('xb',buffering=0) as stream:
                            operation(np.savez_compressed,DeadlineSink(stream,deadline),deadline=deadline,**arrays)
                        row['diagnostics']=operation(file_record,path,deadline=deadline)
                if request['job_id'] == 'S1-calibration-recovery-001':
                    from .s1_progress import publish_segment_row
                    failure_stage = 'first_result' if offset == 0 else 'output_qualification'
                    checks = publish_segment_row(row,request,loader,clock,progress,
                        stem.with_name(stem.name + '-produced-row.json'),
                        stem.with_name(stem.name + '-qualified-row.json'),first=offset == 0)
                rows.append(row)
            if offset == 0:
                if request.get('runtime', {}).get('inventory'):
                    from .runtime_capture import loaded_runtime
                    if deadline is not None:
                        from .s1_progress import loaded_runtime
                    runtime['loaded_files'] = loaded_runtime(output / 'loaded-runtime.json')
                    runtime['installed_inventory'] = verify_record(request['runtime']['inventory'])
                if request['job_id'] == 'S1-calibration-recovery-001':
                    from .s1_evidence import first_record, qualify_runtime
                    failure_stage = 'runtime_qualification'
                    write_json(output / 'partial-runtime.json', runtime)
                    qualify_runtime(runtime, request,deadline=deadline)
                    clock.observe()
                    failure_stage = 'first_result_publication'
                    first_record(request, output, 'passed', clock=clock, rows=rows, runtime=runtime,
                                 checks=checks, raw=[rows[0]['diagnostics']],first_result_handoff=first_result_handoff)
                    clock.observe()
                    progress.runtime['partial-runtime.json']=file_record(output/'partial-runtime.json')
                    progress.first_result=file_record(output/'first-result-qualification.json')
                    progress.publish()
                else:
                    write_json(output / 'first-result-qualification.json', dict(status='passed',
                        count=len(rows), rows=rows, runtime=runtime,
                        note='first real predictions validated inside the allocated job'))
        except BaseException as exc:
            if component == 'S1':
                from .s1_evidence import preserve_failure
                try:
                    preserve_failure(request, output, group[0], exc, adapter=adapter,
                                     prediction=prediction, stage=failure_stage,
                                     parent=loader.row(group[0]), runtime=runtime, clock=clock,first_result_handoff=first_result_handoff)
                except BaseException as persistence_error:
                    exc.add_note(f'S1 evidence publication failed: {persistence_error}')
                if request['job_id'] == 'S1-calibration-recovery-001': progress.close()
            raise
        print(f'{request["job_id"]}: {len(rows)}/{len(identities)} outputs', flush=True)
    validate_membership(rows, identities)
    from .native_helpers import finalize_evidence
    finalize_evidence(runtime.get('isolation', {}))
    result = dict(status='complete', component=component, branch=branch, job_id=request['job_id'], rows=rows,
        configuration=file_record(output / 'config.json'), runtime=runtime, native_wall_seconds=native_seconds,
        peak_allocated_bytes=torch.cuda.max_memory_allocated(), peak_reserved_bytes=torch.cuda.max_memory_reserved())
    if request['job_id'] == 'S1-calibration-recovery-001':
        result['first_result'] = file_record(output / 'first-result-qualification.json')
        from .s1_evidence import validate_result
        result['reservation_clock'] = clock.mapping()
        validate_result(result, request, config, clock=clock,deadline=deadline)
    if observer:
        result['memory'] = observer.finish()
        result['timing_scope'] = 'memory diagnostic only; excluded from benchmark timing' if diagnostic else 'reconstruction including validated lifecycle cleanup and memory observation'
    if diagnostic:
        result['partial_comparison'] = compare_partial(rows, request['partial_output'])
    if repeat:
        baseline = read_json(verify_record(request['baseline'])['path'])
        by_key = {Identity(**r['identity']).key(): r for r in baseline['rows']}
        result['repeat'] = [dict(identity=r['identity'],
            differing_pixels=int((load_array(r['instances']) != load_array(by_key[Identity(**r['identity']).key()]['instances'])).sum()))
            for r in rows]
        result['baseline'] = request['baseline']
    write_json(output / 'result.json', result)
    if request['job_id'] == 'S1-calibration-recovery-001': progress.close()


def predict_depth(request, output, config):
    import cv2
    import torch
    from .backends import build_backend
    from .scale import evaluate
    inputs = read_json(verify_record(request['inputs'])['path'])
    component = request['component']
    repeat = request['job_id'] == 'R-D'
    frame = config['scale_fit_frame'] if request['role'] == 'fit' else config['scale_check_frame']
    rows = [r for r in inputs['depth'] if r['identity']['frame'] == frame]
    if repeat:
        if component != 'D1' or frame != 100:
            raise ValueError('R-D fixed to D1 camera1 frame100')
        rows = [r for r in rows if r['identity']['camera'] == 1]
    runtime = _model_runtime(request)
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    write_json(output / 'config.json', request)
    if request['job_id'] == 'S1-calibration-recovery-001':
        write_json(output / 'initial-runtime.json', runtime)
    adapter = build_backend(component, request['assets'], device='cuda')
    predictions, result_rows = {}, []
    for row in sorted(rows, key=lambda r: r['identity']['camera']):
        identity = Identity(**row['identity'])
        rgb = cv2.cvtColor(cv2.imread(verify_record(row['rgb'])['path']), cv2.COLOR_BGR2RGB)
        valid = load_array(row['valid'])
        torch.cuda.synchronize()
        tick = time.monotonic()
        prediction = adapter.predict(rgb, np.asarray(row['K'], np.float64), valid)
        torch.cuda.synchronize()
        elapsed = time.monotonic() - tick
        validate_depth(prediction.depth, prediction.valid, valid)
        path = output / f'camera{identity.camera}-frame{frame}.npz'
        arrays = dict(depth=prediction.depth, valid=prediction.valid)
        if prediction.confidence is not None:
            arrays['confidence'] = prediction.confidence
        if prediction.raw_depth is not None:
            arrays['raw_depth'] = prediction.raw_depth
        with path.open('xb') as stream:
            np.savez_compressed(stream, **arrays)
        predictions[identity.camera] = file_record(path)
        result_rows.append(dict(**source_row(identity, row), depth=predictions[identity.camera],
                                metadata=prediction.metadata, native_wall_seconds=elapsed))
        if len(result_rows) == 1:
            if request.get('runtime', {}).get('inventory'):
                from .runtime_capture import loaded_runtime
                runtime['loaded_files'] = loaded_runtime(output / 'loaded-runtime.json')
                runtime['installed_inventory'] = verify_record(request['runtime']['inventory'])
            write_json(output / 'first-result-qualification.json', dict(status='passed', row=result_rows[0], runtime=runtime))
        print(f'{request["job_id"]}: {len(result_rows)}/{len(rows)} depths', flush=True)
    component_hash = object_hash(dict(component=component, assets=request['assets'], runtime=request['runtime']))
    result = dict(status='complete', component=component, component_sha256=component_hash,
                  rows=result_rows, runtime=runtime, configuration=file_record(output / 'config.json'),
                  peak_allocated_bytes=torch.cuda.max_memory_allocated(), peak_reserved_bytes=torch.cuda.max_memory_reserved())
    if not repeat:
        scale = evaluate(rows, predictions, config,
                         provenance=dict(component=component, component_sha256=component_hash,
                                         configuration=file_record(output / 'config.json')),
                         frozen_fit=request.get('frozen_fit'))
        scale.update(component=component, component_sha256=component_hash)
        write_json(output / 'scale.json', scale)
        result['scale'] = file_record(output / 'scale.json')
    else:
        baseline = read_json(verify_record(request['baseline'])['path'])
        first = next(r for r in baseline['rows'] if r['identity']['camera'] == 1)
        from .aggregation import compare_depth
        result['repeat'] = compare_depth(first, result_rows[0], rows[0])
        result['baseline'] = request['baseline']
    write_json(output / 'result.json', result)


def motion(request, output, config):
    import cv2
    from .motion import RoleMOG2, changing
    method = request['component']
    inputs = read_json(verify_record(request['inputs'])['path'])
    loader = RGBLoader(inputs['rgb'], config)
    cv2.setNumThreads(8)
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    write_json(output / 'config.json', request)
    wanted = output_identities(config, 'calibration') + output_identities(config, 'reconstruction')
    rows, cache = [], {}
    if method == 'M2':
        desired = {(i.branch, i.camera, i.frame) for i in wanted}
        for branch, cameras, ranges in [('calibration', range(34), [(50, 150), (150, 200)]),
                                        ('reconstruction', training_cameras(config), [(0, 50)])]:
            for camera in cameras:
                for lo, hi in ranges:
                    state = RoleMOG2(branch, camera, lo)
                    for frame in range(lo, hi):
                        identity = Identity(branch, camera, frame)
                        parent = loader.row(identity)
                        mask, native, context = state.advance(identity, loader.load(identity), parent['rgb']['sha256'])
                        if (branch, camera, frame) in desired:
                            # Serialize once; do not retain thousands of full-resolution arrays in RAM.
                            stem = output / identity.key()
                            cache[branch, camera, frame] = (array_file(stem.with_suffix('.npy'), mask),
                                array_file(stem.with_name(stem.name + '-native.npy'), native), context)
    for identity in wanted:
        parent = loader.row(identity)
        if method == 'M2':
            mask_record, native_record, context = cache[identity.branch, identity.camera, identity.frame]
        else:
            mask, context = changing(identity, method, loader)
            mask_record = array_file(output / (identity.key() + '.npy'), mask)
            native_record = None
        rows.append(dict(**source_row(identity, parent), changing=mask_record,
                         native=native_record, metadata=context))
    validate_membership(rows, wanted)
    write_json(output / 'result.json', dict(status='complete', component=method, rows=rows,
               configuration=file_record(output / 'config.json'), runtime=cpu_runtime(request, output),
               independent_motion_truth=False))


def neighbors(request, output, config):
    from .neighbors import rank
    inputs = read_json(verify_record(request['inputs'])['path'])
    scene = read_json(verify_record(inputs['map'])['path'])
    cameras = {int(k): v for k, v in scene['cameras'].items()}
    training = training_cameras(config)
    tracks = {int(k): set(v) for k, v in scene['tracks'].items() if int(k) in training}
    points = {int(k): v for k, v in scene['points'].items()}
    footprints = {int(k): load_array(v) for k, v in scene['footprints'].items()}
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    write_json(output / 'config.json', request)
    rows = [dict(reference=c, **rank(request['component'], c, tracks, training=training,
                points=points, cameras=cameras, footprints=footprints)) for c in training]
    write_json(output / 'result.json', dict(status='complete', component=request['component'], records=rows,
        inputs=request['inputs'], map=inputs['map'], runtime=cpu_runtime(request, output),
        configuration=file_record(output / 'config.json'),
        all_references_have_three_neighbors=all(r['status'] == 'complete' for r in rows)))


def run(request, output, config, *, clock=None):
    component = request['component']
    if component.startswith('S'):
        return segment(request, output, config, clock=clock)
    if component.startswith('D'):
        return predict_depth(request, output, config)
    if component.startswith('M'):
        return motion(request, output, config)
    if component.startswith('N'):
        return neighbors(request, output, config)
    raise ValueError('unknown component worker')

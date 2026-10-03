"""Fixed native stage factory entered only inside a registered DO child.

No injected runtime, matcher or guard can turn fixture evidence into actual work.
All process supervision and ledger writes belong to the external dispatcher.
"""
import argparse
import io
import time

import numpy as np

from .files import file_record, read_json, safe_path, verify_record, write_json, object_hash


def execute(invocation_record):
    """Execute the exact admitted invocation in its registered process group."""
    if verify_record(invocation_record) != invocation_record:
        raise ValueError('immutable actual invocation required')
    invocation = read_json(invocation_record['path'])
    if invocation.get('record_kind') != 'actual':
        raise ValueError('actual invocation required; fixtures cannot be promoted')
    request_record = invocation['request']
    if verify_record(request_record) != request_record:
        raise ValueError('changed actual request')
    request = read_json(request_record['path'])
    if request.get('record_kind') != 'actual':
        raise ValueError('actual request required; invocation labels cannot promote fixtures')
    arm, phase = invocation['arm'], invocation['phase']
    from .final_render_admission import worker_binding
    binding = worker_binding(invocation_record,request,arm,phase)
    # Re-read only the checked payload, not caller-supplied factories/configuration.
    invocation = binding['invocation']
    from .final_render_workers import train, render, _Budget, _publish
    if phase in ('train','render'):
        from .final_render_native import NativeFreeTimeRuntime
        checkout = safe_path(request['bindings']['preset']['path']).resolve().parents[1]
        runtime = NativeFreeTimeRuntime(request,arm,checkout)
        return (train if phase == 'train' else render)(request,arm,invocation['parent_result'],
            invocation['initializer'],invocation['output'],runtime,invocation_record=invocation_record)
    start = time.monotonic()
    output = safe_path(invocation['output']).resolve()
    if phase == 'geometry':
        from .final_render_geometry import run
        from .final_render_matcher import NativeGeometryBackend
        geometry = run(request,arm,output,NativeGeometryBackend(binding['matcher_runtime']),
            invocation_record=invocation_record)
        budget = _Budget(request,phase,output,time.monotonic,start,invocation_record)
        budget.usage = {name:geometry[name] for name in ('peak_device_bytes','cpu_workers_used')}
        budget.cleanup_confirmed = True  # Fixed geometry.run closes its matcher before return.
        return _publish(request,arm,None,budget,dict(geometry=geometry['geometry'],coverage_edges=geometry['coverage_edges']))
    if phase != 'initializer':
        raise ValueError('unknown admitted worker phase')
    from .final_render_actual_result import validate_actual_worker_result
    from .final_render_initializer import assemble
    from .final_render_adapter import prepare_model_input
    parent = invocation['parent_result']
    previous = validate_actual_worker_result(request,arm,'geometry',read_json(parent['path']))
    width = invocation.get('voxel_width')
    if type(width) is not dict or verify_record(width) != width:
        raise ValueError('exact bound voxel width required')
    output.mkdir(parents=True,exist_ok=False)
    budget = _Budget(request,phase,output,time.monotonic,start,invocation_record)
    budget.usage = dict(peak_device_bytes=0,cpu_workers_used=1)
    try:
        budget.check(30.)
        arrays, assembly = assemble(request,arm,previous['geometry'],width)
        _, native_input = prepare_model_input(request,arm,assembly['initializer_receipt'],arrays)
        budget.check(30.)
        # Exclusive immutable publication; never overwrite an earlier attempt.
        buffer = io.BytesIO()
        np.savez_compressed(buffer,**arrays)
        if len(buffer.getbuffer())+2**20 > request['artifact_bytes_limit']:
            raise ValueError('initializer artifact storage limit exhausted')
        path = output/'initializer.npz'
        with path.open('xb') as stream:
            stream.write(buffer.getbuffer())
        archive = file_record(path)
        write_json(output/'assembly.json',assembly)
        write_json(output/'native-input.json',native_input)
        bundle = dict(schema='plan069-final-render-prepared-initializer/v1',record_kind='actual',arm=arm,
            request_sha256=object_hash(request),archive=archive,initializer_receipt=assembly['initializer_receipt'],
            execution_authorized=False,native_adapter_qualified=False)
        write_json(output/'initializer.json',bundle)
        budget.cleanup_confirmed = True
        return _publish(request,arm,parent,budget,dict(initializer=file_record(output/'initializer.json'),
            assembly=file_record(output/'assembly.json'),native_input=file_record(output/'native-input.json')))
    except BaseException as error:
        if not hasattr(error,'worker_failure'):
            budget.cleanup_confirmed = True
            budget.failure(arm,error)
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--invocation',required=True)
    parser.add_argument('--release-file',required=True)
    arguments = parser.parse_args()
    invocation = file_record(arguments.invocation)
    release = safe_path(arguments.release_file).resolve()
    started = time.monotonic()
    while not release.exists():
        if time.monotonic()-started >= 30.:
            raise RuntimeError('registered worker release deadline exceeded')
        time.sleep(.05)
    gate = read_json(release)
    if gate != dict(schema='plan069-final-render-actual-release/v1',invocation=invocation):
        raise ValueError('exact immutable invocation release required')
    execute(invocation)


if __name__ == '__main__':
    main()

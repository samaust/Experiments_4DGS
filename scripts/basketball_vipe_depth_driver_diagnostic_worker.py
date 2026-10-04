"""Driver init only under the unchanged native guard; never load a model."""
import argparse
import importlib.util
import json
from pathlib import Path
import sys


def main(request_path):
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from vipe_benchmark.depth_driver_diagnostic import JOB, validate_request
    from vipe_benchmark.depth_admission import local_source_records
    from vipe_benchmark.files import file_record, read_json, write_json
    from vipe_benchmark.ledger import Ledger
    from vipe_benchmark.config import load
    record = file_record(request_path)
    request, _ = validate_request(record, current_sources=local_source_records('D6'))
    if request['record_kind'] != 'actual':
        raise ValueError('fixture cannot initialize actual CUDA')
    state = Ledger(request['ledger_path'], load()).states().get(JOB, {})
    if state.get('event') != 'reserve' or state.get('command') != request['command'] or state.get('evidence') != dict(request=record):
        raise ValueError('active exact diagnostic reservation required')
    output = Path(request['output']); output.mkdir(exist_ok=False)
    spec = importlib.util.spec_from_file_location('exact_retained_guard', request['guard']['path'])
    assert spec is not None and spec.loader is not None
    guard = importlib.util.module_from_spec(spec); spec.loader.exec_module(guard)
    guard.deny_native_network()
    guard.install_guards()
    from vipe_benchmark.files import verify_record
    dependencies = read_json(request['dependencies']['path'])
    for row in dependencies['files']:
        verify_record(row)
    import torch
    if torch.__version__ != '2.6.0+cu124':
        raise ValueError('diagnostic Torch version differs from accepted D6 recipe')
    # Init needs no forward, allocations or benchmark. Fail if Python callers try them.
    def denied(*unused_args, **unused_kwargs):
        raise PermissionError('driver diagnostic prohibits model/inference/allocation')
    torch.nn.Module._call_impl = denied
    for name in ('tensor', 'empty', 'zeros', 'ones', 'rand', 'randn', 'load'):
        setattr(torch, name, denied)
    error = None
    try:
        torch.cuda.init()
    except Exception as caught:
        error = dict(type=type(caught).__name__, message=str(caught)[:2048])
    result = dict(schema='plan069-D6-driver-diagnostic-result/v1', record_kind='actual',
        status='captured', request=record, network_guard=request['guard'],
        cuda_init_outcome='error' if error else 'initialized', error=error,
        model_loaded=False, inference=False, benchmarks=False,
        tensor_peak_allocated_bytes=torch.cuda.max_memory_allocated() if torch.cuda.is_initialized() else 0,
        trace_path=str(output.with_suffix('.syscalls.log')))
    write_json(output / 'result.json', result)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('--request', required=True)
    main(parser.parse_args().request)

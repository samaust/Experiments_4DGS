"""Root-only immutable D9 CPU request preparation; never execute models or filters."""
import argparse
import importlib.util
import json
from pathlib import Path
import signal
import time


def main():
    started = time.monotonic()
    def deadline(signum, frame):
        raise TimeoutError('CPU request preparation ten-second deadline')
    signal.signal(signal.SIGALRM, deadline)
    signal.setitimer(signal.ITIMER_REAL, 10)
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('root', 'run', 'source-review', 'cpu-qualification', 'cpu-admission', 'authorization', 'output', 'wrapper-output', 'capture-output'):
        parser.add_argument('--' + name, required=True)
    args = parser.parse_args()
    here = Path(__file__).resolve().parent
    spec = importlib.util.spec_from_file_location('video_wrapper', here/'wrapper.py')
    if spec is None or spec.loader is None:
        raise ValueError('wrapper loader unavailable')
    wrapper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(wrapper)
    root, run, out = (Path(value).absolute() for value in (args.root, args.run, args.output))
    for path in (root,run,out,Path(args.wrapper_output).absolute(),Path(args.capture_output).absolute()):
        wrapper.require(path == path.resolve() and 'prompts' not in path.parts, 'unsafe preparation path')
    wrapper.require(not out.exists() and not Path(args.wrapper_output).exists() and not Path(args.capture_output).exists(), 'all outputs must be fresh')
    setup = wrapper.record(run/'jobs/plan069-D9-setup-recovery-002/result.json')
    request = wrapper.record(run/'requests/plan069-D9-setup-recovery-002.json')
    setup_doc = wrapper.read_json(setup['path'])
    runtime = wrapper.read_json(setup_doc['runtime_environment']['path'])
    request_doc = wrapper.read_json(request['path'])
    interpreter = runtime['python_executable']
    command = [interpreter, '-I', '-B', str(root/'docs/research/vipe-alternatives/plan031-execution/video-cpu-method-003/producer.py'), 'capture', '--root', str(root), '--candidate', 'D9', '--setup', setup['path'], '--setup-request', request['path'], '--authorization', str(Path(args.authorization).absolute()), '--ledger', str(run/'ledger.jsonl'), '--output', str(Path(args.capture_output).absolute()), '--seconds', '140', '--artifact-bytes', str(64*1024*1024)]
    bindings = dict(setup=setup, setup_request=request, runtime_recipe=request_doc['runtime_environment']['recipe'], source_review=wrapper.record(args.source_review), cpu_qualification=wrapper.record(args.cpu_qualification), cpu_admission=wrapper.record(args.cpu_admission), authorization=wrapper.record(args.authorization))
    for row in bindings.values():
        wrapper.require(wrapper.record(row['path']) == row, 'changed immutable binding')
    review = wrapper.read_json(args.source_review)
    config = dict(schema='plan069-video-parent-cpu-request/v1', candidate='D9', cpu_accounting_owner='D9', admitted=True, charge_owner='root', cpu_workers=7, seconds=180, cleanup_seconds=20, bootstrap=wrapper.record(Path(interpreter).resolve()), interpreter_invocation=interpreter, method=wrapper.record(command[3]), root=str(root), output=str(Path(args.wrapper_output).absolute()), command=command, ledger=str(run/'ledger.jsonl'), bindings=bindings, accepted_setup_sha256=setup['sha256'], root_source_commit=review.get('root_source_commit'), disk_roots=[dict(role=role,path=str(path),maximum_total_bytes=210*1024**3,maximum_delta_bytes=64*1024**2) for role,path in [('global',run),('candidate',run),('runtime-cache',Path(setup_doc['runtime_environment']['path']).parent)]])
    wrapper.verify_admission(config,review)
    out.mkdir(parents=True,exist_ok=False)
    wrapper.write(out/'request.json',config)
    wrapper.write(out/'preparation.json',dict(schema='plan069-video-native-cpu-preparation/v1',cpu_accounting_owner='D9',elapsed_seconds=time.monotonic()-started,request=wrapper.record(out/'request.json'),no_models=True,no_filters=True,no_ledger_mutation=True))
    signal.setitimer(signal.ITIMER_REAL,0)
    print(json.dumps(dict(request=str(out/'request.json'), command=[interpreter,'-I','-B',str(root/'docs/research/vipe-alternatives/plan031-execution/video-native-wrapper-001/wrapper.py'),'--request',str(out/'request.json')])) )


if __name__ == '__main__':
    main()

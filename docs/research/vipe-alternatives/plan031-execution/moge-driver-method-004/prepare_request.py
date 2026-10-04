"""Bind proposed D6 driver qualification or accepted CPU finalization; never run it."""
import argparse
import hashlib
import json
from pathlib import Path


def record(path):
    path=Path(path).absolute()
    if 'prompts' in path.parts or 'prompts' in path.resolve().parts:
        raise ValueError('prompts prohibited')
    return dict(path=str(path),bytes=path.stat().st_size,sha256=hashlib.sha256(path.read_bytes()).hexdigest())


def read(path):
    return json.loads(Path(path).read_text())


def prepare(args):
    root,run=Path(args.root).absolute(),Path(args.run).absolute()
    source_record=record(args.source_review)
    source=read(source_record['path'])
    if source.get('candidate')!='D6' or source.get('status')!='passed' or not source.get('reviewer'):
        raise ValueError('passed current post-setup D6 source review required')
    for item in source['local_sources']:
        if record(item['path'])!=item:
            raise ValueError('reviewed current helper changed')
    method=root/'docs/research/vipe-alternatives/plan031-execution/moge-driver-method-004/producer.py'
    setup_path=run/'jobs/plan069-D6-setup-001/result.json'
    setup_record=record(setup_path)
    setup=read(setup_path)
    if args.mode=='driver':
        if not all((args.authorization,args.cpu_validation)):
            raise ValueError('separate user DO and combined CPU qualification required')
        interpreter=setup['python_executable']
        request=dict(schema='plan069-D6-driver-qualification-request/v1',candidate='D6',record_kind='actual',
            job_id='plan069-D6-driver-qualification-001',root=str(root),ledger_path=str(run/'ledger.jsonl'),
            review=record(root/'docs/specs/plan031-execution/D6-driver-qualification-review-001.json'),
            authorization=record(args.authorization),cpu_validation=record(args.cpu_validation),source_review=source_record,
            setup=setup_record,setup_request=record(run/'requests/plan069-D6-setup-001.json'),
            setup_dispatch=record(root/'docs/research/vipe-alternatives/plan031-20260913T032700Z/plan069-D6-setup-001.json'),
            worker=record(method),interpreter_invocation=interpreter,executable=record(Path(interpreter).resolve()),
            output=str(Path(args.producer_output).absolute()))
        request['command']=[interpreter,'-I','-B',str(method),'driver-child','--request',str(Path(args.output).absolute()),
            '--output',request['output']]
        if read(args.authorization).get('status')!='DO':
            raise ValueError('REVIEW does not authorize driver qualification')
    else:
        if not all((args.driver_result,args.commercial_assessment,args.disk_roots,args.interpreter,args.wrapper_output)):
            raise ValueError('accepted driver result, commercial evidence and CPU wrapper bounds required')
        native_record=record(args.driver_result)
        native=read(native_record['path'])
        capture=Path(args.driver_result).absolute().parent
        assessment_record=record(args.commercial_assessment)
        assessment=read(assessment_record['path'])
        finish_record=record(capture/'finish.json')
        ledger_path=str(run/'ledger.jsonl')
        bootstrap=str(Path(args.interpreter).absolute())
        bindings=dict(driver_result=native_record,driver_finish=finish_record,driver_request=native['request'],
            dependency_manifest=native['dependency_manifest'],commercial_assessment=assessment_record,
            permission_report=assessment['permission_report'],runtime_recipe=source['runtime_recipe'],source_review=source_record)
        command=[bootstrap,'-B',str(method),'finalize','--root',str(root),'--candidate','D6','--capture',str(capture),
            '--finish',finish_record['path'],'--ledger',ledger_path,'--commercial-assessment',assessment_record['path'],
            '--source-review',source_record['path'],'--output',str(Path(args.producer_output).absolute())]
        request=dict(schema='plan069-moge-driver-parent-finalize-request/v1',candidate='D6',root=str(root),
            root_source_commit=source['root_source_commit'],accepted_setup_sha256=setup_record['sha256'],
            qualification_ledger=ledger_path,bootstrap=record(Path(bootstrap).resolve()),interpreter_invocation=bootstrap,
            seconds=180,cleanup_seconds=20,cpu_workers=7,admitted=True,charge_owner='root',
            bindings=bindings,command=command,method=record(method),output=str(Path(args.wrapper_output).absolute()),
            disk_roots=read(args.disk_roots))
    with Path(args.output).open('x') as stream:
        json.dump(request,stream,indent=2)
        stream.write('\n')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode',choices=('driver','finalize'),required=True)
    for name in ('root','run','source-review','producer-output','output'):
        parser.add_argument('--'+name,required=True)
    for name in ('authorization','cpu-validation','driver-result','commercial-assessment','disk-roots','interpreter','wrapper-output'):
        parser.add_argument('--'+name)
    prepare(parser.parse_args())

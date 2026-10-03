"""Dispatch fixed native workers under immutable DO authority.

This interface prepares no approvals and exposes no runtime/probe overrides.
The shared admission ledger owns every allocation; CPU fixtures use the separate
fixture dispatcher.
"""
from pathlib import Path
import time

from .files import file_record, read_json, safe_path, verify_record, write_json


def _bound(record):
    if type(record) is not dict or set(record) != {'path','sha256','bytes'} or verify_record(record) != record:
        raise ValueError('exact unchanged dispatch evidence required')
    return read_json(record['path'])


def native_command(interpreter, worker, invocation_path, release_path):
    """Literal approved worker command, including the registration handshake."""
    return [str(safe_path(interpreter['path']).resolve()), str(safe_path(worker['path']).resolve()),
            '--invocation', str(safe_path(invocation_path).resolve()),
            '--release-file', str(safe_path(release_path).resolve())]


class ActualDispatcher:
    def __init__(self, envelope_record, ledger):
        envelope = _bound(envelope_record)
        if envelope.get('schema') != 'plan069-final-render-do/v1' or envelope.get('record_kind') != 'actual' or envelope.get('mode') != 'DO':
            raise ValueError('actual DO envelope required; fixtures cannot authorize native dispatch')
        from .extended_final_render_contract import parse_request, validate_budget_configuration
        request = parse_request(_bound(envelope['request']))
        if request['record_kind'] != 'actual':
            raise ValueError('actual REVIEW request required')
        validate_budget_configuration(request,ledger.config)
        self.envelope_record, self.ledger = envelope_record, ledger

    def dispatch(self, arm, phase, invocation_path, output, *, parent_result=None,
                 initializer=None, voxel_width=None):
        """Consume one approved slot and supervise its fixed native worker.

        Invocation and control evidence are immutable, including failed
        preparations. Reattempts require an approved fresh allocation identity.
        """
        from .extended_final_render_contract import parse_request
        from .final_render_admission import reserve, validate_dispatch_invocation
        from .final_render_actual_control import run_control
        from .final_render_actual_supervisor import supervise_reserved
        from .final_render_contract import PHASES

        envelope = _bound(self.envelope_record)
        request = parse_request(_bound(envelope['request']))
        if request['record_kind'] != 'actual' or envelope.get('record_kind') != 'actual':
            raise ValueError('actual dispatch evidence required')
        if arm not in request['compositions'] or phase not in PHASES:
            raise ValueError('unknown native arm/phase')
        invocation_path, output = safe_path(invocation_path).resolve(), safe_path(output).resolve()
        run_root = self.ledger.path.resolve().parent
        if not invocation_path.is_relative_to(run_root) or not output.is_relative_to(run_root):
            raise ValueError('dispatch files must remain inside the charged study root')
        release_path = invocation_path.with_name(invocation_path.stem+'-release.json')
        control_root = invocation_path.with_name(invocation_path.stem+'-control')
        if any(p.exists() or p.is_symlink() for p in (invocation_path,output,release_path,control_root)):
            raise FileExistsError('fresh immutable dispatch paths required')
        if output in (invocation_path,release_path,control_root) or output in invocation_path.parents or output in control_root.parents:
            raise ValueError('worker output cannot contain dispatch control files')
        if phase == 'geometry' and any(v is not None for v in (parent_result,initializer,voxel_width)):
            raise ValueError('geometry must start without predecessor or initializer')
        if phase != 'geometry':
            _bound(parent_result)
        if phase == 'initializer':
            _bound(voxel_width)
            if initializer is not None:
                raise ValueError('initializer phase cannot consume a prepared initializer')
        elif voxel_width is not None:
            raise ValueError('voxel width belongs only to initializer preparation')
        if phase in ('train','render'):
            _bound(initializer)
        worker = file_record(Path(__file__).resolve().parents[1]/'final-render-actual-worker.py')
        command = native_command(envelope['interpreter'],worker,invocation_path,release_path)
        if envelope['commands'].get(arm+'/'+phase) != command:
            raise ValueError('fixed native command differs from approved command')
        if worker not in envelope['source_files']:
            raise ValueError('fixed native worker is absent from approved source closure')
        for record in [envelope['interpreter'],*envelope['source_files']]:
            if verify_record(record) != record:
                raise ValueError('approved interpreter or source bytes changed')
        invocation = dict(schema='plan069-final-render-actual-invocation/v1',record_kind='actual',
            envelope=self.envelope_record,request=envelope['request'],arm=arm,phase=phase,
            parent_result=parent_result,initializer=initializer,voxel_width=voxel_width,
            output=str(output),worker=worker,interpreter=envelope['interpreter'],
            source_files=envelope['source_files'],ledger_path=str(self.ledger.path.resolve()),
            run_root=str(run_root),release_path=str(release_path))
        write_json(invocation_path,invocation)
        invocation_record = file_record(invocation_path)
        control_root.mkdir(parents=True,exist_ok=False)
        def live_probe():
            measured = run_control('sample',invocation_record,control_root/'admission',seconds=15.)
            return {key:measured[key] for key in ('artifact_bytes','download_bytes','free_disk_bytes',
                    'device_bytes','gpu_pids','cpu_workers_used','cleanup_confirmed','observed_unix')}
        reservation = reserve(self.envelope_record,self.ledger,arm,phase,command,
                              probe=live_probe,parent_result=parent_result)
        start = reservation['monotonic_start']
        try:
            validate_dispatch_invocation(invocation_record,self.ledger,reservation)
        except BaseException as error:
            failure = dict(record_kind='actual',invocation=invocation_record,
                           error_class=type(error).__name__,message=str(error),
                           cleanup_confirmed=True,cleanup_uncertain=False)
            write_json(control_root/'prelaunch-failure.json',failure)
            self.ledger.finish(reservation['job_id'],'failed',time.monotonic()-start,
                               **failure)
            raise
        return supervise_reserved(self.ledger,reservation,command,output,invocation_record,
                                  release_path=release_path)

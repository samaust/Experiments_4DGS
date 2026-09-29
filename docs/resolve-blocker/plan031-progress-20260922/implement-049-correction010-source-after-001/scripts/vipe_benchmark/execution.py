"""Admission and dependency-aware dispatch of immutable matrix requests."""
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import time

from .config import ROOT, execution_order, jobs, load
from .files import file_record, read_json, verify_record, write_json
from .ledger import Ledger
from .runtime import ENVIRONMENTS, TARGETS, historical_assets
from .supervisor import directory_bytes, gpu_reading, supervise, SupervisionFailure


def result_path(local, job):
    return (local / job if job in ('prepare', 'annotations') else local / 'jobs' / job) / 'result.json'


def result_record(local, job):
    path = result_path(local, job)
    ledger = Ledger(local / 'ledger.jsonl', load())
    state = ledger.states().get(job, {})
    if state.get('event') != 'finish' or state.get('status') != 'complete' or not state.get('result'):
        recoveries = [e for e in ledger.events() if e['event'] == 'component_recovery_authorized'
                      and e['original_job_id'] == job]
        if job == 'S1-calibration' and len(recoveries) > 1:
            raise ValueError('S1 recovery must have one authorization')
        if recoveries:
            record = result_record(local, recoveries[-1]['job_id'])
            if record:
                result = read_json(record['path'])
                component, branch = job.split('-', 1)
                if (result.get('component') != component or result.get('branch') != branch or
                        len(result.get('rows', [])) != (510 if branch == 'calibration' else 840)):
                    raise ValueError('component recovery result has wrong original arm')
                return record
        if job == 'S3-reconstruction':
            recoveries = [e for e in ledger.events() if e['event'] == 'reconstruction_recovery_authorized']
            if recoveries:
                record = result_record(local, recoveries[-1]['job_id'])
                if record:
                    result = read_json(record['path'])
                    if result.get('component') != 'S3' or result.get('branch') != 'reconstruction' or len(result.get('rows', [])) != 840:
                        raise ValueError('recovery result differs from S3 reconstruction contract')
                    return record
        return None
    if job == 'S1-calibration-recovery-001':
        from .s1_recovery import resolved_result
        resolved_result(local, load(), ledger.events(), state)
    record = state['result']
    if Path(record['path']).resolve() != path.resolve():
        raise ValueError('ledger result identity differs from allocated job')
    verify_record(record)
    if read_json(record['path']).get('status') != 'complete':
        raise ValueError('successful ledger entry contains an incomplete worker result')
    return record


def result_artifact(local, job, field):
    """Bind downstream artifacts to a successfully validated, ledger-frozen result."""
    result = result_record(local, job)
    if not result:
        return None
    record = read_json(result['path']).get(field)
    if not isinstance(record, dict) or 'path' not in record:
        raise ValueError(f'{job}: completed result lacks {field} artifact')
    verify_record(record)
    return record


def qualification_record(local):
    path = local / 'qualification/result.json'
    charges = [e for e in Ledger(local / 'ledger.jsonl', load()).events()
               if e['event'] == 'cpu_preparation_charge' and
               Path(e['evidence']['path']).resolve() == path.resolve()]
    if not charges:
        return None
    record = charges[-1]['evidence']
    verify_record(record)
    if read_json(record['path']).get('status') != 'complete':
        raise ValueError('existing-runtime qualification did not complete')
    return record


def qualified_existing(local):
    record = qualification_record(local)
    if not record:
        return None
    result = read_json(record['path'])
    events = Ledger(local / 'ledger.jsonl', load()).events()
    supplements = [e for e in events if e['event'] == 'cpu_preparation_charge' and
                   Path(e['evidence']['path']).parent.name == 'qualification-full-inventory']
    if supplements:
        supplement = read_json(verify_record(supplements[-1]['evidence'])['path'])
        if supplement['parent'] != record or supplement['status'] != 'complete':
            raise ValueError('full inventory does not bind the original successful qualification')
        result['runtime'] = supplement['runtime']
    return result


def aggregate_record(local, stage, *, artifact=False):
    expected = local / f'jobs/aggregate-{stage}/result.json'
    events = Ledger(local / 'ledger.jsonl', load()).events()
    matched = [e for e in events if e['event'] in ('checkpoint', 'finish') and e.get('job_id') == 'aggregate'
               and not e.get('error') and e.get('result') and
               Path(e['result']['path']).resolve() == expected.resolve() and
               (e['event'] == 'checkpoint' or e.get('status') == 'complete')]
    if not matched:
        return None
    record = matched[-1]['result']
    verify_record(record)
    doc = read_json(record['path'])
    if doc.get('status') != 'complete':
        raise ValueError('aggregation checkpoint is not complete')
    verify_record(doc['evidence'])
    return doc['evidence'] if artifact else record


def resources(local, *, gpu=False):
    from .budgets import budget_snapshot
    reading = budget_snapshot(local)
    if gpu:
        reading.update(gpu_reading())
    return reading


def _qualify_existing(local, docs, config, deadline):
    """Read-only E0/E8 inventories: no rebuild and no model/GPU smoke run."""
    output = local / 'qualification'
    output.mkdir(parents=True, exist_ok=False)
    tick = time.monotonic()
    assets, historical_parent = historical_assets()
    write_json(output / 'historical-assets.json', dict(assets=assets, parent=historical_parent))
    runtimes = {}
    for name, python in [('E0', Path(assets['vipe_source']['path']) / '.venv/bin/python'),
                         ('E8', ROOT / '.local/envs/roma/bin/python')]:
        path = output / f'{name}-inventory.json'
        subprocess.run([str(python), str(ROOT / 'scripts/vipe_benchmark/runtime_inventory.py'), '--output', str(path)],
                       check=True, timeout=max(.01, deadline - time.monotonic() - 2.))
        inventory = read_json(path)
        if any(inventory['versions'].get(k) != v for k, v in TARGETS[name].items()):
            raise ValueError(f'{name}: existing runtime differs from frozen target')
        runtimes[name] = dict(python=str(python), versions=TARGETS[name], inventory=file_record(path))
    from edgs_source import ROMA_PIN, ROMA_WEIGHTS
    roma = ROOT / '.local/RoMa-edgs'
    if subprocess.check_output(['git', '-C', str(roma), 'rev-parse', 'HEAD'], text=True).strip() != ROMA_PIN:
        raise ValueError('historical RoMa source pin changed')
    if subprocess.check_output(['git', '-C', str(roma), 'status', '--porcelain', '--untracked-files=no'], text=True).strip():
        raise ValueError('historical RoMa source modified')
    weights = [file_record(ROOT / '.local/weights/roma-edgs' / n, h) for n, h in ROMA_WEIGHTS.items()]
    result = dict(status='complete', runtime=runtimes, assets=file_record(output / 'historical-assets.json'),
        roma=dict(checkout=str(roma), weights=str(ROOT / '.local/weights/roma-edgs'),
                  revision=ROMA_PIN, files=weights),
        host=dict(platform=platform.platform(), os_release=file_record('/etc/os-release')),
        gpu_qualification='deferred to exclusive-device admission and first allocated result',
        wall_seconds=time.monotonic() - tick)
    write_json(output / 'result.json', result)
    write_json(docs / 'existing-runtime-qualification.json', result)
    return result


def qualify_existing(local, docs, config):
    ledger = Ledger(local / 'ledger.jsonl', config)
    remaining = config['cpu_prepare_score_report_seconds_limit'] - ledger.totals()['cpu']['elapsed_seconds']
    if remaining <= 5 or (local / 'qualification').exists():
        raise ValueError('qualification already exists or CPU allowance is exhausted')
    start = time.monotonic()
    try:
        return _qualify_existing(local, docs, config, start + min(600., remaining))
    finally:
        output = local / 'qualification/result.json'
        if not output.exists():
            write_json(output, dict(status='failed', error=str(sys.exc_info()[1]),
                                    wall_seconds=time.monotonic() - start))
        ledger.charge_cpu_preparation(time.monotonic() - start, file_record(output))


def supplement_existing_inventory(local, docs, config):
    """Add full file inventories without changing or rebuilding qualified E0/E8."""
    parent = qualification_record(local)
    if not parent:
        raise ValueError('original successful qualification is required')
    ledger = Ledger(local / 'ledger.jsonl', config)
    remaining = config['cpu_prepare_score_report_seconds_limit'] - ledger.totals()['cpu']['elapsed_seconds']
    if remaining <= 5:
        raise ValueError('CPU allowance is exhausted')
    output = local / 'qualification-full-inventory'
    output.mkdir(parents=True, exist_ok=False)
    start = time.monotonic()
    deadline = start + min(600., remaining)
    result = dict(status='failed', parent=parent, runtime={})
    try:
        for name, runtime in read_json(parent['path'])['runtime'].items():
            path = output / (name + '-inventory.json')
            subprocess.run([runtime['python'], str(ROOT / 'scripts/vipe_benchmark/runtime_inventory.py'),
                            '--output', str(path)], check=True, timeout=max(.01, deadline - time.monotonic() - 2.))
            inventory = read_json(path)
            if any(inventory['versions'].get(k) != v for k, v in TARGETS[name].items()):
                raise ValueError('existing runtime version changed during full inventory')
            result['runtime'][name] = dict(runtime, inventory=file_record(path),
                                           original_inventory=runtime['inventory'])
        result['status'] = 'complete'
    except BaseException as exc:
        result['error'] = f'{type(exc).__name__}: {exc}'
        raise
    finally:
        result['wall_seconds'] = time.monotonic() - start
        result['inventory_script'] = file_record(ROOT / 'scripts/vipe_benchmark/runtime_inventory.py')
        write_json(output / 'result.json', result)
        receipt = file_record(output / 'result.json')
        ledger.charge_cpu_preparation(time.monotonic() - start, receipt)
        write_json(docs / 'existing-runtime-full-inventory.json', dict(status=result['status'], result=receipt))
    return result


def components(local):
    records = {}
    qualification = qualified_existing(local)
    if qualification:
        assets = read_json(verify_record(qualification['assets'])['path'])['assets']
        for name in ('S0', 'D0'):
            records[name] = dict(status='admitted', runtime=qualification['runtime']['E0'], assets=assets,
                                 commercial_permission='unverified', non_agpl='unverified')
    for i in range(1, 8):
        record = setup_result_record(local, f'E{i}')
        if record:
            result = read_json(record['path'])
            assets = read_json(verify_record(result['assets'])['path'])
            for name in result['components']:
                records[name] = dict(status='admitted', runtime=result['runtime'], assets=assets,
                    setup=record, commercial_permission=result.get('commercial_permission', 'unverified'),
                    non_agpl=result.get('non_agpl', 'unverified'))
    for name, record in records.items():
        required = ([name + '-calibration', name + '-reconstruction'] if name.startswith('S') else [name + '-fit'])
        if all(result_record(local, j) for j in required):
            record['status'] = 'qualified'
            record['qualification_results'] = [result_record(local, j) for j in required]
    for name in ['M0', 'M1', 'M2', 'N0', 'N1', 'N2']:
        result = result_record(local, name)
        if result:
            records[name] = dict(status='qualified', result=result,
                                 runtime=qualification['runtime']['E8'], assets={})
    from .licenses import assess
    for name, record in records.items():
        record.update(assess(local, name, record))
    return records


def setup_result_record(local, environment):
    """Resolve an authorized successful recovery without relabeling its failure."""
    original = result_record(local, environment + '-setup')
    if original or environment not in ('E1', 'E2', 'E3', 'E4'):
        return original
    ledger = Ledger(local / 'ledger.jsonl', load())
    recoveries = [event for event in ledger.events() if event['event'] == 'setup_recovery_authorized'
                  and event['environment'] == environment]
    if not recoveries:
        return None
    event = recoveries[-1]
    verify_record(event['authorization'])
    recovered = result_record(local, event['job_id'])
    if recovered:
        result = read_json(recovered['path'])
        components = sorted(c for c, env in ENVIRONMENTS.items() if env == environment)
        if (result.get('environment') != environment or result.get('components') != components or
                result.get('runtime', {}).get('versions') != TARGETS[environment]):
            raise ValueError(f'successful recovery differs from the prescribed {environment} qualification')
        for field in ('inventory', 'imports', 'dependency_lock', 'build_inputs'):
            verify_record(result['runtime'][field])
        imports = read_json(result['runtime']['imports']['path'])
        if imports.get('status') != 'complete' or imports.get('forwards') != 0:
            raise ValueError('setup recovery lacks completed import-only qualification')
    return recovered


def common_admission(local, docs, config, validation, *, recovery_authorization=None):
    from .auto_annotations import validate as validate_proxy
    from .annotations import validate as validate_human
    reasons, evidence = [], {}
    if recovery_authorization is not None:
        from .s1_recovery import validate_binding
        document, _ = validate_binding(local, config, recovery_authorization)
        if file_record(validation) != document['repair_validation']:
            raise ValueError('admission validation differs from S1 recovery authorization')
        evidence['s1_recovery_authorization'] = recovery_authorization
        for key in ('semantic_amendment', 'configuration', 'original_failure', 'e1_qualification',
                    'e1_assets', 'e1_runtime', 'inputs', 'annotations', 'annotation_policy', 'annotation_review',
                    'baseline_correction'):
            evidence[key] = document[key]
        evidence['original_failure_event'] = document['original_failure_event_sha256']
        evidence['ledger_before'] = file_record(local / 'ledger.jsonl')
    for name, record in [('inputs', result_artifact(local, 'prepare', 'inputs')),
                         ('annotations', result_artifact(local, 'annotations', 'annotations')),
                         ('runtime', qualification_record(local))]:
        if not record:
            reasons.append(f'{name}: completed evidence missing')
        else:
            evidence[name] = record
    if 'inputs' in evidence and 'annotations' in evidence:
        annotation = read_json(evidence['annotations']['path'])
        validator = validate_proxy if annotation.get('evidence_kind') == 'model-assisted-proxy' else validate_human
        validator(annotation, read_json(evidence['inputs']['path']), config)
    if not validation:
        reasons.append('saved implementation validation missing')
    else:
        checks = read_json(verify_record(file_record(validation))['path'])
        if checks.get('status') != 'passed':
            reasons.append('implementation validation did not pass')
        if not checks.get('sources'):
            reasons.append('implementation validation has no bound source files')
        for source in checks.get('sources', []):
            verify_record(source)
        evidence['implementation_validation'] = file_record(validation)
    host = gpu_reading()
    if host['gpu_pids']:
        reasons.append('exclusive GPU access unavailable; active compute PIDs: ' + ', '.join(map(str, host['gpu_pids'])))
    if host['device_bytes'] > config['gpu_peak_device_gib_limit'] * 2**30:
        reasons.append('GPU already exceeds total memory ceiling')
    storage = resources(local)
    if storage['artifact_bytes'] > config['new_artifact_disk_gib_limit'] * 2**30:
        reasons.append('artifact allowance exceeded')
    if storage['download_bytes'] > config['new_download_gib_limit'] * 2**30:
        reasons.append('download allowance exceeded')
    result = dict(status='blocked' if reasons else 'admitted', reasons=reasons, evidence=evidence,
                  gpu=host, resources=storage, candidates={k: v['status'] for k, v in components(local).items()},
                  consumption=Ledger(local / 'ledger.jsonl', config).totals())
    ledger = Ledger(local / 'ledger.jsonl', config)
    with ledger.locked() as (stream, events):
        if recovery_authorization is not None:
            # Recheck under the append lock; only one successful admission wins.
            document, _ = validate_binding(local, config, recovery_authorization, events=events)
            prior = [e for e in events if e['event'] == 'admission'
                     and read_json(e['evidence']['path']).get('evidence', {}).get(
                         's1_recovery_authorization') == recovery_authorization
                     and read_json(e['evidence']['path']).get('status') == 'admitted']
            if prior:
                raise ValueError('S1 successful admission already exists')
        sequence = len(list(docs.glob('admission-*.json'))) + 1
        path = docs / f'admission-{sequence:03d}.json'
        write_json(path, result)
        ledger._append(stream, events, dict(event='admission', evidence=file_record(path)))
    return result


def make_request(local, job_id, config):
    available = components(local)
    request = dict(job_id=job_id, inputs=result_artifact(local, 'prepare', 'inputs'))
    if not request['inputs']:
        return None, ['completed frozen input preparation unavailable']
    reasons = []
    if job_id.startswith(('S', 'D')) or job_id in ('R-S', 'R-D'):
        name = job_id.split('-')[0] if not job_id.startswith('R-') else {'R-S': 'S1', 'R-D': 'D1'}[job_id]
        qualification = available.get(name)
        if not qualification:
            return None, [f'{name}: pinned assets and target environment unavailable']
        request.update(component=name, runtime=qualification['runtime'], assets=qualification['assets'],
                       forbidden_vipe_roots=[read_json(local / 'qualification/historical-assets.json')['assets']['vipe_source']['path']])
        if name.startswith('S'):
            request['branch'] = 'calibration' if job_id.endswith('-calibration') else 'reconstruction'
        else:
            request['role'] = 'check' if job_id.endswith('-check') else 'fit'
            if request['role'] == 'check':
                fit = result_artifact(local, name + '-fit', 'scale')
                if not fit or read_json(fit['path']).get('status') != 'passed':
                    reasons.append(f'{name}: current scale fitting gates did not pass')
                else:
                    request['frozen_fit'] = fit
        if job_id.startswith('R-'):
            parent = {'R-S': 'S1-reconstruction', 'R-D': 'D1-fit'}[job_id]
            baseline = result_record(local, parent)
            if not baseline:
                reasons.append(f'fixed repeat source {parent} unavailable')
            else:
                request['baseline'] = baseline
    elif job_id.startswith(('M', 'N')):
        request['component'] = job_id
        request['runtime'] = qualified_existing(local)['runtime']['E8']
    elif job_id.startswith(('G-', 'C')) or job_id == 'R-G':
        if job_id.startswith('G-S'):
            s, d, m, n = job_id[2:], 'D0', 'M0', 'N0'
        elif job_id.startswith('G-M'):
            s, d, m, n = 'S0', 'D0', job_id[2:], 'N0'
        elif job_id.startswith('G-N'):
            s, d, m, n = 'S0', 'D0', 'M0', job_id[2:]
        elif job_id == 'R-G':
            s, d, m, n = 'S0', 'D0', 'M0', 'N0'
            source = result_record(local, 'G-S0')
            if source:
                request['repeat_source'] = source
            else:
                reasons.append('fixed G-S0 repeat source unavailable')
        else:
            finalists = aggregate_record(local, 'finalists', artifact=True)
            if not finalists:
                return None, ['frozen finalists unavailable']
            slots = read_json(finalists['path'])['combined']
            slot = slots[job_id]
            if slot['status'] != 'eligible':
                return None, slot['reasons']
            s, d, m, n = slot['components']
            request.update(finalists=finalists, scale_fit=result_artifact(local, d + '-fit', 'scale'),
                           scale_check=result_artifact(local, d + '-check', 'scale'))
            if not request['scale_fit'] or not request['scale_check']:
                reasons.append(f'{d}: successful frozen fit/check result unavailable')
        request['components'] = [s, d, m, n]
        for field, parent in [('segmentation', s + '-reconstruction'), ('motion', m), ('neighbors', n)]:
            record = result_record(local, parent)
            if record:
                request[field] = record
            else:
                reasons.append(f'{parent}: required completed result unavailable')
        qualification = qualified_existing(local)
        request['roma'] = {key: qualification['roma'][key] for key in ('checkout', 'weights')}
        request['roma_provenance'] = qualification['roma']
        request['runtime'] = qualification['runtime']['E8']
    else:
        raise ValueError('unknown matrix slot')
    return request, reasons


def require_stage_order(local, job_id, config):
    order = execution_order()
    if job_id not in order:
        raise ValueError('not a preregistered matrix stage')
    states = Ledger(local / 'ledger.jsonl', config).states()
    missing = [job for job in order[:order.index(job_id)]
               if job not in states or states[job]['event'] == 'reserve']
    if missing:
        raise ValueError('earlier allocated stages are unfinished: ' + ', '.join(missing))
    for boundary, stage in [('D0-fit', 'masks'), ('C0', 'finalists')]:
        if order.index(job_id) >= order.index(boundary) and not aggregate_record(local, stage):
            raise ValueError('required frozen aggregation checkpoint unavailable: ' + stage)


def component_recovery_request(local, config, job):
    events = Ledger(local / 'ledger.jsonl', config).events()
    registered = [e for e in events if e['event'] == 'component_recovery_authorized' and e['job_id'] == job]
    if len(registered) != 1:
        raise ValueError('component recovery lacks registered authorization')
    event = registered[0]
    if event['original_job_id'].startswith('S1-'):
        from .s1_recovery import validate_binding
        document, request = validate_binding(local, config, event['authorization'])
        if (job != document['job_id'] or event['original_job_id'] != document['original_job_id']
                or event['original_failure_event_sha256'] != document['original_failure_event_sha256']):
            raise ValueError('registered S1 recovery binding differs from authorization')
        from .s1_recovery import BINDINGS, admitted_event
        if any(event.get(k) != document[k] for k in BINDINGS):
            raise ValueError('registered S1 evidence changed')
        if admitted_event(events, event['authorization'], document) != event['admission']:
            raise ValueError('registered S1 admission changed')
        return dict(request, job_id=job, recovery_authorization=event['authorization'])
    request, reasons = make_request(local, event['original_job_id'], config)
    if reasons:
        raise ValueError('; '.join(reasons))
    return dict(request, job_id=job)


def reconstruction_request(local, config, job):
    from .sam3_memory import DIAGNOSTIC, CLEANUP, validate_diagnostic_review
    request, reasons = make_request(local, 'S3-reconstruction', config)
    if reasons:
        raise ValueError('; '.join(reasons))
    events = Ledger(local / 'ledger.jsonl', config).events()
    kind = 'memory_diagnostic_authorized' if job == DIAGNOSTIC else 'reconstruction_recovery_authorized'
    registered = [e for e in events if e['event'] == kind and e['job_id'] == job]
    if len(registered) != 1:
        raise ValueError('reconstruction/diagnostic identity lacks exact registered authorization')
    document = read_json(verify_record(registered[0]['authorization'])['path'])
    request = dict(request, job_id=job)
    if job == DIAGNOSTIC:
        request.update(memory_cleanup=CLEANUP, partial_output=str(local / 'jobs/S3-reconstruction-recovery-002'))
    elif document.get('memory_diagnostic_review'):
        validate_diagnostic_review(document['memory_diagnostic_review'])
        request.update(memory_cleanup=CLEANUP, memory_diagnostic_review=document['memory_diagnostic_review'])
    return request


def s1_sampling_operation(local):
    return dict(operation='resources', args=dict(local=str(local)))


def dispatch(local, docs, config, request, *, operation='component', checkpoint=False, resume_checkpoint=False):
    job = request['job_id']
    ledger = Ledger(local / 'ledger.jsonl', config)
    allocated = ledger.jobs
    if job not in allocated:
        raise ValueError('unallocated worker')
    if '-setup-recovery-' in job and operation != 'setup':
        raise ValueError('authorized setup recovery cannot fund another operation')
    if any(e['event'] == 'component_recovery_authorized' and e['job_id'] == job for e in ledger.events()):
        if operation != 'component' or request != component_recovery_request(local, config, job):
            raise ValueError('component recovery must preserve the exact original recipe')
    if job.startswith('S3-reconstruction-recovery-') or job == 'S3-memory-diagnostic-001':
        expected = reconstruction_request(local, config, job)
        if operation != 'component' or request != expected:
            raise ValueError('reconstruction recovery must use the exact original component recipe')
    device_monitored = allocated[job]['resource'] in ('gpu', 'setup')
    if device_monitored and Path('/proc/1/comm').read_text().strip() != 'systemd':
        raise PermissionError('GPU execution requires host PID visibility for nvidia-smi ownership; '
                              'run this allocated dispatch outside the sandbox before reserving an attempt')
    suffix = job if job != 'aggregate' else 'aggregate-' + request['stage']
    request = dict(request, configuration=file_record(ROOT / 'configs/vipe-alternatives/benchmark-v1.json'))
    request_path = local / 'requests' / (suffix + '.json')
    if request_path.exists():
        if read_json(request_path) != request:
            raise ValueError('saved unstarted request differs from the explicit dispatch')
    else:
        write_json(request_path, request)
    python = request.get('runtime', {}).get('python', str(ROOT / '.local/envs/stg-colmap/bin/python'))
    command = [python, str(ROOT / 'scripts/basketball_vipe_worker.py'), '--operation', operation,
               '--config', str(ROOT / 'configs/vipe-alternatives/benchmark-v1.json'),
               '--request', str(request_path), '--output', str(local / 'jobs' / suffix)]
    def validate(output):
        result = read_json(output / 'result.json')
        if result.get('status') != 'complete':
            raise ValueError('worker did not complete its explicit result contract')
        if job == 'S1-calibration-recovery-001':
            from .s1_recovery import accept_result
            return accept_result(local, config, request, result, output)
        if operation == 'component' and request['component'].startswith(('S', 'D')):
            expected = (96 if job == 'S3-memory-diagnostic-001' else 2 if job == 'R-S' else 1 if job == 'R-D' else
                        510 if request.get('branch') == 'calibration' else 840 if request.get('branch') == 'reconstruction' else 30)
            if len(result['rows']) != expected:
                raise ValueError('component output count differs from allocated identity set')
            for row in result['rows']:
                for field in ('instances', 'semantic_static', 'static', 'depth'):
                    if field in row:
                        verify_record(row[field])
    evidence = dict(request=file_record(request_path), worker=file_record(ROOT / 'scripts/basketball_vipe_worker.py'))
    if job == 'S1-calibration-recovery-001':
        from .s1_recovery import event_ref
        event = next(e for e in ledger.events() if e['event'] == 'component_recovery_authorized' and e['job_id'] == job)
        evidence.update({k: event[k] for k in ('authorization', 'admission', 'semantic_amendment', 'repair_validation', 'configuration', 'baseline_correction')})
        evidence['authorization_event'] = event_ref(event)
    def publish(reservation, outcome):
        from .s1_recovery import terminal_receipt
        return terminal_receipt(local, docs, config, request['recovery_authorization'],
                                reservation=reservation, outcome=outcome)
    result = supervise(ledger, job, command, local / 'jobs' / suffix,
        evidence=evidence,
        sample_resources=s1_sampling_operation(local) if job == 'S1-calibration-recovery-001' else lambda: resources(local, gpu=device_monitored),
        validate_result=validate, poll_seconds=.1 if job == 'S1-calibration-recovery-001' else 2., checkpoint=checkpoint, resume_checkpoint=resume_checkpoint,
        terminal_publisher=publish if job == 'S1-calibration-recovery-001' else None, terminal_docs=docs)
    if job != 'S1-calibration-recovery-001':
        write_json(docs / (suffix + '.json'), dict(status='complete', result=file_record(local / 'jobs' / suffix / 'result.json')))
    return result


def aggregate_request(local, stage, config):
    request = dict(job_id='aggregate', stage=stage, inputs=result_artifact(local, 'prepare', 'inputs'))
    if stage == 'masks':
        request.update(annotations=result_artifact(local, 'annotations', 'annotations'),
            segmentation={f'S{i}': {branch: record for branch in ('calibration', 'reconstruction')
                                   if (record := result_record(local, f'S{i}-{branch}'))} for i in range(5)},
            motion={f'M{i}': record for i in range(3) if (record := result_record(local, f'M{i}'))})
    elif stage == 'finalists':
        request.update(mask_metrics=aggregate_record(local, 'masks', artifact=True),
            geometry={job: record for job in ['G-S0', 'G-S1', 'G-S2', 'G-S3', 'G-S4', 'G-M1', 'G-M2', 'G-N1', 'G-N2']
                      if (record := result_record(local, job))},
            scales={f'D{i}': {role: record for role in ('fit', 'check')
                              if (record := result_artifact(local, f'D{i}-{role}', 'scale'))} for i in range(5)},
            components=components(local),
            depth_controls={role: {label: record for label, component in [('baseline', 'D0'), ('candidate', 'D1')]
                                   if (record := result_record(local, f'{component}-{role}'))}
                            for role in ('fit', 'check')})
    elif stage == 'final':
        request.update(finalists=aggregate_record(local, 'finalists', artifact=True),
            combined={f'C{i}': record for i in range(4) if (record := result_record(local, f'C{i}'))},
            repeats={j: record for j in ('R-S', 'R-D', 'R-G') if (record := result_record(local, j))})
    else:
        raise ValueError('unknown aggregate stage')
    amendment = read_json(local / 'annotations/annotations.json').get('policy')
    if amendment:
        request['amendment'] = amendment
    return request


def execute_matrix(local, docs, config, validation):
    completed_report = result_record(local, 'report')
    if completed_report:
        result = read_json(completed_report['path'])
        verify_record(result['report'])
        return result
    report_state = Ledger(local / 'ledger.jsonl', config).states().get('report')
    if report_state:
        raise ValueError('report attempt already consumed or accounted; cannot launch another pass')
    admission = common_admission(local, docs, config, validation)
    if admission['status'] != 'admitted':
        raise ValueError('; '.join(admission['reasons']))
    ledger = Ledger(local / 'ledger.jsonl', config)
    for job in execution_order():
        if job == 'D0-fit' and not aggregate_record(local, 'masks'):
            dispatch(local, docs, config, aggregate_request(local, 'masks', config),
                     operation='aggregate', checkpoint=True)
        if job == 'C0' and not aggregate_record(local, 'finalists'):
            dispatch(local, docs, config, aggregate_request(local, 'finalists', config),
                     operation='aggregate', checkpoint=True, resume_checkpoint=True)
        state = ledger.states().get(job)
        if state:
            if state['event'] == 'reserve':
                raise ValueError('unreconciled existing attempt; cannot redispatch')
            continue
        request, reasons = make_request(local, job, config)
        if reasons:
            ledger.account(job, 'skipped' if job.startswith('R-') else 'blocked', '; '.join(reasons))
            continue
        operation = 'geometry' if job.startswith(('G-', 'C')) or job == 'R-G' else 'component'
        try:
            dispatch(local, docs, config, request, operation=operation)
        except SupervisionFailure as error:
            failure = local / 'jobs' / job / 'failure.json'
            if error.stop_required or (failure.exists() and read_json(failure).get('requires_permission_review')):
                raise
            # A native contract/runtime failure consumes its attempt and blocks
            # only dependent arms. Suspected access failures always stop.
            write_json(docs / (job + '-failure.json'), dict(status='failed',
                failure=file_record(failure) if failure.exists() else None,
                supervisor=ledger.states()[job]))
    if not aggregate_record(local, 'final'):
        dispatch(local, docs, config, aggregate_request(local, 'final', config),
                 operation='aggregate', resume_checkpoint=True)
    write_json(local / 'final-components.json', components(local))
    recovery_allocations = [event for event in ledger.events() if event['event'] == 'setup_recovery_authorized']
    reconstruction_recoveries = [event for event in ledger.events() if event['event'] == 'reconstruction_recovery_authorized']
    component_recoveries = [e for e in ledger.events() if e['event'] == 'component_recovery_authorized']
    write_json(local / 'final-accounting-before-report.json', dict(jobs=ledger.states(), consumption=ledger.totals(),
        setup_recovery_authorizations=recovery_allocations, reconstruction_recovery_authorizations=reconstruction_recoveries,
        component_recovery_authorizations=component_recoveries))
    request = dict(job_id='report', inputs=result_artifact(local, 'prepare', 'inputs'),
        annotations=result_artifact(local, 'annotations', 'annotations'),
        aggregate=aggregate_record(local, 'final', artifact=True),
        components=file_record(local / 'final-components.json'),
        accounting=file_record(local / 'final-accounting-before-report.json'), validation=file_record(validation))
    result = dispatch(local, docs, config, request, operation='report')
    write_json(docs / 'matrix-accounting-final.json', dict(jobs=ledger.states(), consumption=ledger.totals(),
        setup_recovery_authorizations=recovery_allocations, reconstruction_recovery_authorizations=reconstruction_recoveries,
        component_recovery_authorizations=component_recoveries))
    shutil.copyfile(result['report']['path'], docs / 'report.md')
    return result


def execute_s1_recovery(local, docs, config, authorization):
    """One controller lifecycle; no matrix/report follow-up and no replay."""
    from .s1_recovery import JOB, validate_binding, terminal_receipt
    ledger = Ledger(local / 'ledger.jsonl', config)
    # Replay is rejected before publishing another admission/receipt.
    error = None
    primary = None
    supplied = authorization
    try:
        if not isinstance(authorization, dict):
            authorization = file_record(authorization)
        document, _ = validate_binding(local, config, authorization)
        registered = [e for e in ledger.events() if e['event'] == 'component_recovery_authorized' and e['job_id'] == JOB]
        if not registered:
            admission = common_admission(local, docs, config,
                Path(document['repair_validation']['path']), recovery_authorization=authorization)
            if admission['status'] != 'admitted':
                raise ValueError('; '.join(admission['reasons']))
            ledger.authorize_component_recovery(authorization)
        elif len(registered) != 1 or registered[0]['authorization'] != authorization:
            raise ValueError('different S1 authorization already registered')
        return dispatch(local, docs, config, component_recovery_request(local, config, JOB))
    except BaseException as exc:
        primary = exc
        error = f'{type(exc).__name__}: {exc}'
        raise
    finally:
        try:
            # Consumed outcomes belong exclusively to the charged supervisor.
            if not any(e.get('job_id') == JOB and e['event'] == 'reserve' for e in ledger.events()):
                terminal_receipt(local, docs, config, authorization if isinstance(authorization, dict) else supplied, error=error)
        except BaseException as publication_error:
            if primary is None:
                raise
            primary.add_note(f'S1 terminal publication failed: {publication_error}')

"""Bounded, metered isolated environments within the approved depth setup slot."""
import math
import os
from pathlib import Path
import subprocess
import time
from urllib.parse import urlsplit

from packaging.requirements import Requirement
from packaging.utils import canonicalize_name

from .budgets import budget_snapshot
from .config import ROOT
from .files import file_record, read_json, safe_path, verify_record, write_json


SCHEMA = 'plan069-depth-environment-request/v1'


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def _requirements(values):
    _require(isinstance(values, list) and bool(values), 'explicit depth requirements required')
    parsed = []
    for value in values:
        _require(isinstance(value, str) and '\n' not in value and '\r' not in value and
                 not value.startswith('-'), 'invalid depth package requirement')
        requirement = Requirement(value)
        _require(requirement.url is None, 'depth dependency URLs must be pinned local archives')
        parsed.append(requirement)
    return parsed


def _validate_inventory(inventory, request, python):
    _require(inventory.get('executable') == python and inventory.get('inventory_only') is True and
             inventory.get('model_imports') is False and inventory.get('gpu_operations') is False and
             inventory.get('versions', {}).get('python') == request['python_version'],
             'depth environment inventory interpreter or CPU-only scope differs')
    packages = {canonicalize_name(row['name']): row for row in inventory.get('packages', [])}
    for requirement in _requirements(request['requirements'] + request['constraints']):
        if requirement.marker and not requirement.marker.evaluate(
                {'python_version': request['python_version'],
                 'python_full_version': request['python_version'] + '.0'}):
            continue
        row = packages.get(canonicalize_name(requirement.name))
        _require(row is not None and requirement.specifier.contains(row['version']),
                 'depth installed dependency differs: ' + requirement.name)
    for source in request.get('sources', []):
        _require(canonicalize_name(source['name']) in packages,
                 'depth local source package absent from installed inventory')


def _setup_deadline(request, output, run_root, config, deadline):
    from .ledger import Ledger
    from .setup_recovery_core import candidate_for_job
    ledger_path = safe_path(request['ledger_path']).absolute()
    saved = verify_record(request['setup_request'])
    parent = read_json(saved['path'])
    job = f"plan069-{request['candidate']}-setup-001"
    if candidate_for_job(parent.get('job_id')) == request['candidate']:
        job = parent['job_id']  # The candidate's own reserved setup recovery.

    state = Ledger(ledger_path, config).states().get(job, {})
    command = state.get('command', [])
    _require(ledger_path == run_root / 'ledger.jsonl' and
             output == run_root / 'jobs' / job / 'runtime' and
             state.get('event') == 'reserve' and state.get('resource') == 'setup' and
             state.get('evidence', {}).get('request') == saved and
             parent.get('candidate') == request['candidate'] and parent.get('job_id') == job and
             parent.get('record_kind') == 'actual' and
             '--request' in command and '--output' in command and
             command[command.index('--request') + 1] == saved['path'] and
             command[command.index('--output') + 1] == str(output.parent) and
             os.environ.get('VIPE_RESERVATION_START') == str(state.get('monotonic_start')),
             'active exact depth setup reservation required for environment provisioning')
    return min(deadline, state['monotonic_start'] + state['seconds'] - 30)


def provision_depth_environment(request, output, config, *, run_root, deadline,
                                download_limit=None, artifact_limit=None, runner=None):
    """Provision once; fixture runners simulate commands without network or GPU use.

    Callers bind requirements to reviewed source and pass the original setup's
    absolute byte ceilings and remaining deadline. Local package archives are
    installed offline after the hash-locked dependency closure.
    """
    _require(request.get('schema') == SCHEMA and request.get('candidate') in
             ('D5', 'D6', 'D7', 'D8', 'D9', 'D10', 'D11') and
             request.get('record_kind') in ('actual', 'fixture') and
             request.get('python_version') in ('3.10', '3.11'),
             'exact depth environment recipe and compatible Python required')
    _require((request['record_kind'] == 'fixture') == (runner is not None),
             'actual depth provisioning cannot inject a fixture command runner')
    output, run_root = safe_path(output).absolute(), safe_path(run_root).absolute()
    _require(output.is_relative_to(run_root) and not output.exists(),
             'immutable depth environment output must belong to the shared run')
    _require(type(deadline) in (float, int) and math.isfinite(deadline) and
             time.monotonic() < deadline, 'depth setup environment deadline exhausted')
    download_limit = config.get('download_limit') if download_limit is None else download_limit
    artifact_limit = config.get('artifact_limit') if artifact_limit is None else artifact_limit
    _require(type(download_limit) is int and 0 < download_limit <=
             config['new_download_gib_limit'] * 2**30 and
             type(artifact_limit) is int and 0 < artifact_limit <=
             config['new_artifact_disk_gib_limit'] * 2**30,
             'explicit candidate and shared depth provisioning byte ceilings required')
    if request['record_kind'] == 'actual':
        deadline = _setup_deadline(request, output, run_root, config, deadline)
        _require(time.monotonic() < deadline, 'depth setup reservation cleanup deadline exhausted')
    requirements = _requirements(request['requirements'])
    constraints = _requirements(request['constraints'])
    _require(all(requirement.specifier and str(requirement.specifier).startswith('==') and
                 '*' not in str(requirement.specifier) and requirement.url is None
                 for requirement in constraints), 'exact depth base constraints required')
    seed = safe_path(request['python_seed_executable']).absolute()
    _require(str(seed) == request['python_seed_executable'] and
             file_record(seed) == verify_record(request['python_seed']),
             'exact absolute depth Python seed invocation required')
    uv = verify_record(request['uv'])['path']
    sources = request.get('sources', [])
    _require(isinstance(sources, list), 'explicit local source package list required')
    for source in sources:
        _require(source.get('install_local_offline') is True and
                 isinstance(source.get('name'), str) and source['name'] and
                 isinstance(source.get('revision'), str) and source['revision'],
                 'pinned offline local source package required')
        verify_record(source['record'])
        _require(not any(canonicalize_name(row.name) == canonicalize_name(source['name'])
                         for row in requirements),
                 'local source packages must not be resolved from an unpinned package index')
    _require(isinstance(request.get('requirement_sources'), list) and
             bool(request['requirement_sources']), 'reviewed source requirement records required')
    for record in request['requirement_sources']:
        verify_record(record)
    indexes = request.get('indexes')
    _require(isinstance(indexes, list) and bool(indexes), 'explicit depth package indexes required')
    for index in indexes:
        parsed = urlsplit(index)
        _require(parsed.scheme == 'https' and parsed.hostname and not parsed.username and
                 not parsed.password and not parsed.query and not parsed.fragment,
                 'depth indexes require credential-free explicit HTTPS origins')
    index_arguments = ['--index-url', indexes[0]]
    for index in indexes[1:]:
        index_arguments.extend(['--extra-index-url', index])
    index_arguments.extend(['--index-strategy', 'unsafe-best-match'])
    environment = dict(os.environ, UV_CACHE_DIR=str(run_root / 'setup-cache'),
        UV_PYTHON_INSTALL_DIR=str(run_root / 'managed-python'), UV_LINK_MODE='hardlink',
        UV_HTTP_RETRIES='0', UV_PYTHON_DOWNLOADS='never', PIP_RETRIES='0', PIP_NO_INPUT='1',
        UV_CONCURRENT_DOWNLOADS='1', UV_CONCURRENT_BUILDS='1', UV_CONCURRENT_INSTALLS='7',
        OMP_NUM_THREADS='7', MAX_JOBS='7', PYTHONDONTWRITEBYTECODE='1',
        PYTHONNOUSERSITE='1', CUDA_VISIBLE_DEVICES='')
    flex_cache = None
    if request['candidate'] in ('D5', 'D6'):
        from .moge_source_build import cache_path, verify_derivation
        flex_sources = [s for s in sources if s['name'] == 'flex-gemm']
        _require(len(flex_sources) == 1, 'one reviewed FlexGEMM derivation required')
        verify_derivation(flex_sources[0])
        flex_cache = str(cache_path(output))
        _require(request.get('flex_cache_path') == flex_cache,
                 'reviewed MoGe cache differs from reserved runtime')
        environment.update(FLEX_GEMM_AUTOTUNE_CACHE_PATH=flex_cache,
                           FLEX_GEMM_BUILD_CUDA='0', BUILD_CUDA='0')
    for name in ('PYTHONPATH', 'PYTHONHOME'):
        environment.pop(name, None)
    output.mkdir(parents=True, exist_ok=False)
    write_json(output / 'request.json', request)
    (output / 'requirements.txt').write_text('\n'.join(request['requirements'] + request['constraints']) + '\n')
    (output / 'constraints.txt').write_text('\n'.join(request['constraints']) + '\n')
    env_path = output / 'environment'
    receipts: list[dict] = []
    python = str(env_path / 'bin/python')
    lock = output / 'requirements.lock'
    started = time.monotonic()

    def check_limits():
        snapshot = budget_snapshot(run_root)
        _require(time.monotonic() < deadline, 'depth provisioning setup deadline exceeded')
        _require(snapshot['download_bytes'] <= download_limit and
                 snapshot['artifact_bytes'] <= artifact_limit,
                 'depth provisioning candidate or shared byte ceiling exceeded')
        return snapshot

    def run(command, label, *, offline=False):
        check_limits()
        log = output / 'commands' / f'{len(receipts):02d}-{label}.log'
        log.parent.mkdir(exist_ok=True)
        env = dict(environment)
        if offline:
            env.update(UV_OFFLINE='1', HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1', PIP_NO_INDEX='1')
        begin, error = time.monotonic(), None
        uv_transfer_receipt = None
        try:
            if runner is not None:
                runner(command, environment=env, cwd=ROOT,
                       timeout=deadline - time.monotonic(), log=log)
            else:
                with log.open('x') as stream:
                    if command[0] == uv:
                        from .transfer_proxy import inherited_https_proxy, uv_proxy
                        with uv_proxy(run_root, download_limit, artifact_limit=artifact_limit,
                                      upstream_proxy=inherited_https_proxy(env)) as proxy:
                            env.update(proxy.environment)
                            try:
                                subprocess.run(command, check=True, env=env, cwd=ROOT,
                                    stdout=stream, stderr=subprocess.STDOUT,
                                    timeout=max(.001, deadline - time.monotonic()))
                            finally:
                                proxy.check()
                        if request['record_kind'] == 'actual':
                            uv_transfer_receipt = file_record(proxy.receipt_path)
                    else:
                        subprocess.run(command, check=True, env=env, cwd=ROOT,
                            stdout=stream, stderr=subprocess.STDOUT,
                            timeout=max(.001, deadline - time.monotonic()))
            check_limits()
        except BaseException as exception:
            error = f'{type(exception).__name__}: {exception}'
            raise
        finally:
            if not log.exists():
                log.write_text('Command failed before log creation.\n')
            path = output / 'commands' / f'{len(receipts):02d}-{label}.json'
            write_json(path, dict(command=command, cwd=str(ROOT), log=file_record(log),
                wall_seconds=time.monotonic() - begin, error=error, offline=offline,
                automatic_retries=0, package_transfer_proxy=command[0] == uv,
                record_kind=request['record_kind'], uv_transfer_receipt=uv_transfer_receipt))
            receipts.append(file_record(path))
        return log

    try:
        seed_probe = run([str(seed), '-I', '-B', '-c',
            'import json,sys; print(json.dumps({"python_version": "%d.%d" % sys.version_info[:2]}))'],
            'seed-python', offline=True)
        _require(read_json(seed_probe).get('python_version') == request['python_version'],
                 'depth Python seed version differs from reviewed recipe')
        _require(file_record(seed) == request['python_seed'], 'depth Python seed changed')
        run([uv, 'venv', '--python', str(seed), '--no-python-downloads', str(env_path)], 'venv')
        run([uv, 'pip', 'compile', '--python', python, *index_arguments,
            '--generate-hashes', '--no-build-isolation', '-c', str(output / 'constraints.txt'),
            '--output-file', str(lock), str(output / 'requirements.txt')], 'resolve')
        _require(lock.is_file() and lock.stat().st_size > 0,
                 'depth resolver did not produce an immutable hash lock')
        run([uv, 'pip', 'install', '--python', python, *index_arguments, '--require-hashes',
            '--no-build-isolation', '-c', str(output / 'constraints.txt'), '-r', str(lock)], 'locked-dependencies')
        for source in sources:
            record = verify_record(source['record'])
            run([uv, 'pip', 'install', '--python', python, '--offline', '--no-deps',
                '--no-build-isolation', record['path']], 'source-' + str(len(receipts)), offline=True)
        run([uv, 'pip', 'check', '--python', python], 'dependency-check', offline=True)
        inventory_path = output / 'inventory.json'
        run([python, '-I', '-B', str(ROOT / 'scripts/vipe_benchmark/runtime_inventory.py'),
             '--output', str(inventory_path)], 'inventory', offline=True)
        _validate_inventory(read_json(inventory_path), request, python)
        for record in request['requirement_sources']:
            verify_record(record)
        check_limits()
        result = dict(schema='plan069-depth-environment-result/v1', status='complete',
            candidate=request['candidate'], record_kind=request['record_kind'],
            python_executable=python, python=file_record(python), python_seed=request['python_seed'],
            dependency_lock=file_record(lock), inventory=file_record(inventory_path),
            command_receipts=receipts, requirement_sources=request['requirement_sources'],
            sources=sources, source_packages=sources, elapsed_seconds=time.monotonic() - started,
            model_imports=False, gpu_operations=False, automatic_retries=0)
        if flex_cache is not None:
            result['flex_cache_path'] = flex_cache
        write_json(output / 'result.json', result)
        return result
    except BaseException as exception:
        write_json(output / 'failure.json', dict(schema='plan069-depth-environment-failure/v1',
            status='failed', candidate=request['candidate'], record_kind=request['record_kind'],
            error=f'{type(exception).__name__}: {exception}', command_receipts=receipts,
            elapsed_seconds=time.monotonic() - started, automatic_retries=0))
        raise

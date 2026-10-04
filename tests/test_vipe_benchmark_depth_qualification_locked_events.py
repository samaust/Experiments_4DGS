"""Retained D6 proof uses authoritative locked events without nested flock."""
from pathlib import Path
import json
import os
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from vipe_benchmark.config import load
from vipe_benchmark.files import file_record, read_json, write_json
from vipe_benchmark.ledger import Ledger
from test_vipe_benchmark_depth_driver_qualification import fixture, result_fixture


def retained(root):
    record, request, sources = fixture(root)
    ledger = Ledger(root/'ledger.jsonl', load())
    result = result_fixture(record, request, sources)
    write_json(root/'result.json', result)
    with patch('vipe_benchmark.depth_admission.local_source_records', return_value=sources), patch(
            'vipe_benchmark.execution.resources', return_value=dict(gpu_pids=[], device_bytes=0, artifact_bytes=0, download_bytes=0)):
        ledger.authorize_depth_driver_qualification(record)
        ledger.reserve(request['job_id'], request['command'], dict(request=record))
        finish = ledger.finish(request['job_id'], 'complete', 2, cleanup_confirmed=True,
            result=file_record(root/'result.json'), peak=dict(device_bytes=0))
    write_json(root/'finish.json', finish)
    runtime = dict(record_kind='fixture', qualification_kind='gpu_aware_import_cpu_weights',
        setup=request['setup'], local_sources=sources, driver_qualification=dict(request=record,
        result=file_record(root/'result.json'), finish=file_record(root/'finish.json'), ledger_path=str(ledger.path)))
    return ledger, runtime


def locked_admission():
    from test_vipe_benchmark_depth_admission import DepthAdmissionTests
    from vipe_benchmark import depth_admission as admission
    case = DepthAdmissionTests(); case.setUp()
    try:
        proofroot = case.root/'proof'; proofroot.mkdir()
        ledger, proof = retained(proofroot)
        inventory = read_json(case.inventory); inventory['candidates']['D6'] = inventory['candidates']['D5']
        case.inventory.write_text(json.dumps(inventory))
        case.proposal['candidate'] = 'D6'
        qualification = read_json(case.runtime['receipt']['path']); qualification.update(proof)
        Path(case.runtime['receipt']['path']).write_text(json.dumps(qualification))
        case.runtime['receipt'] = file_record(case.runtime['receipt']['path'])
        with ledger.locked() as (_, events):
            blockers = case.decide(setup_events=events, run_root=proofroot)
        assert not any('driver qualification exception invalid' in item for item in blockers), blockers
    finally:
        case.tearDown()


class LockedQualificationTests(unittest.TestCase):
    def test_public_admission_finishes_while_real_ledger_flock_is_held(self):
        command = [sys.executable, '-B', '-c',
            'from test_vipe_benchmark_depth_qualification_locked_events import locked_admission; locked_admission()']
        result = subprocess.run(command, env=dict(os.environ, CUDA_VISIBLE_DEVICES=''),
            capture_output=True, text=True, timeout=5)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_recovery_proof_accepts_locked_events_and_rejects_unreviewed_worker(self):
        from test_vipe_benchmark_depth_driver_qualification_recovery import fixture as recovery_fixture
        from vipe_benchmark.depth_driver_qualification_recovery import validate_request, qualification_exception
        from vipe_benchmark.files import object_hash
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            ledger, record, request, sources, live = recovery_fixture(root)
            result = result_fixture(record, request, sources)
            trace = Path(request['output']).with_suffix('.syscalls.log'); trace.write_text('stable fixture trace')
            result.update(schema='plan069-D6-driver-qualification-result/v2',network_guard=request['network_guard'],
                creation_exception=request['creation_exception'],trace_path=str(trace))
            output = Path(request['output']); write_json(output/'worker-result.json', result)
            result.update(trace=file_record(trace),worker_result=file_record(output/'worker-result.json'))
            write_json(output/'result.json', result)
            with patch('vipe_benchmark.depth_admission.local_source_records', return_value=sources), patch(
                    'vipe_benchmark.execution.resources', return_value=live):
                ledger.authorize_depth_driver_qualification_recovery(record)
                ledger.reserve(request['job_id'], request['command'], dict(request=record))
                finish = ledger.finish(request['job_id'], 'complete', 2, cleanup_confirmed=True,
                    result=file_record(output/'result.json'), peak=dict(device_bytes=0))
            write_json(output/'finish.json', finish)
            proof = dict(request=record,result=file_record(output/'result.json'),finish=file_record(output/'finish.json'),ledger_path=str(ledger.path))
            runtime = dict(record_kind='fixture',qualification_kind='gpu_aware_import_cpu_weights',setup=request['setup'],local_sources=sources,driver_qualification=proof)
            with ledger.locked() as (_, events):
                self.assertEqual(qualification_exception(runtime,events=events,run_root=root),proof)
            review = read_json(request['review']['path']); review['proposal'].pop('worker')
            Path(request['review']['path']).write_text(json.dumps(review)); request['review'] = file_record(request['review']['path'])
            approval = read_json(request['authorization']['path']); approval.update(review=request['review'],proposal_sha256=object_hash(review['proposal']))
            Path(request['authorization']['path']).write_text(json.dumps(approval)); request['authorization'] = file_record(request['authorization']['path'])
            Path(record['path']).write_text(json.dumps(request))
            with self.assertRaisesRegex(ValueError,'reviewed qualification worker'):
                validate_request(file_record(record['path']))

    def test_events_must_be_current_authoritative_chain_for_exact_run_root(self):
        from vipe_benchmark.depth_driver_qualification import qualification_exception
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); ledger, runtime = retained(root)
            with ledger.locked() as (_, events):
                self.assertEqual(qualification_exception(runtime, events=events, run_root=root), runtime['driver_qualification'])
                for changed, run_root in [(events[:-1], root), (events, root/'foreign'), (events, None)]:
                    with self.subTest(root=run_root), self.assertRaises(ValueError):
                        qualification_exception(runtime, events=changed, run_root=run_root)
                forged = [dict(row) for row in events]; forged[-1]['elapsed_seconds'] = 0
                with self.assertRaises(ValueError): qualification_exception(runtime, events=forged, run_root=root)
            self.assertEqual(qualification_exception(runtime), runtime['driver_qualification'])


if __name__ == '__main__': unittest.main()

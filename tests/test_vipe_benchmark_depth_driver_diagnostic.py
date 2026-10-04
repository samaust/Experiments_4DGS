"""Diagnostic public authority and one-use ledger contract; no CUDA execution."""
from pathlib import Path
import json
import tempfile
import unittest
from unittest.mock import patch

from test_vipe_benchmark_depth_driver_qualification import fixture
from vipe_benchmark.depth_driver_diagnostic import JOB, PREDECESSOR, validate_request
from vipe_benchmark.files import file_record, object_hash, read_json, write_json
from vipe_benchmark.config import load
from vipe_benchmark.ledger import Ledger


class DiagnosticTests(unittest.TestCase):
    def prepare(self, root):
        old_record, old, sources = fixture(root)
        ledger = Ledger(root/'ledger.jsonl', load())
        live = dict(gpu_pids=[],device_bytes=0,artifact_bytes=0,download_bytes=0)
        with patch('vipe_benchmark.depth_admission.local_source_records',return_value=sources), patch('vipe_benchmark.execution.resources',return_value=live):
            ledger.authorize_depth_driver_qualification(old_record)
            ledger.reserve(PREDECESSOR,old['command'],dict(request=old_record))
            finish=ledger.finish(PREDECESSOR,'failed',1,cleanup_confirmed=True)
        finish_path=root/'old-finish.json';write_json(finish_path,finish)
        Path(old['output']).mkdir()
        dependencies=Path(old['output'])/'installed-dependencies.json';write_json(dependencies,dict(schema='plan069-depth-installed-dependencies/v1',
            record_kind='fixture',candidate='D6',setup=old['setup'],files=[]))
        proposal=dict(candidate='D6',job_id=JOB,predecessor_job=PREDECESSOR,max_attempts=1,
            seconds=60,cleanup_seconds=30,device_bytes=2*1024**3,artifact_bytes=16*1024**2,
            downloads=0,model_load=False,inference=False,benchmarks=False,preserve_network_guard=True,
            setup=old['setup'],predecessor_finish=file_record(finish_path),worker=old['worker'],guard=old['worker'],
            strace=old['worker'],dependencies=file_record(dependencies))
        review_path=root/'diag-review.json';write_json(review_path,dict(schema='plan069-D6-driver-diagnostic-review/v1',status='REVIEW',proposal=proposal))
        do_path=root/'diag-do.json';write_json(do_path,dict(schema='plan069-D6-driver-diagnostic-authorization/v1',status='DO',review=file_record(review_path),proposal_sha256=object_hash(proposal)))
        record_path=root/'diag-request.json';output=root/'diagnostic'
        request=dict(schema='plan069-D6-driver-diagnostic-request/v1',record_kind='fixture',
            review=file_record(review_path),authorization=file_record(do_path),source_review=old['source_review'],
            cpu_validation=old['cpu_validation'],setup=old['setup'],predecessor_finish=file_record(finish_path),
            worker=old['worker'],guard=old['worker'],strace=old['worker'],executable=old['executable'],
            interpreter_invocation=old['interpreter_invocation'],ledger_path=str(ledger.path),output=str(output))
        request['dependencies']=file_record(dependencies)
        request['command']=[request['strace']['path'],'-f','-qq','-s','128','-e',
            'trace=socket,socketpair,connect,bind,listen,accept,accept4,sendto,sendmsg,recvfrom,recvmsg,ioctl',
            '-e','raw=sendto,sendmsg,recvfrom,recvmsg,ioctl','-o',str(output.with_suffix('.syscalls.log')),
            request['interpreter_invocation'],'-I','-B',request['worker']['path'],'--request',str(record_path)]
        write_json(record_path,request)
        return ledger,file_record(record_path),request,sources,live

    def test_new_do_clean_predecessor_one_use_and_original_slot_preserved(self):
        with tempfile.TemporaryDirectory() as directory:
            ledger,record,request,sources,live=self.prepare(Path(directory))
            with patch('vipe_benchmark.depth_admission.local_source_records',return_value=sources), patch('vipe_benchmark.execution.resources',return_value=live):
                ledger.authorize_depth_driver_diagnostic(record)
                reservation=ledger.reserve(JOB,request['command'],dict(request=record))
                self.assertEqual(reservation['seconds'],60)
                ledger.finish(JOB,'complete',1,cleanup_confirmed=True)
                with self.assertRaisesRegex(ValueError,'consumed'):ledger.authorize_depth_driver_diagnostic(record)
            self.assertEqual(ledger.states()[PREDECESSOR]['status'],'failed')
            self.assertNotIn('plan069-D6-maps-001',ledger.states())

    def test_notes_missing_do_and_changed_command_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            ledger,record,request,sources,live=self.prepare(Path(directory))
            with self.assertRaisesRegex(ValueError,'checked'):ledger.note('depth_driver_diagnostic_authorized')
            request['command']=['unreviewed-tracer'];Path(record['path']).write_text(json.dumps(request))
            with self.assertRaisesRegex(ValueError,'trace command'):validate_request(file_record(record['path']))
            do=read_json(request['authorization']['path']);do['status']='REVIEW'
            Path(request['authorization']['path']).write_text(json.dumps(do))
            request['authorization']=file_record(request['authorization']['path']);Path(record['path']).write_text(json.dumps(request))
            with self.assertRaisesRegex(ValueError,'DO'):validate_request(file_record(record['path']))

    def test_predecessor_receipt_cannot_forge_clean_finish(self):
        with tempfile.TemporaryDirectory() as directory:
            ledger,record,request,sources,live=self.prepare(Path(directory))
            from vipe_benchmark.depth_driver_diagnostic import check_predecessor
            check_predecessor(ledger.events(),request)
            finish=read_json(request['predecessor_finish']['path']);finish['cleanup_confirmed']=False
            Path(request['predecessor_finish']['path']).write_text(json.dumps(finish))
            request['predecessor_finish']=file_record(request['predecessor_finish']['path'])
            with self.assertRaisesRegex(ValueError,'clean predecessor'):check_predecessor(ledger.events(),request)

    def test_substituted_manifest_and_dangling_trace_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);ledger,record,request,sources,live=self.prepare(root)
            from vipe_benchmark.depth_driver_diagnostic import check_predecessor
            substitute=root/'substitute.json';write_json(substitute,read_json(request['dependencies']['path']))
            with self.assertRaisesRegex(ValueError,'predecessor installed'):
                check_predecessor(ledger.events(),dict(request,dependencies=file_record(substitute)))
            trace=Path(request['output']).with_suffix('.syscalls.log')
            trace.symlink_to(root/'missing'/'outside.log')
            with self.assertRaisesRegex(ValueError,'trace symlink'):validate_request(record)

"""Exact immutable historical owner alias; no shared state or execution."""
import importlib.util
from pathlib import Path
import unittest
import json,hashlib,math,tempfile
from vipe_benchmark.ledger import Ledger
from unittest.mock import patch

PATH = Path(__file__).resolve().parents[1] / 'docs/research/vipe-alternatives/plan069-D9-recovery-causal-001/prepare_reconciliation_admission.py'
spec = importlib.util.spec_from_file_location('recovery_admission_producer', PATH)
assert spec and spec.loader
producer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(producer)


class HistoricalPreservationChargeTests(unittest.TestCase):
    def setUp(self):
        self.evidence = dict(path='/home/auss/git_repos/samaust/Experiments_4DGS/.local/plan069-worktrees/'
            'depth-extension/.local/D9-frame-recovery-outcome-001/preservation-receipt.json',
            sha256='f15273481e8a19f2abddc8bd9d705f0b400df8197c6e9a77d61d84740e71c6fe', bytes=1715)
        self.event = dict(sequence=785, event='cpu_preparation_charge', resource='cpu',
            event_sha256='287a285eb7b2dc231f251b477ac9c27476686e0abb57d43ba5bc2fd2dce48017',
            evidence=self.evidence, elapsed_seconds=30.002395444000285)
        self.document = dict(schema='plan069-cpu-preservation/v1', record_kind='actual', cpu_preparation_owner='D9')

    def owner(self, event):
        with patch.object(producer, 'record', return_value=self.evidence), \
             patch.object(producer, 'read', return_value=self.document):
            return producer.preservation_charge_owner(event)

    def test_exact_retained_785_is_consumed_d9_cpu(self):
        self.assertEqual(self.owner(self.event), 'D9')
        self.assertEqual(self.event['elapsed_seconds'], 30.002395444000285)

    def test_no_generic_owner_alias(self):
        self.assertIsNone(self.owner(dict(self.event, sequence=786)))

    def test_mutated_event_or_receipt_rejected(self):
        for key, value in [('event', 'note'), ('resource', 'setup'), ('event_sha256', 'forged'),
                           ('evidence', {}), ('elapsed_seconds', 0)]:
            with self.subTest(key=key), self.assertRaisesRegex(ValueError, 'exact protected historical'):
                self.owner(dict(self.event, **{key: value}))
        self.document['cpu_preparation_owner'] = 'D6'
        with self.assertRaisesRegex(ValueError, 'exact historical D9'):
            self.owner(self.event)

    def test_changed_retained_receipt_bytes_rejected(self):
        with patch.object(producer, 'record', return_value=dict(self.evidence, sha256='changed')):
            with self.assertRaisesRegex(ValueError, 'exact protected historical'):
                producer.preservation_charge_owner(self.event)


class GlobalCpuAccumulationTests(unittest.TestCase):
    def test_public_admission_matches_sequential_ledger_not_accurate_sum(self):
        # Modern builtin sum compensates rounding; the persisted ledger uses +=.
        # Patch this producer's builtin lookup to reproduce that host behavior
        # even if a future fixture interpreter uses an older builtin algorithm.
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);run=root/'run';run.mkdir();out=root/'admission'
            def save(name,value):
                path=root/name;path.parent.mkdir(parents=True,exist_ok=True)
                path.write_text(json.dumps(value));return producer.record(path)
            helper=save('helper.json',{'fixture':True})
            archive=save('archive.json',{'fixture':'archive'})
            profile=save('profile.json',{'fixture':'profile'})
            maps=dict(candidate='D9',allocation=dict(cpu_seconds=3600),candidate_config=dict(code=dict(revision='pinned')),profile_inventory=profile)
            proposal_hash=hashlib.sha256(json.dumps(maps,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
            historical=save('historical-source.json',{'fixture':'accepted old006 immutable'})
            source=save('source.json',dict(schema='plan069-depth-source-review/v1',status='passed',candidate='D9',reviewer='independent',local_sources=[helper],proposal_sha256=proposal_hash,source_revision='pinned',profile_inventory=profile,source_archive=archive,source_files=[]))
            accepted_review=save('accepted-review.json',dict(proposals=[maps]))
            authorization=save('accepted-DO.json',dict(schema='plan069-depth-user-authorization/v1',status='DO',review=accepted_review,candidate_approvals=[dict(candidate='D9',status='approved',max_attempts=1,proposal_sha256=proposal_hash)]))
            review=save('review.json',dict(proposals=[dict(candidate='D9',allocation=dict(cpu_seconds=3600))]))
            save('configs/vipe-alternatives/benchmark-v1.json',dict(cpu_prepare_score_report_seconds_limit=57600))
            job='plan069-D9-setup-recovery-002';request=dict(path='fixture-request',sha256='fixture',bytes=0)
            result=save('result.json',dict(schema='plan069-video-setup-recovery-result/v2',job_id=job,status='complete',record_kind='actual',candidate='D9',request=request,source_review=historical,review=accepted_review,authorization=authorization,source_revision='pinned',source_archive=archive,source_files=[]))
            events=[dict(event='depth_setup_authorized',candidate='D9',review=review),
                dict(event='depth_setup_recovery_authorized',job_id=job,source_review=historical,request=request,review=accepted_review,authorization=authorization),
                dict(event='finish',job_id=job,status='complete',resource='setup',elapsed_seconds=0.,cleanup_confirmed=True,cleanup_uncertain=False,surviving_pids=[],deadline_exceeded=False,result=result),
                dict(event='finish',job_id='cpu-fixture',resource='cpu',elapsed_seconds=1.),
                dict(event='cpu_preparation_charge',resource='cpu',elapsed_seconds=2.**-53,evidence=helper),
                dict(event='checkpoint',job_id='cpu-checkpoint',resource='cpu',elapsed_seconds=2.**-53),
                dict(event='finish',job_id='gpu-fixture',resource='gpu',elapsed_seconds=99.)]
            previous=None
            for index,row in enumerate(events):
                row.update(sequence=index,previous_sha256=previous)
                previous=hashlib.sha256(json.dumps(row,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest();row['event_sha256']=previous
            (run/'ledger.jsonl').write_text(''.join(json.dumps(row)+'\n' for row in events))
            expected=Ledger.__new__(Ledger).totals(events)['cpu']['elapsed_seconds']
            self.assertEqual(expected,1.)
            self.assertNotEqual(math.fsum([1.,2.**-53,2.**-53]),expected)
            args=['prepare','--checkout',str(root),'--run',str(run),'--output',str(out),'--source-review',source['path']]
            with patch('sys.argv',args),patch.object(producer.subprocess,'check_output',side_effect=lambda args,**kwargs:'fixture-head\n' if args[1]=='rev-parse' else ''),patch.object(producer,'sum',math.fsum,create=True),patch.object(producer,'current_public_sources',return_value=[helper],create=True):
                producer.main()
            admitted=producer.read(out/'admission.json')
            self.assertEqual(admitted['global_cpu_elapsed_seconds'],expected)
            self.assertEqual(admitted['global_cpu_remaining_seconds'],57600.-expected)
            self.assertEqual(admitted['candidate_cpu_elapsed_seconds'],0.)


class FreshPhaseSourceTests(unittest.TestCase):
    def test_fresh_review_cannot_replace_history_or_change_scientific_binding(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            def save(name,value):
                path=root/name;path.write_text(json.dumps(value));return producer.record(path)
            old=save('old.json',{'immutable':'old accepted source'})
            helper=save('helper.json',{'new':'phase bytes'})
            archive=save('archive.json',{'pinned':'archive'})
            profile=save('profile.json',{'pinned':'profile'})
            maps=dict(candidate='D9',candidate_config=dict(code=dict(revision='pinned')),profile_inventory=profile)
            hashed=hashlib.sha256(json.dumps(maps,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
            review=save('review.json',dict(proposals=[maps]))
            DO=save('DO.json',dict(schema='plan069-depth-user-authorization/v1',status='DO',review=review,candidate_approvals=[dict(candidate='D9',status='approved',max_attempts=1,proposal_sha256=hashed)]))
            grant=dict(source_review=old,review=review,authorization=DO)
            result=dict(grant,source_revision='pinned',source_archive=archive,source_files=[])
            source=dict(schema='plan069-depth-source-review/v1',candidate='D9',status='passed',reviewer='independent',local_sources=[helper],proposal_sha256=hashed,source_revision='pinned',profile_inventory=profile,source_archive=archive,source_files=[])
            with patch.object(producer,'current_public_sources',return_value=[helper]):
                producer.validate_phase_source(source,grant,result,root)
                for key,value in [('proposal_sha256','wrong'),('source_revision','wrong'),('source_archive',{}),('source_files',[{}]),('local_sources',[]),('reviewer',''),('schema','wrong'),('profile_inventory',{})]:
                    with self.subTest(key=key),self.assertRaises(ValueError):
                        producer.validate_phase_source(dict(source,**{key:value}),grant,result,root)
                with self.assertRaisesRegex(ValueError,'historical'):
                    producer.validate_phase_source(source,grant,dict(result,source_review=helper),root)
                with self.assertRaisesRegex(ValueError,'accepted map proposal DO'):
                    approval=producer.read(DO['path']);approval['status']='REVIEW';Path(DO['path']).write_text(json.dumps(approval))
                    changed=producer.record(DO['path'])
                    producer.validate_phase_source(source,dict(grant,authorization=changed),dict(result,authorization=changed),root)

    def test_public_closure_refuses_other_checkout(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(ValueError,'different checkout'):
                producer.current_public_sources(Path(directory))

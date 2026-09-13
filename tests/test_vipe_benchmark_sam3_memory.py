"""Synthetic memory lifecycle, equality gate and bounded diagnostic accounting."""
from pathlib import Path
from types import SimpleNamespace
from contextlib import nullcontext
import json
import sys
import tempfile
import unittest
from unittest.mock import patch
import weakref
import numpy as np

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from vipe_benchmark.sam3_memory import MemoryObserver, CLEANUP, DIAGNOSTIC, compare_partial, validate_diagnostic_review
from vipe_benchmark.backends import SAM3Backend
from vipe_benchmark.files import file_record, write_json
from vipe_benchmark.config import load
from vipe_benchmark.ledger import Ledger


class MemoryTests(unittest.TestCase):
    def test_semantic_state_and_native_output_released_before_next_init(self):
        refs=[]; observations=[]
        class State(dict): pass
        class Output(dict): pass
        class Video:
            def init_state(self,**kwargs):
                if refs:
                    assert refs[-1][0]() is None and refs[-1][1]() is None
                state=State();refs.append([weakref.ref(state),lambda:None]);return state
            def add_prompt(self,state,**kwargs):state['concept']=kwargs['text_str']
            def propagate_in_video(self,state,**kwargs):
                for frame in (0,1):
                    output=Output(out_binary_masks=np.ones((1,2,2),bool),out_probs=np.array([.8]),out_obj_ids=np.array([7]))
                    refs[-1][1]=weakref.ref(output)
                    yield frame,output
            def reset_state(self,state):state.clear()
        class Observer:
            def phase(self,*args):pass
            def cleanup(self,semantic):observations.append((semantic,refs[-1][0]() is None,refs[-1][1]() is None))
        backend=SAM3Backend(lambda:None,Video,SimpleNamespace(inference=lambda *_:nullcontext()))
        backend.memory_observer=Observer()
        result=backend.segment([np.zeros((2,2,3),np.uint8)]*2,[np.ones((2,2),bool)]*2,frame_ids=[0,1])
        self.assertEqual(observations,[('person',True,True),('basketball',True,True)])
        self.assertEqual(len(result),2)
        self.assertEqual(result[0].semantics['2']['class'],'basketball')

    def test_observer_separates_reference_gc_and_allocator_phases(self):
        with tempfile.TemporaryDirectory() as t:
            calls=[]
            cuda=SimpleNamespace(synchronize=lambda:None,mem_get_info=lambda:(90,100),memory_stats=lambda:{},
                memory_allocated=lambda:3,memory_reserved=lambda:7,max_memory_allocated=lambda:5,max_memory_reserved=lambda:9,
                empty_cache=lambda:calls.append('empty_cache'),memory=SimpleNamespace(
                    _record_memory_history=lambda **kw:calls.append(kw),_snapshot=lambda:{'segments':[]}))
            observer=MemoryObserver(SimpleNamespace(cuda=cuda),t,diagnostic=True);observer.pair=1
            with patch('vipe_benchmark.sam3_memory.gc.collect',side_effect=lambda:calls.append('gc')):
                observer.cleanup('person')
            summary=observer.finish()
            events=[json.loads(s) for s in (Path(t)/'memory-events.jsonl').read_text().splitlines()]
            self.assertEqual([e['phase'] for e in events],['observer_started','after_release','after_gc','after_empty_cache','finished'])
            self.assertEqual(calls[1:3],['gc','empty_cache'])
            self.assertEqual(events[1]['allocated_bytes'],3);self.assertEqual(events[1]['reserved_bytes'],7)
            self.assertEqual(calls[-1],{'enabled':None});self.assertTrue(Path(summary['path']).exists())

    def test_exact_overlap_comparison_detects_changed_labels(self):
        import cv2
        from vipe_benchmark.access import output_identities
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);rows=[];old=root/'old'
            for i,identity in enumerate(output_identities(load(),'reconstruction')[:82]):
                before=old/identity.key();after=root/'new'/identity.key()
                for stem in (before,after):
                    stem.parent.mkdir(parents=True,exist_ok=True)
                    np.save(stem.with_suffix('.npy'),np.ones((2,2),np.int32))
                    cv2.imwrite(str(stem.with_suffix('.png')),np.zeros((2,2),np.uint8))
                rows.append(dict(identity=identity.record(),instances=file_record(after.with_suffix('.npy')),semantic_static=file_record(after.with_suffix('.png'))))
            self.assertEqual(compare_partial(rows,old)['status'],'identical')
            changed=Path(rows[-1]['instances']['path']);np.save(changed,np.zeros((2,2),np.int32));rows[-1]['instances']=file_record(changed)
            result=compare_partial(rows,old)
            self.assertEqual(result['status'],'requires-review');self.assertEqual(result['comparisons'][-1]['instance_disagreements'],4)

    def test_review_rejects_missing_evidence(self):
        with tempfile.TemporaryDirectory() as t:
            path=Path(t)/'review.json';write_json(path,dict(status='passed',cleanup=CLEANUP))
            with self.assertRaisesRegex(ValueError,'validated cleanup'):
                validate_diagnostic_review(file_record(path))


class DiagnosticBudgetTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
        self.ledger=Ledger(self.root/'ledger.jsonl',load())
        source=self.root/'source.py';source.write_text('fixture')
        validation=self.root/'validation.json';write_json(validation,dict(status='passed',sources=[file_record(source)]));self.validation=file_record(validation)
        self.ledger.reserve('S3-reconstruction',[],{});original=self.ledger.finish('S3-reconstruction','failed',11,cleanup_confirmed=True)
        previous=None
        for index in (1,2):
            job=f'S3-reconstruction-recovery-{index:03d}'
            doc=dict(schema='vipe-benchmark-s3-reconstruction-recovery/v1',job_id=job,original_job_id='S3-reconstruction',attempts_limit=1,
                seconds_limit=5400,reset_previous_consumption=False,gpu_total_seconds_limit=93600,unrelated_attempts_reopened=False,
                authorization='fixture approval',repair_validation=self.validation,original_failure_event_sha256=original['event_sha256'])
            if previous:doc['previous_recovery_failure_event_sha256']=previous['event_sha256']
            path=self.root/f'recovery{index}.json';write_json(path,doc);self.ledger.authorize_reconstruction_recovery(file_record(path))
            self.ledger.reserve(job,[],{});previous=self.ledger.finish(job,'failed',20,cleanup_confirmed=True)
        self.doc=dict(schema='vipe-benchmark-s3-memory-diagnostic/v1',job_id=DIAGNOSTIC,attempts_limit=1,seconds_limit=600,pairs_limit=48,
            gpu_total_seconds_limit=93600,reset_previous_consumption=False,unrelated_attempts_reopened=False,authorization='fixture diagnostic approval',
            repair_validation=self.validation,previous_failure_event_sha256=previous['event_sha256'])
        self.full=dict(doc,job_id='S3-reconstruction-recovery-003',previous_recovery_failure_event_sha256=previous['event_sha256'])

    def authorize(self,**changes):
        path=self.root/f'diagnostic-{len(list(self.root.glob("diagnostic*")))}.json';write_json(path,dict(self.doc,**changes))
        return self.ledger.authorize_memory_diagnostic(file_record(path))

    def test_exact_single_600_second_diagnostic_without_reopening_full(self):
        before=self.ledger.path.read_bytes();self.authorize();self.assertTrue(self.ledger.path.read_bytes().startswith(before))
        self.assertEqual(self.ledger.reserve(DIAGNOSTIC,[],{})['seconds'],600)
        self.ledger.finish(DIAGNOSTIC,'failed',50,cleanup_confirmed=True)
        self.assertEqual(self.ledger.totals()['gpu']['attempts'],4)
        for action in (lambda:self.authorize(),lambda:self.ledger.reserve(DIAGNOSTIC,[],{})):
            with self.assertRaises(ValueError):action()
        path=self.root/'full.json';write_json(path,self.full)
        with self.assertRaisesRegex(ValueError,'conditional'):
            self.ledger.authorize_reconstruction_recovery(file_record(path))

    def test_bounds_and_unregistered_diagnostic_rejected(self):
        with self.assertRaises(ValueError):self.ledger.reserve(DIAGNOSTIC,[],{})
        for changes in (dict(pairs_limit=49),dict(seconds_limit=601),dict(attempts_limit=2),dict(previous_failure_event_sha256='wrong')):
            with self.subTest(changes=changes),self.assertRaises(ValueError):self.authorize(**changes)
        with self.assertRaises(ValueError):self.ledger.note('memory_diagnostic_authorized')

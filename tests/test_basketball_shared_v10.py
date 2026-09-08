"""No extra optimization: durable transaction faults and numerical-boundary regressions."""
import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from basketball_shared_storage_v10 import publish,read,sha,Journal,journal_prefix,commit_attempt,recover_attempt,PersistenceError
from basketball_shared_verify_v10 import inspect_attempt
from basketball_shared_accounting_v10 import CanonicalAdapter,Ledger,reconcile,bytes_of
from basketball_shared_recovery_v8 import fixture
from basketball_shared_solver_v6 import EvaluationLimit

class StorageTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
    def tearDown(self):self.temp.cleanup()
    def allocated(self):
        j=Journal(self.root/'journal.jsonl');j.append('allocated',id='a')
        return dict(id='a',row=dict(valid=False),value=[1.])
    def verify(self,item,directory):
        assert item['id']=='a' and item['value']==[1.]
        return dict(passed=True)
    def test_numpy_and_nonfinite_encoding(self):
        p=self.root/'a.json.gz';publish(p,dict(array=np.array([1.]),number=np.int64(2)))
        self.assertEqual(read(p),dict(array=[1.],number=2))
        for value in [dict(bad=object()),dict(bad=np.array([np.nan])),dict(bad=np.float64(np.inf))]:
            q=self.root/'bad.gz'
            with self.assertRaises((TypeError,ValueError)):publish(q,value)
            self.assertFalse(q.exists())
        self.assertEqual(len(list(self.root.iterdir())),1)
    def test_no_overwrite_duplicate_id(self):
        item=self.allocated();commit_attempt(self.root,item,self.verify);old=sha(self.root/'attempt.json.gz')
        with self.assertRaises(PersistenceError):commit_attempt(self.root,item,self.verify)
        with self.assertRaises(FileExistsError):Journal(self.root/'journal.jsonl')
        self.assertEqual(sha(self.root/'attempt.json.gz'),old)
    def test_before_publication_failure(self):
        item=self.allocated()
        with self.assertRaises(PersistenceError):commit_attempt(self.root,item,self.verify,'before_publish')
        self.assertFalse((self.root/'attempt.json.gz').exists());self.assertFalse((self.root/'receipt.json').exists())
        self.assertEqual([e['event'] for e in journal_prefix(self.root/'journal.jsonl')['events']],['allocated'])
    def test_after_publication_recovery_never_reruns(self):
        item=self.allocated()
        with self.assertRaises(PersistenceError):commit_attempt(self.root,item,self.verify,'after_publish')
        self.assertTrue((self.root/'attempt.json.gz').exists());self.assertFalse((self.root/'receipt.json').exists())
        with patch('basketball_shared_solver_v10.minimize',side_effect=AssertionError('no solver allowed')):
            recover_attempt(self.root,self.verify);recover_attempt(self.root,self.verify)
        self.assertEqual(sum(e['event']=='completed' for e in journal_prefix(self.root/'journal.jsonl')['events']),1)
    def test_failure_after_receipt_before_completion(self):
        item=self.allocated();original=Journal.append
        def fail(j,event,**data):
            if event=='completed':raise PersistenceError('injected completion failure')
            return original(j,event,**data)
        with patch.object(Journal,'append',fail):
            with self.assertRaises(PersistenceError):commit_attempt(self.root,item,self.verify)
        self.assertTrue((self.root/'receipt.json').exists());recover_attempt(self.root,self.verify)
    def test_bad_verification_does_not_complete(self):
        item=self.allocated()
        def fail(*args):raise ArithmeticError('corrupt arithmetic')
        with self.assertRaises(PersistenceError):commit_attempt(self.root,item,fail)
        self.assertFalse((self.root/'receipt.json').exists())
        self.assertFalse(any(e['event']=='completed' for e in journal_prefix(self.root/'journal.jsonl')['events']))
    def test_truncated_prefix_and_missing_worker(self):
        self.assertIsNone(inspect_attempt(self.root)['numerical_entries'])
        j=Journal(self.root/'journal.jsonl');j.append('numerical_entry',index=0)
        good=(self.root/'journal.jsonl').read_bytes()
        with (self.root/'journal.jsonl').open('ab') as f:f.write(b'{"seq":1')
        prefix=journal_prefix(j.path);self.assertEqual(prefix['valid_bytes'],len(good));self.assertFalse(prefix['complete'])
        self.assertIsNone(inspect_attempt(self.root)['numerical_entries'])
        with self.assertRaises(PersistenceError):Journal(j.path,recover=True)
    def test_checksum_corruption_stops_at_first_bad_record(self):
        j=Journal(self.root/'journal.jsonl');j.append('a');j.append('b');j.append('c')
        lines=j.path.read_bytes().splitlines(keepends=True);lines[1]=lines[1].replace(b'"b"',b'"x"');j.path.write_bytes(b''.join(lines))
        self.assertEqual(len(journal_prefix(j.path)['events']),1)
    def test_hash_mismatch_and_corrupt_record(self):
        item=self.allocated();commit_attempt(self.root,item,self.verify)
        with self.assertRaises(PersistenceError):recover_attempt(self.root,self.verify,expected='0'*64)
        f=self.root/'attempt.json.gz';f.write_bytes(b'corrupt')
        with self.assertRaises((AssertionError,OSError,ValueError)):inspect_attempt(self.root)
    def test_completion_without_artifact(self):
        j=Journal(self.root/'journal.jsonl');j.append('completed',artifact_sha256='0'*64,receipt_sha256='0'*64)
        with self.assertRaises(AssertionError):inspect_attempt(self.root)
    def test_sync_directory_and_journal(self):
        with patch('basketball_shared_storage_v10.os.fsync',wraps=os.fsync) as sync:
            publish(self.root/'a.json',dict(a=1));Journal(self.root/'journal.jsonl').append('allocated')
            self.assertGreaterEqual(sync.call_count,5)

class BoundaryTests(unittest.TestCase):
    def test_exact_adjacent_and_no_201st_entry(self):
        with tempfile.TemporaryDirectory() as t:
            j=Journal(Path(t)/'journal');l=Ledger('unit',[1.],journal=j)
            a=l.request([1.],'constraint');b=l.request([np.nextafter(1.,2.)],'hessian');self.assertNotEqual(a.identity,b.identity)
            for i in range(2,200):l.request([float(i+1)],'trial')
            with self.assertRaises(EvaluationLimit):l.request([201.],'constraint_first')
            self.assertEqual(len(l.states),200);self.assertEqual(len(journal_prefix(j.path)['events']),200)
    def test_actual_boundaries_and_first_request_routes(self):
        for route in ['fun','jac','hess','depth']:
            with tempfile.TemporaryDirectory() as t:
                p=fixture(2,0.,1.);p.journal=Journal(Path(t)/'journal');a=CanonicalAdapter(p);q=p.x0/a.scale
                getattr(a,route)(q);a.fun(q);a.jac(q);a.hess(q);a.depth(q)
                result=a.export();reconcile(result);self.assertEqual(len(a.ledger.states),1)
                entries=[e for e in journal_prefix(p.journal.path)['events'] if e['event']=='numerical_entry']
                self.assertEqual(len(entries),len(result['observed_numerical_entries']))
                self.assertTrue(all(e['physical_hex']==bytes_of(q*a.scale).hex() for e in entries))
    def test_entry_survives_numerical_exception(self):
        with tempfile.TemporaryDirectory() as t:
            p=fixture(2,0.,1.);p.journal=Journal(Path(t)/'journal');a=CanonicalAdapter(p)
            with patch.object(p,'evaluate',side_effect=TimeoutError('interrupt')):
                with self.assertRaises(TimeoutError):a.fun(p.x0/a.scale)
            events=journal_prefix(p.journal.path)['events'];self.assertEqual(events[-1]['status'],'interrupted');reconcile(a.export())
    def test_shared_initialization_budget_and_seed_namespace(self):
        from basketball_shared_initialization_v9 import sanitize
        a=CanonicalAdapter(fixture(2,0.,1.),'baseline');b=CanonicalAdapter(fixture(2,0.,1.),'candidate')
        self.assertNotEqual(a.problem_key,b.problem_key);sanitize(a);before=len(a.ledger.states)
        a.set_transform(a.p.x0,True);a.depth(np.zeros(len(a.p.x0)));self.assertEqual(len(a.ledger.states),before)
    def test_descendants_killed(self):
        from basketball_shared_workflow_v10 import terminate_group
        with tempfile.TemporaryDirectory() as t:
            path=Path(t)/'pid';script='import subprocess,time,pathlib; p=subprocess.Popen(["sleep","30"]); pathlib.Path('+repr(str(path))+').write_text(str(p.pid)); time.sleep(30)'
            child=subprocess.Popen([sys.executable,'-c',script],start_new_session=True)
            try:
                for _ in range(100):
                    if path.exists():break
                    time.sleep(.01)
                pid=int(path.read_text());terminate_group(child)
                stat=Path(f'/proc/{pid}/stat')
                self.assertTrue(not stat.exists() or stat.read_text().split()[2]=='Z')
            finally:
                if child.poll() is None:terminate_group(child)
    def test_failure_prevents_following_dispatch(self):
        import basketball_shared_workflow_v10 as w
        from types import SimpleNamespace
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);(root/'prepare').mkdir();publish(root/'prepare/benchmark-manifest.json',{})
            p={'v10':{'absolute_deadlines':{'baseline':time.time()+60}}};tasks=[dict(id=str(i)) for i in range(7)]
            with patch.object(w,'ROOT',root),patch('basketball_shared_benchmark_v9.jobs',return_value=tasks),patch.object(w,'launch_worker',return_value=SimpleNamespace(poll=lambda:1)) as launch:
                with self.assertRaises(PersistenceError):w.run_policy(p,root/'policy',dict(name='baseline'),'baseline')
                self.assertEqual(launch.call_count,6)

if __name__=='__main__':unittest.main()

"""Corrupt saved evidence without new optimization and require verifier rejection."""
from pathlib import Path
import copy
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from basketball_shared_storage_v10 import read,sha
from basketball_shared_verify_v10 import verify_item
from basketball_shared_report_v10 import detailed_evidence
ROOT=Path('docs/experiments/basketball-shared-timing-v10')

class SavedEvidenceTests(unittest.TestCase):
    def item(self,relative):
        directory=ROOT/relative;artifact=directory/'attempt.json.gz';item=read(artifact)
        item['artifact']=dict(artifact=str(artifact),sha256=sha(artifact))
        return item,directory
    def test_real_control_still_verifies(self):
        item,directory=self.item('persist/preflight-four-0/cold')
        self.assertTrue(verify_item(item,directory)['passed']);self.assertTrue(detailed_evidence(item)['passed'])
    def test_fabricated_entry_count_rejected(self):
        item,directory=self.item('persist/preflight-four-0/cold')
        item['row']['accounting']['observed_numerical_entries'].pop()
        with self.assertRaises(AssertionError):verify_item(item,directory)
    def test_cross_policy_seed_rejected(self):
        item,directory=self.item('baseline/policy/conditional-02/ascending')
        self.assertIsNotNone(item['row']['seed']);item['row']['seed']['policy']='preflight'
        with self.assertRaises(AssertionError):verify_item(item,directory)
    def test_trace_parameter_corruption_rejected(self):
        item,_=self.item('persist/preflight-four-0/cold');item['row']['solver_trace'][0]['x'][0]+=1
        with self.assertRaises(AssertionError):detailed_evidence(item)
    def test_multiplier_mapping_corruption_rejected(self):
        item,_=self.item('persist/preflight-four-0/cold');item['row']['multipliers_transformed'][0]+=1
        with self.assertRaises(AssertionError):detailed_evidence(item)
    def test_support_corruption_rejected(self):
        item,_=self.item('persist/preflight-four-0/cold');item['row']['original_support'][0]['data_norms'][0]+=1
        with self.assertRaises(AssertionError):detailed_evidence(item)
    def test_supervisor_packages_missing_result_and_kills_descendants(self):
        import json
        import subprocess
        import tempfile
        import time
        from unittest.mock import patch
        import basketball_shared_workflow_v10 as workflow
        real_popen=subprocess.Popen
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);config=root/'config.json';started=time.time()
            config.write_text(json.dumps(dict(investigation_started_unix=started,v10=dict(absolute_deadlines=dict(baseline=started+30)))))
            pid_file=root/'descendant';failure=root/'baseline/failure.json'
            program=('import subprocess,time,pathlib; '
                     'p=subprocess.Popen(["sleep","30"]); '
                     'pathlib.Path('+repr(str(pid_file))+').write_text(str(p.pid)); '
                     'pathlib.Path('+repr(str(failure))+').write_text("{}\\n"); time.sleep(30)')
            def launch(*args,**kwargs):return real_popen([sys.executable,'-c',program],start_new_session=True)
            with patch.object(workflow,'ROOT',root),patch.object(workflow,'CONFIG',config),patch.object(workflow.subprocess,'Popen',launch):
                self.assertEqual(workflow.main('baseline'),1)
            result=read(root/'baseline/result.json');self.assertEqual(result['status'],'blocked')
            self.assertNotIn('solver_invocations',result)
            pid=int(pid_file.read_text());stat=Path(f'/proc/{pid}/stat')
            self.assertTrue(not stat.exists() or stat.read_text().split()[2]=='Z')

    def test_different_execution_source_rejected(self):
        item,directory=self.item('persist/preflight-four-0/cold')
        key=next(iter(item['identity']['execution_sha256']));item['identity']['execution_sha256'][key]='0'*64
        from basketball_shared_storage_v10 import PersistenceError
        with self.assertRaises(PersistenceError):verify_item(item,directory)

if __name__=='__main__':unittest.main()

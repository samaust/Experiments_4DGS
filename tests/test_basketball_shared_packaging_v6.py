import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch,Mock
from argparse import Namespace
import subprocess
import signal
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from basketball_scale import read,write
from basketball_shared_report_v6 import report_partial
from basketball_shared_workflow_v6 import main

class PackagingV6Tests(unittest.TestCase):
    def test_diagnosis_only_and_timeout_without_later_artifacts(self):
        for kind in ['numerical_failure','budget_exhaustion']:
            with tempfile.TemporaryDirectory() as d:
                root=Path(d)/'run';(root/'package').mkdir(parents=True)
                write(root/'package/result.json',dict(status='blocked',terminal_kind=kind,blockers=['fixed gate stopped work']))
                report_partial(root,dict(investigation_started_unix=0))
                result=read(root/'result.json')
                self.assertEqual(result['pilot_executed'],0);self.assertEqual(result['pilot_missing'],144)
                self.assertIsNone(result['pilot_decision']);self.assertIsNone(result['accepted_timing'])
                self.assertFalse((root/'pilot').exists())

    def test_external_watchdog_terminates_process_group_and_writes_blocker(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);config=root/'config.json';out=root/'output'
            write(config,dict(investigation_started_unix=0))
            child=Mock(pid=4321)
            child.wait.side_effect=[subprocess.TimeoutExpired('worker',1),subprocess.TimeoutExpired('worker',2),0]
            def launch(*args,**kwargs):
                self.assertTrue(kwargs['start_new_session']);out.mkdir()
                write(out/'frozen.json',dict(source_sha256={}))
                return child
            with patch('basketball_shared_workflow_v6.time.time',return_value=1799.),patch('basketball_shared_workflow_v6.subprocess.Popen',side_effect=launch),patch('basketball_shared_workflow_v6.os.killpg') as kill:
                result=main(Namespace(output=out,config=config,stage='pilot'))
            self.assertEqual(result,1)
            self.assertEqual(kill.call_args_list[0].args,(4321,signal.SIGTERM))
            self.assertEqual(kill.call_args_list[1].args,(4321,signal.SIGKILL))
            self.assertEqual(read(out/'result.json')['terminal_kind'],'budget_exhaustion')

    def test_ninety_minute_gate_blocks_before_launch(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);config=root/'config.json';write(config,dict(investigation_started_unix=0))
            with patch('basketball_shared_workflow_v6.time.time',return_value=5400.),patch('basketball_shared_workflow_v6.subprocess.Popen') as launch:
                with self.assertRaises(TimeoutError):main(Namespace(output=root/'out',config=config,stage='safeguard'))
                launch.assert_not_called()

if __name__=='__main__':unittest.main()

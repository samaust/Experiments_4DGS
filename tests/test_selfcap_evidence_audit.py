import copy
import importlib.util
from pathlib import Path
import tempfile
import unittest
from PIL import Image

SPEC=importlib.util.spec_from_file_location('audit',Path(__file__).resolve().parents[1]/'scripts/audit-selfcap-evidence.py')
audit=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(audit)

class EvidenceTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name);self.a=audit.Audit(self.root)
    def test_valid_graph_and_changed_png(self):
        p=self.root/'frame.png';Image.new('RGB',(3,2),'red').save(p);sha=audit.digest(p)
        self.a.file(p,sha,image_size=[3,2]);self.assertTrue(all(c['status']=='passed' for c in self.a.checks))
        Image.new('RGB',(3,2),'blue').save(p);changed=audit.Audit(self.root);changed.file(p,sha,image_size=[3,2]);self.assertEqual(changed.checks[0]['status'],'failed')
    def test_missing_bundle_component(self):
        self.a.file('mlp_offset.pth','a'*64,10);self.assertEqual(self.a.checks[0]['status'],'failed')
    def test_membership(self):
        self.assertTrue(audit.membership([('0015',1),('0015',2)],[('0015',1),('0015',2)]))
        self.assertFalse(audit.membership([('0015',1),('0015',1)],[('0015',1),('0015',2)]))
        self.assertFalse(audit.membership([('0015',1)],[('0015',1),('0015',2)]))
    def test_bad_time(self):
        c=dict(synchronization_offset_seconds=.1,frames=[dict(frame_id=10,timestamp_seconds=.9,normalized_time=.45),dict(frame_id=11,timestamp_seconds=1.,normalized_time=.5)])
        self.assertTrue(audit.validate_times(c,dict(origin_seconds=0,duration_seconds=2),10));c['frames'][1]['normalized_time']=.6
        self.assertFalse(audit.validate_times(c,dict(origin_seconds=0,duration_seconds=2),10))
    def test_sweep_and_disagreement(self):
        p=self.root/'sweep.png';Image.new('RGB',(2,2)).save(p);sha=audit.digest(p)
        self.a.file(p,'0'*64);self.assertEqual(self.a.checks[-1]['status'],'failed')
        expected={'poses':[{'T':[1,2,3]} for _ in range(20)],'normalized_time':.5,'frame_id':4150,'start_camera':'0015','end_camera':'0014','intrinsics_camera':'0015'};changed=copy.deepcopy(expected);changed['poses'][0]['T'][0]=2
        self.assertTrue(audit.validate_sweep(expected,expected))
        self.assertFalse(audit.validate_sweep(changed,expected))
    def test_aggregate_mismatch(self):
        metrics=dict(per_frame=[dict(psnr=1.),dict(psnr=3.)],aggregate=dict(psnr=7.))
        self.assertFalse(audit.close(audit.metric_means(metrics)['psnr'],metrics['aggregate']['psnr']))
    def test_unavailable_is_not_passed_and_output_refusal(self):
        self.a.check('runtime',None);self.a.file('required-source.py','0'*64)
        self.assertEqual([c['status'] for c in self.a.checks],['unavailable','failed'])
        with self.assertRaises(ValueError):audit.new_destinations(self.root,self.root,self.root/'assets')
        with self.assertRaises(ValueError):audit.new_destinations(self.root,self.root/audit.PROFILE/'new',self.root/'assets')

class StageTests(unittest.TestCase):
    def test_internal_isolation_entrypoints_and_incomplete_stage(self):
        stages=[dict(label=label,status='completed',exit_code=0,command=['python','scripts/render-atgs-manifest.py']) for label in ('reload-a','reload-b')]
        self.assertTrue(audit.completed_reload_stages({'status':'completed'},stages,'atgs'))
        stages[1]['exit_code']=1
        self.assertFalse(audit.completed_reload_stages({'status':'completed'},stages,'atgs'))
        self.assertFalse(audit.completed_reload_stages({'status':'completed'},stages[:1],'atgs'))

class MissingGraphTests(unittest.TestCase):
    def test_cli_retains_report_when_required_manifest_missing(self):
        import subprocess
        import sys
        import json
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);output=root/'report'
            result=subprocess.run([sys.executable,str(Path(audit.__file__)), '--root',str(root),'--output',str(output),'--assets-output',str(root/'assets')],capture_output=True,text=True)
            self.assertEqual(result.returncode,1,result.stderr)
            report=json.loads((output/'audit.json').read_text())
            self.assertTrue(any(c['status']=='failed' and 'manifest.json' in c['id'] for c in report['checks']))
            self.assertFalse((output/'inspection.html').exists())
    def test_missing_crop_cannot_present(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);a=audit.Audit(root)
            with self.assertRaises(KeyError):audit.presentation(a,root/'report',root/'assets')
            self.assertEqual(a.checks[0]['status'],'failed')
            self.assertFalse((root/'assets').exists())

if __name__=='__main__':unittest.main()

"""Worker and supervisor share protected video setup byte ceilings."""
import copy
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from vipe_benchmark.video_setup_budget import setup_byte_limits
from vipe_benchmark.files import object_hash

class VideoSetupBudgetTests(unittest.TestCase):
    def setUp(self):
        self.request=dict(record_kind='actual',candidate='D9',review={'sha256':'review'},authorization={'sha256':'do'})
        self.proposal=dict(candidate='D9',allocation=dict(download_bytes=6*2**30,artifact_bytes=9*2**30))
        self.baseline=dict(download_bytes=20*2**30,artifact_bytes=100*2**30)
        self.config=dict(new_download_gib_limit=110,new_artifact_disk_gib_limit=210)
        self.grant=dict(event='depth_setup_authorized',candidate='D9',review=self.request['review'],authorization=self.request['authorization'],proposal_sha256=object_hash(self.proposal),resource_snapshot=self.baseline)
    def limits(self,reading=None,request=None,grant=None,config=None):
        with patch('vipe_benchmark.ledger.Ledger') as ledger:
            ledger.return_value.events.return_value=[grant or self.grant]
            return setup_byte_limits(request or self.request,self.proposal,Path('/unused'),reading or self.baseline,config or self.config)
    def test_actual_baseline_is_protected_grant_not_request(self):
        request=dict(self.request,resource_snapshot=dict(download_bytes=0,artifact_bytes=199*2**30))
        self.assertEqual(self.limits(request=request)['artifact_bytes'],109*2**30)
    def test_global_cap_can_only_reduce_slot_limit(self):
        config=dict(self.config,new_artifact_disk_gib_limit=105)
        self.assertEqual(self.limits(config=config)['artifact_bytes'],105*2**30)
    def test_exact_boundary_and_one_byte_overflow(self):
        self.limits(reading=dict(self.baseline,artifact_bytes=109*2**30))
        with self.assertRaisesRegex(ValueError,'allocation exhausted'):
            self.limits(reading=dict(self.baseline,artifact_bytes=109*2**30+1))
    def test_changed_grant_lineage_rejected(self):
        with self.assertRaisesRegex(ValueError,'protected video setup'):
            self.limits(grant=dict(self.grant,proposal_sha256='wrong'))
    def test_invalid_budget_types_rejected(self):
        for allowance in (True,0,-1,9.0):
            with self.subTest(allowance=allowance):
                proposal=copy.deepcopy(self.proposal);proposal['allocation']['artifact_bytes']=allowance
                grant=dict(self.grant,proposal_sha256=object_hash(proposal))
                with patch('vipe_benchmark.ledger.Ledger') as ledger:
                    ledger.return_value.events.return_value=[grant]
                    with self.assertRaisesRegex(ValueError,'positive video setup'):
                        setup_byte_limits(self.request,proposal,Path('/unused'),self.baseline,self.config)
    def test_worker_passes_slot_artifact_ceiling_to_acquisition(self):
        import test_vipe_benchmark_video_setup as fixtures
        from vipe_benchmark.video_setup import run_video_setup
        from vipe_benchmark.budgets import budget_snapshot
        from vipe_benchmark.files import read_json
        f=fixtures.VideoSetupTests();f.setUp();self.addCleanup(f.tearDown)
        seen=[]
        def acquire(*args,**kwargs):
            seen.append(kwargs['artifact_limit']);return f.acquire(*args,**kwargs)
        result=run_video_setup(f.request,f.root/f.request['job_id'],acquire=acquire)
        allocation=read_json(f.request['review']['path'])['proposals'][0]['allocation']['artifact_bytes']
        self.assertTrue(all(limit < 210*2**30 for limit in seen))
        self.assertTrue(all(limit >= allocation for limit in seen))
        self.assertEqual(result['status'],'complete')

    def test_worker_budget_rejection_retains_failure_receipt(self):
        import test_vipe_benchmark_video_setup as fixtures
        from vipe_benchmark.video_setup import run_video_setup
        from vipe_benchmark.files import read_json
        f=fixtures.VideoSetupTests();f.setUp();self.addCleanup(f.tearDown)
        output=f.root/f.request['job_id']
        with patch('vipe_benchmark.video_setup_budget.setup_byte_limits',side_effect=ValueError('protected baseline mismatch')),patch('vipe_benchmark.video_setup._acquire') as acquire:
            with self.assertRaisesRegex(ValueError,'protected baseline mismatch'):
                run_video_setup(f.request,output,acquire=acquire)
        acquire.assert_not_called()
        failure=read_json(output/'failure.json')
        self.assertEqual(failure['status'],'failed')
        self.assertEqual(failure['bytes_received'],0)
        self.assertIn('protected baseline mismatch',failure['error'])

    def test_dispatch_supervisor_rejects_growth_inside_global_cap(self):
        import test_vipe_benchmark_video_setup as fixtures
        import basketball_vipe_video_setup_dispatch as dispatcher
        from vipe_benchmark.files import read_json, file_record, write_json
        from unittest.mock import Mock
        f=fixtures.VideoSetupTests();f.setUp();self.addCleanup(f.tearDown)
        local=f.root/'.local/vipe-alternatives/plan031-20260913T032700Z'
        (local/'requests').mkdir(parents=True)
        receipt=f.root/'source.json';write_json(receipt,{'fixture':'source'})
        worker=f.root/'scripts/basketball_vipe_video_setup.py';worker.parent.mkdir();worker.write_text('# fixture worker\n')
        ledger=Mock(path=local/'ledger.jsonl')
        proposal=read_json(f.request['review']['path'])['proposals'][0]
        baseline=dict(download_bytes=100,artifact_bytes=100,gpu_pids=[])
        ledger.events.return_value=[dict(event='depth_setup_authorized',candidate='D9',
            review=f.request['review'],authorization=f.request['authorization'],
            proposal_sha256=object_hash(proposal),resource_snapshot=baseline)]
        readings=[baseline,dict(baseline,artifact_bytes=100+proposal['allocation']['artifact_bytes']+1)]
        original_read=Path.read_text
        def read(path,*args,**kwargs):
            return 'systemd' if str(path)=='/proc/1/comm' else original_read(path,*args,**kwargs)
        def supervise(*args,**kwargs):
            return kwargs['sample_resources']()
        with patch.object(Path,'read_text',read),patch.object(dispatcher,'ROOT',f.root),\
             patch.object(dispatcher,'DO',Path(f.request['authorization']['path'])),\
             patch.object(dispatcher,'shared_run_root',return_value=f.root),\
             patch.object(dispatcher,'Ledger',return_value=ledger),\
             patch('vipe_benchmark.ledger.Ledger',return_value=ledger),\
             patch.object(dispatcher,'resources',side_effect=readings),\
             patch.object(dispatcher,'environment_request',return_value=f.runtime_request()),\
             patch.object(dispatcher,'supervise',side_effect=supervise):
            with self.assertRaisesRegex(ValueError,'allocation exhausted'):
                dispatcher.dispatch('D9',source_review_path=receipt)

if __name__=='__main__':unittest.main()

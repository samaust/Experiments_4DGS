"""Public approval selection for the separately approved D9 setup recovery."""
import copy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from vipe_benchmark.config import ROOT
from vipe_benchmark.files import file_record,object_hash,read_json,write_json


class RecoveryAuthorizationTests(unittest.TestCase):
    def setUp(self):
        from vipe_benchmark.depth_admission import VIDEO_FRAME_PROFILES
        from vipe_benchmark.video_environment import FRAME_RECIPE
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
        self.review_path=self.root/'docs/specs/plan031-execution/depth-D9-frame-recovery-review-001.json'
        self.review=read_json(ROOT/'docs/specs/plan031-execution/depth-D9-frame-recovery-review-001.json')
        self.maps=self.review['proposals'][0]
        self.maps.update(runtime_recipe=file_record(FRAME_RECIPE),profile_inventory=file_record(VIDEO_FRAME_PROFILES))
        self.recovery=self.review['setup_recovery_proposal']
        self.recovery.update(runtime_recipe=self.maps['runtime_recipe'],profile_inventory=self.maps['profile_inventory'])
        self.recovery['original_setup']['request']=dict(path=str(self.root/'run/requests/original.json'),sha256='a'*64,bytes=1)
        self.original=copy.deepcopy(self.maps)
        self.original.update(runtime_recipe={'original':True},profile_inventory={'original':True},profile={'original':True})
        self.lineage=dict(proposal=self.original,grant=dict(sequence=761),finish=dict(sequence=765,elapsed_seconds=203.775189598))
        self.auth_path=self.root/'approval.json';self.events=[{'private_fixture_event':True}]
        self.refresh()

    def refresh(self):
        self.recovery['map_proposal_sha256']=object_hash(self.maps)
        if self.review_path.exists():self.review_path.unlink()
        write_json(self.review_path,self.review)
        self.approved=dict(schema='plan069-depth-user-authorization/v1',status='DO',review=file_record(self.review_path),
            setup_recovery_approval=dict(candidate='D9',job_id='plan069-D9-setup-recovery-001',status='approved',max_attempts=1,
                proposal_sha256=object_hash(self.recovery)),candidate_approvals=[dict(schema='plan069-depth-execution-approval/v1',
                candidate='D9',status='approved',max_attempts=1,proposal_sha256=object_hash(self.maps))])
        self.save_approval()

    def save_approval(self):
        if self.auth_path.exists():self.auth_path.unlink()
        write_json(self.auth_path,self.approved)

    def select(self,candidate='D9'):
        from vipe_benchmark.depth_authorization import execution_authorization
        with patch('vipe_benchmark.ledger.Ledger.events',return_value=self.events), \
                patch('vipe_benchmark.depth_setup_recovery.original_setup_lineage',return_value=self.lineage) as original:
            result=execution_authorization(candidate,root=self.root,authorization_path=self.auth_path)
        original.assert_called_once_with(self.recovery['original_setup'],self.events,self.root/'run')
        return result

    def test_single_d9_recovery_approval_selected_without_old_runtime_amendment(self):
        self.assertEqual(self.select()[2],self.maps)

    def test_both_fresh_approval_hashes_are_required(self):
        for key in ('setup_recovery_approval','candidate_approvals'):
            prior=copy.deepcopy(self.approved[key]);self.approved[key]=None if key=='setup_recovery_approval' else []
            self.save_approval()
            with self.assertRaises(ValueError):self.select()
            self.approved[key]=prior
        self.approved['setup_recovery_approval']['proposal_sha256']='b'*64;self.save_approval()
        with self.assertRaises(ValueError):self.select()

    def test_d10_cannot_use_d9_recovery_approval(self):
        with self.assertRaisesRegex(ValueError,'D9'):self.select('D10')

    def test_no_changed_science_caps_assets_or_extra_candidates(self):
        for key,value in [('candidate_config',{'changed':True}),('allocation',{'changed':True}),('required_assets',{'changed':True})]:
            with self.subTest(key=key):
                prior=self.maps[key];self.maps[key]=value;self.refresh()
                with self.assertRaises(ValueError):self.select()
                self.maps[key]=prior
        self.review['proposals'].append(dict(self.maps,candidate='D10'));self.refresh()
        with self.assertRaises(ValueError):self.select()

    def test_exact_recovery_duration_and_protected_original_events_required(self):
        for seconds in (1201,True):
            self.recovery['recovery_seconds']=seconds;self.refresh()
            with self.assertRaises(ValueError):self.select()
        self.recovery['recovery_seconds']=1200;self.refresh()
        self.lineage['finish']['sequence']=764
        with self.assertRaises(ValueError):self.select()

    def test_original_lineage_rejection_is_not_bypassed(self):
        from vipe_benchmark.depth_authorization import execution_authorization
        with patch('vipe_benchmark.ledger.Ledger.events',return_value=self.events), \
                patch('vipe_benchmark.depth_setup_recovery.original_setup_lineage',side_effect=ValueError('original changed')):
            with self.assertRaisesRegex(ValueError,'original changed'):
                execution_authorization('D9',root=self.root,authorization_path=self.auth_path)

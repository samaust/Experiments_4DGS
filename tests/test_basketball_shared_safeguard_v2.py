import copy
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from basketball_shared_workflow_v2 import recovery_decision,control_sources
from basketball_audit import sha256
from basketball_scale import read,write


class IdentifiabilityGuardTests(unittest.TestCase):
    def profile(self,identified,qualified):
        return dict(passed=qualified,profiles={'data_only':dict(passed=identified)})

    def test_short_recovery_requires_identifiability_not_motion_label(self):
        result=recovery_decision('direction_changes',25,0.,[.05144,None],True,self.profile(False,False))
        self.assertTrue(result['safeguard_passed'])
        self.assertFalse(result['recovery_required']);self.assertFalse(result['estimator_qualified'])
        result=recovery_decision('direction_changes',25,0.,[.05144,.0],True,self.profile(True,True))
        self.assertFalse(result['safeguard_passed']);self.assertEqual(result['recovery_limit_frames'],.05)

    def test_known_long_positive_must_establish_independent_evidence(self):
        result=recovery_decision('constant_velocity',100,0.,[0.,None],True,self.profile(False,False))
        self.assertFalse(result['safeguard_passed']);self.assertTrue(result['recovery_required'])

    def test_noisy_qualified_cases_must_recover_within_point25(self):
        for qualified in [False,True]:
            result=recovery_decision('acceleration',50,.5,[.251],True,self.profile(qualified,qualified))
            self.assertEqual(result['safeguard_passed'],not qualified)
            self.assertEqual(result['recovery_limit_frames'],.25)
        result=recovery_decision('stationary',100,0.,[0.],True,self.profile(True,True))
        self.assertFalse(result['safeguard_passed'])

    def test_reuse_checks_model_code_recipe_and_control_hashes(self):
        config=read('configs/basketball-rev2/timing-shared-v2.json')
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);archive=root/'archive';archive.mkdir();old=root/'old';old.mkdir()
            shutil.copyfile('scripts/basketball_shared_workflow_v2.py',archive/'basketball_shared_workflow_v2.py')
            control=old/'control.json';write(control,dict(offset=.1))
            write(old/'frozen.json',dict(config=config))
            sources={name:sha256(name) for name in ['scripts/basketball_shared_workflow_v2.py','scripts/basketball_shared_spline_v2.py','scripts/basketball_shared_synthetic_v2.py']}
            write(old/'result.json',dict(stage='safeguard',config_sha256=sha256('configs/basketball-rev2/timing-shared-v2.json'),source_sha256=sources,artifacts_sha256={str(control):sha256(control)}))
            control_sources(old,archive,config)
            control.write_text('{}')
            with self.assertRaises(ValueError):control_sources(old,archive,config)


if __name__=='__main__':unittest.main()

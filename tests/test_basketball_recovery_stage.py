import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from basketball_recovery import search_manifest,POLICIES
import basketball_recovery_stage as stage


class RecoveryStageTests(unittest.TestCase):
    def test_prior_continuation_is_counted_once_without_rerun(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);manifest=search_manifest()
            (root/'search.json').write_text(json.dumps(manifest))
            sources=[root/'early',root/'late']
            for source in sources:source.mkdir();(source/'merged.db').write_bytes(b'database fixture')
            prior=[dict(config=dict(id='B-'+policy,policy=policy),sources=list(map(str,sources)),
                        stability=dict(passed=False,rotation_degrees=[1.],center_fraction_of_diameter=[.02])) for policy in POLICIES]
            (root/'stage-B.json').write_text(json.dumps(prior))
            tested=dict(config=manifest['stages']['C'][1],runs=[],initial_pair=[6,12])
            (root/'continuation.json').write_text(json.dumps(tested))
            def fake_run(workspace,config,sources,pair):return dict(config=config,runs=[],initial_pair=pair)
            with patch.object(sys,'argv',['stage','--workspace',str(root),'--stage','C','--already-tested',str(root/'continuation.json')]), \
                 patch('basketball_initial_pairs.inspect_pairs',return_value=[]), \
                 patch('basketball_initial_pairs.rank_common',return_value=[[2,7],[6,12]]), \
                 patch.object(stage,'run_pair',side_effect=fake_run) as run:
                stage.main()
                self.assertEqual(run.call_count,3)
            results=json.loads((root/'stage-C.json').read_text())
            self.assertEqual(len(results),4)
            self.assertEqual(sum(e['config']==tested['config'] for e in results),1)


if __name__=='__main__':unittest.main()

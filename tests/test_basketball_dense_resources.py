"""Measured checkpoint storage projection and complete native validation gates."""
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import basketball_dense_resources as resources
from basketball_study import digest,write_new


class ResourceTests(unittest.TestCase):
    def test_measured_files_and_one_global_recovery_reservation(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            for arm,size in zip(resources.ARMS,(100,200)):
                write_new(root/f'initializers/{arm}/result.json',dict(total_gaussians=10))
                folder=root/f'validation/{arm}/reload'
                folder.mkdir(parents=True)
                checkpoint=folder/'checkpoint-000003.pt'
                checkpoint.write_bytes(b'x'*size)
                write_new(folder/'worker-result.json',dict(completed=True,iteration=3,
                    checkpoints=[dict(iteration=3,sha256=digest(checkpoint))],peak_allocated_bytes=20,peak_reserved_bytes=30))
                write_new(folder.parent/'save/worker-result.json',dict(completed=True,iteration=2,peak_allocated_bytes=25,peak_reserved_bytes=40))
                write_new(folder/'restore-validation.json',dict(passed=True))
            with patch.object(resources,'ARTIFACTS',root),patch.object(resources,'ROOT',root):
                result=resources.projection()
                self.assertEqual(result['concurrent_recovery_reserve_bytes'],560)
                self.assertEqual([r['retained_checkpoint_projection_bytes'] for r in result['rows']],[3240,5040])
                self.assertEqual(result['rows'][0]['peak_reserved_bytes'],40)
                checkpoint.write_bytes(b'changed')
                with self.assertRaisesRegex(ValueError,'checkpoint changed'):resources.projection()


if __name__=='__main__':unittest.main()

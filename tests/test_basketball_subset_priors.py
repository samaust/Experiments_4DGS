import json
from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from basketball_subset_priors import subset
from basketball_protocol import CAMERAS
from basketball_audit import sha256


class SubsetPriorTests(unittest.TestCase):
    def test_retains_only_current_camera_artifacts_and_refuses_overwrite(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);source=root/'source';source.mkdir();output=root/'subset'
            observations=[];artifacts={}
            for c in (*CAMERAS,19):
                for frame in [50,100]:
                    stem=f'camera{c}-frame{frame}'
                    observations.append(dict(camera_id=c,source_frame_id=frame,stem=stem,K_960x540=[[900,0,480],[0,900,270],[0,0,1]]))
                    for suffix in ['.png','-motion.npy','-static.png']+(['-depth.npz'] if frame==100 else []):
                        name=stem+suffix;(source/name).write_bytes(b'fixture artifact');artifacts[name]=sha256(source/name)
            (source/'result.json').write_text(json.dumps(dict(status='priors-generated',blockers=[],source_frames=[50,100],observations=observations,wall_seconds=1.)))
            (source/'artifacts.json').write_text(json.dumps(artifacts));before=sha256(source/'result.json')
            subset(source,output)
            self.assertEqual(sha256(source/'result.json'),before)
            result=json.loads((output/'result.json').read_text())
            self.assertEqual({e['camera_id'] for e in result['observations']},set(CAMERAS))
            self.assertFalse(list(output.glob('camera19-*')))
            with self.assertRaises(FileExistsError):subset(source,output)
            first=next(iter(artifacts));(source/first).write_bytes(b'changed')
            with self.assertRaisesRegex(ValueError,'changed prior artifact'):subset(source,root/'other')


if __name__=='__main__':unittest.main()

import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

import torch
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from freetimegs_scene import FreeTimeSelfCapScene


class FreeTimeSceneTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        root = Path(self.temporary.name)
        self.image = root / 'frame.png'
        Image.new('RGB', (8, 6), (10, 20, 30)).save(self.image)
        digest = hashlib.sha256(self.image.read_bytes()).hexdigest()
        self.K = [[7., 0., 3.3], [0., 6.5, 2.9], [0., 0., 1.]]
        origin, duration = 4120 / 60 - .023, 1.023
        cameras = []
        for index in range(24):
            cameras.append(dict(id=f'{index:04d}',
                split='test' if index == 15 else 'train', width=8, height=6,
                K=self.K, world_to_camera_R=[[0, 0, 1], [0, 1, 0], [-1, 0, 0]],
                world_to_camera_T=[1., 2., 3.], synchronization_offset_seconds=index * .001,
                frames=[dict(frame_id=f, path='frame.png', sha256=digest,
                    normalized_time=(f/60-index*.001-origin)/duration)
                    for f in range(4120, 4180)]))
        data = dict(schema='selfcap-processed/v1', status='prepared', source_fps=60,
                    time=dict(origin_seconds=origin, duration_seconds=duration), cameras=cameras,
                    sweep=dict(start_camera='0015', normalized_time=.5,
                               poses=[dict(world_to_camera_T=[0., 0., 0.])]))
        path = root / 'manifest.json'
        path.write_text(json.dumps(data))
        self.scene = FreeTimeSelfCapScene(path)

    def test_pose_intrinsics_and_rgb_layout(self):
        camera = self.scene.training_camera(('0000', 4150), device='cpu')
        torch.testing.assert_close(camera.Ks[0], torch.tensor(self.K))
        torch.testing.assert_close(camera.viewmats @ camera.camtoworlds, torch.eye(4)[None])
        local = torch.tensor([.1, .2, 2., 1.])
        world = camera.camtoworlds[0] @ local
        projected = camera.Ks[0] @ (camera.viewmats[0] @ world)[:3]
        torch.testing.assert_close(projected[:2] / projected[2], torch.tensor([3.65, 3.55]))
        self.assertEqual(camera.pixels.shape, (1, 6, 8, 3))
        torch.testing.assert_close(camera.pixels[0, 0, 0], torch.tensor([10., 20., 30.]) / 255)
        self.assertTrue(camera.pixels.is_contiguous())

    def test_split_corrected_times_and_shared_sweep(self):
        self.assertEqual(len(self.scene.training_keys()), 1380)
        a = self.scene.camera(('0000', 4150), device='cpu')
        b = self.scene.camera(('0001', 4150), device='cpu')
        self.assertNotEqual(a.t, b.t)
        self.assertIsNone(a.pixels)
        with self.assertRaisesRegex(ValueError, 'held-out'):
            self.scene.training_camera(('0015', 4150), device='cpu')
        sweep = self.scene.sweep_camera(0, device='cpu')
        self.assertEqual(sweep.t, .5)
        torch.testing.assert_close(sweep.viewmats[0, :3, 3], torch.zeros(3))
        self.assertEqual(sweep.name, 'sweep/00')

    def test_image_integrity_remains_enforced(self):
        Image.new('RGB', (8, 6), (1, 2, 3)).save(self.image)
        with self.assertRaisesRegex(ValueError, 'hash mismatch'):
            self.scene.training_camera(('0000', 4150), device='cpu')

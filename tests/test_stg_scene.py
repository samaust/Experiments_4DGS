import importlib.util
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

import numpy as np
import torch
from PIL import Image

spec = importlib.util.spec_from_file_location('stg_scene',
    Path(__file__).resolve().parents[1]/'scripts/stg_scene.py')
scene = importlib.util.module_from_spec(spec)
spec.loader.exec_module(scene)


class CameraTests(unittest.TestCase):
    def test_manifest_split_times_sweep_and_lazy_image_integrity(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            image = root/'frame.png'
            Image.new('RGB', (80, 60), (10, 20, 30)).save(image)
            digest = hashlib.sha256(image.read_bytes()).hexdigest()
            cameras = []
            origin, duration = 4120/60-.023, 1.023
            for index in range(24):
                c = dict(self.calibration(), id=f'{index:04d}',
                         split='test' if index == 15 else 'train',
                         synchronization_offset_seconds=index*.001)
                c['frames'] = [dict(frame_id=f, path='frame.png', sha256=digest,
                    normalized_time=(f/60-index*.001-origin)/duration) for f in range(4120, 4180)]
                cameras.append(c)
            manifest = dict(schema='selfcap-processed/v1', status='prepared', source_fps=60,
                time=dict(origin_seconds=origin, duration_seconds=duration), cameras=cameras,
                sweep=dict(start_camera='0015', normalized_time=.5,
                           poses=[dict(world_to_camera_R=self.calibration()['world_to_camera_R'],
                                       world_to_camera_T=[0, 0, 0])]))
            path = root/'manifest.json'
            path.write_text(json.dumps(manifest))
            loaded = scene.SelfCapScene(path)
            self.assertEqual(len(loaded.training_keys()), 1380)
            self.assertEqual(len(loaded.training_keys(4150)), 23)
            self.assertNotIn(('0015', 4150), loaded.training_keys())
            a = loaded.camera(('0000', 4150), device='cpu', load_image=True)
            b = loaded.camera(('0001', 4150), device='cpu')
            self.assertNotEqual(a.timestamp, b.timestamp)
            self.assertIsNone(b.original_image)
            self.assertEqual(a.original_image.shape, (3, 60, 80))
            self.assertAlmostEqual(a.original_image[0, 0, 0].item(), 10/255)
            self.assertEqual(loaded.sweep_camera(0, device='cpu').timestamp, .5)
            Image.new('RGB', (80, 60), (1, 2, 3)).save(image)
            with self.assertRaisesRegex(ValueError, 'hash mismatch'):
                loaded.camera(('0000', 4150), device='cpu', load_image=True)

    def calibration(self):
        return dict(width=80, height=60, K=[[70, 0, 33], [0, 65, 30], [0, 0, 1]],
                    world_to_camera_R=[[0, 0, 1], [0, 1, 0], [-1, 0, 0]],
                    world_to_camera_T=[1, 2, 3])

    def test_offcenter_projection_matches_pinhole(self):
        c = self.calibration()
        view = scene.make_camera(c, .234, device='cpu')
        points = np.array([[.1, .2, 2], [-.3, .4, 3], [0, 0, 1]])
        world = (points-np.array(c['world_to_camera_T']))@np.array(c['world_to_camera_R'])
        homogeneous = torch.tensor(np.c_[world, np.ones(3)], dtype=torch.float32)
        clip = homogeneous@view.full_proj_transform
        ndc = (clip[:, :2]/clip[:, 3:]).numpy()
        pixel_indices = ((ndc+1)*[80, 60]-1)/2
        expected = points@np.array(c['K']).T
        expected = expected[:, :2]/expected[:, 2:]-.5
        np.testing.assert_allclose(pixel_indices, expected, atol=2e-5)
        np.testing.assert_allclose(view.camera_center.numpy(),
            -np.array(c['world_to_camera_R']).T@c['world_to_camera_T'])
        self.assertEqual(view.timestamp, .234)

    def test_full_rays_project_to_pixel_centers(self):
        c = self.calibration()
        view = scene.make_camera(c, .5, device='cpu', full=True)
        for y, x in [(0, 0), (29, 39), (59, 79)]:
            direction = view.rayd[0, :, y, x].numpy()
            self.assertAlmostEqual(np.linalg.norm(direction), 1, places=6)
            local = np.array(c['world_to_camera_R'])@direction
            projected = np.array(c['K'])@local
            np.testing.assert_allclose(projected[:2]/projected[2], [x+.5, y+.5], atol=1e-5)
        self.assertEqual(view.rays.shape, (1, 6, 60, 80))

    def test_invalid_camera_rejected(self):
        for timestamp in [-.01, 1, float('nan')]:
            with self.assertRaises(ValueError):
                scene.make_camera(self.calibration(), timestamp, device='cpu')
        c = self.calibration()
        c['K'][0][1] = 2
        with self.assertRaises(ValueError):
            scene.make_camera(c, .5, device='cpu')

"""Run caller entry points with synthetic assets and a deterministic matcher."""
from contextlib import ExitStack, contextmanager
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import numpy as np
from PIL import Image
import torch

from test_triangulation import DEVICE, project
import basketball_temporal_cloud as basketball
from basketball_temporal_geometry import geometry_gate, projection
from freetimegs_initialization import digest, load_dense_cloud
from triangulation import solver_metadata, triangulate_points

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('selfcap_initializer', ROOT/'scripts/initialize-edgs-selfcap.py')
selfcap = importlib.util.module_from_spec(spec)
spec.loader.exec_module(selfcap)


def camera(index):
    return dict(id=str(index), K=[[700., 0, 480.5], [0, 760., 270.5], [0, 0, 1]],
                world_to_camera_R=np.eye(3).tolist(), world_to_camera_T=[-index*.3, 0, 0],
                center=[index*.3, 0, 0])


POINTS = np.array([[.1, .1, 6], [.2, -.1, 7], [.3, .2, 8], [.4, -.2, 9],
                   [.1, .1, -6], [.2, .1, 7], [.3, .1, 8], [.4, .1, 9]])


class Matcher:
    sample_thresh = .5

    def match(self, a, b, device):
        i, j = np.asarray(a)[0, 0, 0], np.asarray(b)[0, 0, 0]
        points = np.concatenate((POINTS, POINTS[:2]))
        u, v = project(points, projection(camera(int(i)))), project(points, projection(camera(int(j))))
        v[7, 1] += 30  # Fails both callers' reprojection checks.
        v[6] = u[6]  # Zero disparity is numerically rank deficient.
        v[5] = np.nan
        warp = np.column_stack((u/[480, 270]-1, v/[480, 270]-1)).reshape(2, 5, 4)
        confidence = torch.ones(10, device=DEVICE)
        confidence[-2:] = torch.tensor([float('nan'), float('inf')], device=DEVICE)
        return torch.tensor(warp, dtype=torch.float32, device=DEVICE), confidence.reshape(2, 5)

    def to_pixel_coordinates(self, matches, ha, wa, hb, wb):
        return ((matches[:, :2]+1)*matches.new_tensor([wa/2, ha/2]),
                (matches[:, 2:]+1)*matches.new_tensor([wb/2, hb/2]))


@contextmanager
def runtime(module):
    # On CPU only redirect explicit device requests at the caller boundary.
    # CUDA runs retain real CUDA tensor movement, synchronization and memory APIs.
    with ExitStack() as stack:
        stack.enter_context(patch.object(module, 'load_roma', return_value=Matcher()))
        if DEVICE == 'cpu':
            stack.enter_context(patch.object(module, 'triangulate_points',
                side_effect=lambda *a, **kw: triangulate_points(*a, **{**kw, 'device': 'cpu'})))
            stack.enter_context(patch.object(torch.Tensor, 'cuda', lambda tensor: tensor))
            for name in ('reset_peak_memory_stats', 'synchronize'):
                stack.enter_context(patch.object(torch.cuda, name))
            for name in ('max_memory_allocated',):
                stack.enter_context(patch.object(torch.cuda, name, return_value=0))
            stack.enter_context(patch.object(torch.cuda, 'get_device_name', return_value='cpu-test'))
        # A runtime attempt to read/stat an EDGS checkout or execute git fails.
        original_open, original_stat = Path.open, Path.stat
        def guarded(original):
            def call(path, *a, **kw):
                if 'EDGS' in path.parts or 'forbidden-edgs' in path.parts:
                    raise AssertionError('EDGS filesystem access')
                return original(path, *a, **kw)
            return call
        stack.enter_context(patch.object(Path, 'open', guarded(original_open)))
        stack.enter_context(patch.object(Path, 'stat', guarded(original_stat)))
        stack.enter_context(patch('subprocess.check_output', side_effect=AssertionError('unexpected source subprocess')))
        stack.enter_context(patch('edgs_source.load_geometry', side_effect=AssertionError('EDGS geometry load')))
        yield


class CallerTests(unittest.TestCase):
    def test_behind_camera_acceptance_and_neighbors(self):
        P = torch.tensor(np.array([projection(camera(i)) for i in (0, 1)]), dtype=torch.float32, device=DEVICE)
        uv = torch.tensor(np.array([project(POINTS, p.cpu().numpy()) for p in P]), dtype=torch.float32, device=DEVICE)
        xyz, valid = triangulate_points(*P, *uv, device=DEVICE)
        self.assertTrue(valid.all())
        good, _ = selfcap.geometry_mask(xyz, valid, *P, *uv, (960, 540), (960, 540))
        self.assertFalse(good[4])
        good, _ = geometry_gate(xyz.cpu().numpy(), uv.cpu().numpy(), P.cpu().numpy(), [[0, 0, 0], [.3, 0, 0]])
        self.assertFalse(good[4])
        vectors = torch.tensor([[0., 0], [1, 0], [-1, 0], [0, 0]], device=DEVICE)
        self.assertEqual(selfcap.nearest_neighbors(vectors).tolist(), [3, 0, 0, 0])

    def test_selfcap_entrypoint_and_legacy_loader(self):
        keys = [(str(i), 12) for i in range(23)]
        cameras = {c: camera(int(c)) for c, _ in keys}
        def view(key, **kwargs):
            transform = torch.eye(4)
            transform[:3, 3] = torch.tensor(cameras[key[0]]['world_to_camera_T'])
            return SimpleNamespace(world_view_transform=transform.T,
                original_image=torch.full((3, 540, 960), int(key[0])/255))
        scene = SimpleNamespace(cameras=cameras, camera=view, training_keys=lambda _: keys,
            sha256='manifest', frames={key: dict(frame_id=12, sha256='image', normalized_time=.1) for key in keys})
        with tempfile.TemporaryDirectory() as temp:
            out = Path(temp)/'cloud'
            args = ['initializer', '--manifest', 'unused', '--edgs', '/forbidden-edgs',
                    '--roma', 'stub', '--weights', 'stub', '--frame-id', '12', '--output', str(out)]
            with runtime(selfcap), patch.object(selfcap, 'SelfCapScene', return_value=scene), patch.object(sys, 'argv', args):
                with self.assertWarnsRegex(FutureWarning, 'deprecated and ignored'):
                    selfcap.main()
            report = json.loads((out/'result.json').read_text())
            self.assertEqual(report['schema'], 'edgs-selfcap-cloud/v2')
            self.assertEqual(report['geometry_source'], solver_metadata())
            self.assertNotIn('edgs_pin', report)
            self.assertEqual(report['numerical_rejections'], 46)
            self.assertEqual(report['points'], 92)
            self.assertEqual(len(load_dense_cloud(out, scene, 12)[0]), 92)
            report['schema'] = 'edgs-selfcap-cloud/v1'
            report.pop('geometry_source')
            report['edgs_pin'] = 'historical'
            (out/'result.json').write_text(json.dumps(report))
            self.assertEqual(len(load_dense_cloud(out, scene, 12)[0]), 92)
            report['archive_sha256'] = 'bad'
            (out/'result.json').write_text(json.dumps(report))
            with self.assertRaisesRegex(ValueError, 'archive digest'):
                load_dense_cloud(out, scene, 12)
            report['archive_sha256'] = digest(out/'cloud.npz')
            report['inputs'][0]['sha256'] = 'bad'
            (out/'result.json').write_text(json.dumps(report))
            with self.assertRaisesRegex(ValueError, 'image digest'):
                load_dense_cloud(out, scene, 12)

    def test_basketball_entrypoint_reports_and_geometry(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            masks = root/'masks'
            masks.mkdir()
            cameras = [camera(i) for i in (1, 2, 3, 4)]
            observations = []
            for c in cameras:
                i = int(c['id'])
                path = root/f'image{i}.png'
                Image.fromarray(np.full((540, 960, 3), i, np.uint8)).save(path)
                c['frames'] = [dict(path=path.name, sha256=digest(path))]*2
                for frame in (0, 1):
                    np.save(masks/f'camera{i}-frame{frame}.npy', np.zeros((540, 960), np.uint8))
                    observations.append(dict(camera_id=i, frame_id=frame, phrases={'0': 'background'}))
                np.save(masks/f'camera{i}-frame0-changing.npy', np.zeros((540, 960), np.uint8))
            manifest = root/'manifest.json'
            manifest.write_text(json.dumps(dict(cameras=cameras, time=dict(duration_seconds=2))))
            (masks/'config.json').write_text(json.dumps(dict(manifest_sha256=digest(manifest), frames=[0])))
            (masks/'result.json').write_text(json.dumps(dict(status='masks-generated', artifacts={},
                config_sha256=digest(masks/'config.json'), observations=observations)))
            neighbors = root/'neighbors.json'
            neighbors.write_text(json.dumps(dict(source_files={}, neighbors={str(i): [j for j in (1, 2, 3, 4) if j != i] for i in (1, 2, 3, 4)})))
            cfg = root/'.local/sync-pivot/runs/freetimegs-zero-seed0/worker/training-config.json'
            cfg.parent.mkdir(parents=True)
            cfg.write_text(json.dumps(dict(normalization=dict(transform=np.eye(4).tolist()))))
            cfg.with_name('checkpoint-provenance.json').write_text(json.dumps(dict(configuration_sha256=digest(cfg))))
            # The caller hashes its existing geometry adapter beneath ROOT.
            (root/'scripts').mkdir()
            (root/'scripts/basketball_temporal_geometry.py').write_bytes((ROOT/'scripts/basketball_temporal_geometry.py').read_bytes())
            out = root/'output'
            args = ['cloud', '--masks', str(masks), '--neighbors', str(neighbors), '--output', str(out)]
            with runtime(basketball), patch.object(basketball, 'ROOT', root), patch.object(basketball, 'MANIFEST', manifest), patch.object(basketball, 'CAMERAS', (1, 2, 3, 4)), patch.object(sys, 'argv', args):
                basketball.main()
            config, report = [json.loads((out/name).read_text()) for name in ('config.json', 'result.json')]
            self.assertEqual(config['schema'], 'basketball-temporal-cloud/v2')
            self.assertEqual(config['geometry_source'], solver_metadata())
            self.assertNotIn('edgs_pin', config)
            self.assertEqual(report['status'], 'geometry-generated-not-accepted')
            self.assertEqual(report['numerical_rejections'], 24)
            self.assertEqual(config['numerical_rejections'], 24)
            self.assertEqual(report['config_sha256'], digest(out/'config.json'))
            self.assertEqual(len(report['records']), 12)
            for record in report['records']:
                self.assertEqual(record['retained'], 4)
                with np.load(out/record['path']) as cloud:
                    self.assertTrue((cloud['world_positions'][:, 2] > 0).all())
                    self.assertTrue(np.isfinite(cloud['positions']).all())
                    self.assertFalse(cloud['velocity_valid'].any())


if __name__ == '__main__':
    unittest.main()

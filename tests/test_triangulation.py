"""Independent NumPy oracle; no EDGS source or execution."""
import os
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

import numpy as np
import torch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from triangulation import triangulate_points

DEVICE = os.environ.get('TRIANGULATION_DEVICE', 'cpu')


def fixture(n=32, dtype=np.float32):
    rng = np.random.default_rng(290)
    xyz = rng.uniform([-1, -.5, 4], [1, .5, 8], (n, 3))
    theta = .12
    R = np.array([[np.cos(theta), 0, np.sin(theta)], [0, 1, 0],
                  [-np.sin(theta), 0, np.cos(theta)]])
    K = np.array([[730., 0, 431.5], [0, 810., 251.5], [0, 0, 1]])
    P = np.array([K @ np.column_stack((R, -R @ c))
                  for c in (np.array([-.6, .1, -.2]), np.array([.8, -.1, .1]))]).astype(dtype)
    uv = np.array([project(xyz, p) for p in P]).astype(dtype)
    return xyz, P, uv


def project(xyz, P):
    q = np.column_stack((xyz, np.ones(len(xyz)))) @ P.T
    return q[:, :2] / q[:, 2:]


def reference(P, uv):
    """Assemble each scalar equation independently in float64."""
    solutions, matrices, targets = [], [], []
    for i in range(uv.shape[1]):
        a, b = [], []
        for view in range(2):
            camera = np.asarray(P[view] if P.ndim == 3 else P[view, i], np.float64)
            for axis in range(2):
                pixel = float(uv[view, i, axis])
                a.append([pixel * camera[2, j] - camera[axis, j] for j in range(3)])
                b.append(camera[axis, 3] - pixel * camera[2, 3])
        a, b = np.array(a), np.array(b)
        solutions.append(np.linalg.lstsq(a, b, rcond=None)[0])
        matrices.append(a)
        targets.append(b)
    return np.array(solutions), np.array(matrices), np.array(targets)


class TriangulationTests(unittest.TestCase):
    def solve(self, P, uv, **kwargs):
        return triangulate_points(P[0], P[1], uv[0], uv[1], device=DEVICE, **kwargs)

    def test_exact_noisy_reference_and_residuals(self):
        for dtype, numpy_dtype, tolerance in ((torch.float32, np.float32, 2e-4),
                                              (torch.float64, np.float64, 1e-10)):
            xyz, P, uv = fixture(dtype=numpy_dtype)
            result, valid = self.solve(P, uv, dtype=dtype)
            self.assertTrue(valid.all())
            np.testing.assert_allclose(result.cpu(), xyz, rtol=tolerance, atol=tolerance)
            uv = (uv + np.random.default_rng(291).normal(0, .3, uv.shape)).astype(numpy_dtype)
            expected, A, b = reference(P, uv)
            result, valid = self.solve(P, uv, dtype=dtype)
            self.assertTrue(valid.all())
            actual = result.cpu().numpy()
            np.testing.assert_allclose(actual, expected, rtol=tolerance, atol=tolerance)
            residual = np.linalg.norm(np.einsum('nij,nj->ni', A, actual)-b, axis=1)
            best = np.linalg.norm(np.einsum('nij,nj->ni', A, expected)-b, axis=1)
            np.testing.assert_allclose(residual, best, rtol=tolerance, atol=tolerance)

    def test_rank_sweep_and_solver_screening(self):
        # Parallel optical axes, decreasing disparity, and a point at infinity.
        P = np.array([np.eye(3, 4), np.eye(3, 4)], dtype=np.float32)
        P[1, 0, 3] = -1
        disparity = np.array([.25, .01, 1e-3, 1e-5, 1e-7, 0], np.float32)
        uv = np.zeros((2, len(disparity), 2), np.float32)
        uv[1, :, 0] = -disparity
        expected, A, b = reference(P, uv)
        singular = np.linalg.svd(A, compute_uv=False)
        eligible = singular[:, -1] > 4*np.finfo(np.float32).eps*singular[:, 0]
        original = torch.linalg.lstsq
        def screened(a, b, **kwargs):
            self.assertEqual(len(a), int(eligible.sum()))
            self.assertEqual(kwargs, {'driver': 'gels'})
            return original(a, b, **kwargs)
        with patch('torch.linalg.lstsq', side_effect=screened) as solve:
            result, valid = self.solve(P, uv)
            solve.assert_called_once()
        np.testing.assert_array_equal(valid.cpu(), eligible)
        residual = np.linalg.norm(np.einsum('nij,nj->ni', A[eligible], result.cpu().numpy()[eligible])-b[eligible], axis=1)
        self.assertLess(residual.max(), 2e-4)
        self.assertTrue(torch.isnan(result[~valid]).all())
        with patch('torch.linalg.lstsq', side_effect=AssertionError('rejected input reached solver')):
            _, valid = self.solve(np.array([P[0], P[0]]), uv*0)
            self.assertFalse(valid.any())
            _, valid = self.solve(P, uv, rank_rtol=.9)
            self.assertFalse(valid.any())

    def test_invalid_mixed_overflow_and_empty(self):
        xyz, P, uv = fixture(6)
        uv[0, 1, 0] = np.nan
        uv[1, 3, 1] = np.inf
        result, valid = self.solve(P, uv)
        np.testing.assert_array_equal(valid.cpu(), [True, False, True, False, True, True])
        np.testing.assert_allclose(result.cpu().numpy()[[0, 2, 4, 5]], xyz[[0, 2, 4, 5]], atol=2e-4)
        with patch('torch.linalg.lstsq', side_effect=AssertionError('all invalid')):
            result, valid = self.solve(P, np.full_like(uv, np.nan))
            self.assertTrue(torch.isnan(result).all())
            self.assertFalse(valid.any())
            # Finite cameras and coordinates may still overflow equation assembly.
            huge = np.full((2, 3, 4), np.finfo(np.float32).max, np.float32)
            _, valid = self.solve(huge, np.full_like(uv, 4))
            self.assertFalse(valid.any())
            result, valid = self.solve(P, uv[:, :0])
            self.assertEqual(result.shape, (0, 3))
            self.assertEqual(valid.shape, (0,))
        self.assertEqual(result.device.type, DEVICE.split(':')[0])
        self.assertEqual(valid.dtype, torch.bool)

    def test_validation_errors(self):
        _, P, uv = fixture()
        for threshold in (0, -1, 1, float('nan'), float('inf')):
            with self.assertRaisesRegex(ValueError, 'rank_rtol'):
                self.solve(P, uv, rank_rtol=threshold)
        with self.assertRaisesRegex(ValueError, 'dtype'):
            self.solve(P, uv, dtype=torch.float16)
        for bad in (np.zeros((2, 4, 3)), np.zeros((2, 2, 3, 4))):
            with self.assertRaisesRegex(ValueError, 'P1'):
                self.solve(bad, uv)
        with self.assertRaisesRegex(ValueError, 'matching'):
            triangulate_points(*P, uv[0], uv[1, :2], device=DEVICE)
        with self.assertRaisesRegex(ValueError, 'matching'):
            self.solve(P, np.zeros((2, 3)))
        P[0, 0, 0] = np.nan
        with self.assertRaisesRegex(ValueError, 'non-finite camera'):
            self.solve(P, uv)
        with patch('torch.cuda.is_available', return_value=False):
            with self.assertRaisesRegex(RuntimeError, 'unavailable'):
                triangulate_points(*P, *uv, device='cuda')

    def test_tensor_contract_per_point_order_detach(self):
        xyz, P, uv = fixture()
        cameras = torch.tensor(np.repeat(P[:, None], len(xyz), axis=1), requires_grad=True)
        storage = torch.zeros((2, len(xyz), 4), requires_grad=True)
        with torch.no_grad():
            storage[:, :, ::2] = torch.tensor(uv)
        pixels = storage[:, :, ::2]
        before = storage.detach().clone()
        before_cameras = cameras.detach().clone()
        result, valid = self.solve(cameras, pixels)
        self.assertFalse(result.requires_grad)
        self.assertIsNone(result.grad_fn)
        self.assertTrue(valid.all())
        torch.testing.assert_close(before, storage.detach())
        torch.testing.assert_close(before_cameras, cameras.detach())
        np.testing.assert_allclose(result.cpu(), xyz, atol=2e-4, rtol=2e-4)
        # Distinct per-point projections, not just broadcast copies.
        varied = cameras.detach().numpy().copy()
        varied[1, :, 0, 3] += np.linspace(0, 10, len(xyz))
        varied_uv = np.array([[project(xyz[i:i+1], p)[0] for i, p in enumerate(view)] for view in varied])
        result, valid = self.solve(varied, varied_uv)
        self.assertTrue(valid.all())
        np.testing.assert_allclose(result.cpu(), xyz, atol=2e-4, rtol=2e-4)

    def test_execution_failures_and_nonfinite_solutions(self):
        _, P, uv = fixture()
        for method in ('svdvals', 'lstsq'):
            with patch('torch.linalg.'+method, side_effect=RuntimeError('execution failure')):
                with self.assertRaisesRegex(RuntimeError, 'execution failure'):
                    self.solve(P, uv)
        from types import SimpleNamespace
        with patch('torch.linalg.lstsq', return_value=SimpleNamespace(
                solution=torch.full((32, 3, 1), float('inf'), device=DEVICE))):
            result, valid = self.solve(P, uv)
            self.assertFalse(valid.any())
            self.assertTrue(torch.isnan(result).all())


if __name__ == '__main__':
    unittest.main()

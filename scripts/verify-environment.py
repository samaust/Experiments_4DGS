"""Verify the chosen ABI, with optional GPU and PyTorch3D kernel checks."""
import argparse
import importlib
import sys
import sysconfig

METHOD_IMPORTS = {
    'freetimegs': ('numpy', 'scipy', 'sklearn', 'cv2', 'PIL', 'plyfile', 'tqdm',
                   'matplotlib', 'imageio', 'imageio_ffmpeg', 'tyro', 'yaml',
                   'tensorboard', 'torchmetrics'),
    'atgs': ('numpy', 'scipy', 'skimage', 'cv2', 'PIL', 'plyfile', 'tqdm', 'matplotlib',
             'colorama', 'einops', 'lpips', 'laspy', 'torchmetrics', 'jaxtyping',
             'pytorch_msssim', 'imageio', 'imageio_ffmpeg', 'tensorboard', 'mmengine', 'wandb'),
    'stg-render': ('numpy', 'scipy', 'skimage', 'cv2', 'PIL', 'plyfile', 'kornia', 'natsort', 'tqdm', 'yapf'),
    'stg-colmap': ('numpy', 'cv2', 'tqdm', 'natsort', 'PIL'),
    'hust': ('numpy', 'scipy', 'skimage', 'cv2', 'PIL', 'plyfile', 'tqdm', 'imageio', 'imageio_ffmpeg', 'matplotlib', 'lpips', 'tensorboard'),
    'mango-render': ('numpy', 'scipy', 'skimage', 'cv2', 'PIL', 'yaml', 'tensorboard', 'tqdm', 'imageio', 'imageio_ffmpeg', 'plyfile', 'piq', 'lpips', 'pytorch_msssim', 'matplotlib'),
    'nopo4d': ('numpy', 'einops', 'huggingface_hub', 'jaxtyping', 'gsplat', 'xformers'),
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--gpu', action='store_true', help='Require CUDA and test a synchronized tensor operation')
    parser.add_argument('--method', choices=METHOD_IMPORTS, help='Import the method candidate dependencies (excludes deferred sources)')
    parser.add_argument('--pytorch3d', action='store_true', help='Also test PyTorch3D KNN and point rasterization; requires --gpu')
    args = parser.parse_args()
    if args.pytorch3d and not args.gpu:
        parser.error('--pytorch3d requires --gpu')
    import torch
    import torchvision

    print(sys.executable, sys.version, flush=True)
    print('Torch:', torch.__version__, 'torchvision:', torchvision.__version__, 'CUDA runtime:', torch.version.cuda, flush=True)
    assert sys.version_info[:2] == (3, 14), 'Python 3.14 required'
    assert not sysconfig.get_config_var('Py_GIL_DISABLED'), 'Use standard GIL Python'
    assert torch.__version__ == '2.13.0+cu130', 'Unexpected Torch ABI'
    assert torchvision.__version__ == '0.28.0+cu130', 'Unexpected torchvision ABI'
    assert torch.version.cuda == '13.0', 'Unexpected CUDA runtime'
    print('PASS: base versions and imports', flush=True)
    if args.method:
        for module in METHOD_IMPORTS[args.method]:
            importlib.import_module(module)
        print('PASS: candidate imports for', args.method, flush=True)
    if args.gpu:
        if not torch.cuda.is_available():
            raise RuntimeError('CUDA unavailable in this process. Check NVIDIA device access in an authorized host terminal.')
        print(torch.cuda.get_device_name(0), torch.cuda.get_device_capability(0), flush=True)
        x = torch.ones((32, 32), device='cuda')
        y = x @ x
        torch.cuda.synchronize()
        assert y[0, 0].item() == 32
        print('PASS: synchronized CUDA tensor operation', flush=True)
    if args.pytorch3d:
        import pytorch3d
        from pytorch3d import _C
        from pytorch3d.ops import knn_points
        from pytorch3d.renderer.points import rasterize_points
        from pytorch3d.structures import Pointclouds

        print('PyTorch3D:', pytorch3d.__version__, _C.__file__, flush=True)
        assert hasattr(_C, 'knn_check_version'), 'This pinned PyTorch3D extension was built without CUDA'
        p = torch.tensor([[[0., 0., 1.], [.5, 0., 1.]]], device='cuda', requires_grad=True)
        q = p.detach() + torch.tensor([0., .25, 0.], device='cuda')
        result = knn_points(p, q, K=1)
        assert torch.equal(result.idx, torch.tensor([[[0], [1]]], device='cuda'))
        assert torch.allclose(result.dists, torch.full_like(result.dists, .0625))
        result.dists.sum().backward()
        expected_grad = torch.tensor([[[0., -.5, 0.], [0., -.5, 0.]]], device='cuda')
        assert p.grad is not None and torch.allclose(p.grad, expected_grad)
        indices, _, _ = rasterize_points(Pointclouds(points=p.detach()), image_size=16, radius=.2, points_per_pixel=2)
        torch.cuda.synchronize()
        assert (indices >= 0).any(), 'No points rasterized'
        print('PASS: CUDA KNN forward/backward and point rasterization', flush=True)


if __name__ == '__main__':
    main()

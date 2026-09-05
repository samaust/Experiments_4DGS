"""Exercise the patched inference imports, NumPy preprocessing, and attention.

Run with .local/envs/nopo4d/bin/python. No weights or GPU are required.
"""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault("MPLCONFIGDIR", str(ROOT / ".local/cache/matplotlib"))

import numpy as np
import torch
from PIL import Image
from depth_anything_3.api import DepthAnything3
from depth_anything_3.model.dinov2.layers.attention import Attention
from depth_anything_3.utils.geometry import affine_inverse_np
from depth_anything_3.utils.io.input_processor import InputProcessor
from src.model.nopo4d import NoPo4D


def main():
    paths = sorted((ROOT / ".local/NoPo4D/assets/examples").glob("*.png"))
    assert len(paths) == 16, f"Expected 16 example images, got {len(paths)}"
    images = [np.asarray(Image.open(path).convert("RGB")) for path in paths[:2]]
    batch, _, _ = InputProcessor()(images, process_res=56, sequential=True)
    assert batch.shape[0] == 2 and batch.shape[1] == 3, batch.shape
    assert torch.isfinite(batch).all()
    assert all(d % 14 == 0 for d in batch.shape[-2:])

    transform = np.eye(4, dtype=np.float32)[None]
    transform[0, :3, 3] = [1, 2, 3]
    np.testing.assert_allclose(transform @ affine_inverse_np(transform), np.eye(4)[None])

    torch.manual_seed(0)
    attention = Attention(dim=32, num_heads=4).eval()
    inputs = torch.randn(2, 8, 32, requires_grad=True)
    output = attention(inputs)
    assert output.shape == inputs.shape and torch.isfinite(output).all()
    output.square().mean().backward()
    assert inputs.grad is not None and torch.isfinite(inputs.grad).all()
    print(f"PASS: {NoPo4D.__name__}/{DepthAnything3.__name__} imports, "
          f"NumPy {np.__version__} preprocessing/geometry, attention forward/backward")


if __name__ == "__main__":
    main()

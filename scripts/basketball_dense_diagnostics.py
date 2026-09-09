"""Training-view diagnostics at the fixed Plan 026 pilot cameras and times."""
import argparse
import importlib.util
import json
from pathlib import Path
import time

from basketball_study import MANIFEST, PILOT, ROOT, digest, write_new
from basketball_dense_training import ARMS


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--arm', choices=ARMS, required=True)
    source = p.add_mutually_exclusive_group(required=True)
    source.add_argument('--initializer', type=Path)
    source.add_argument('--checkpoint', type=Path)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    import numpy as np
    import torch
    from PIL import Image
    started = time.monotonic()
    torch.manual_seed(0)
    a.checkout = ROOT/'.local/FreeTimeGsVanilla'
    a.manifest, a.method = MANIFEST, 'freetimegs'
    if a.checkpoint:
        state = torch.load(a.checkpoint, map_location='cpu', weights_only=True)
        if state['provenance'].get('arm') != a.arm:
            raise ValueError('diagnostic recipe mismatch')
        spec = importlib.util.spec_from_file_location('frozen_renderer', ROOT/'scripts/evaluate-basketball-sync.py')
        renderer = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(renderer)
        scene, model, iteration, pixels = renderer.load_model(a)
        source_hash = digest(a.checkpoint)
        seed = state['provenance']['seed']
    else:
        from basketball_dense_fusion import load_frozen, NATIVE
        from basketball_native_train import prepare_free
        from basketball_scene import FreeTimeBasketballScene
        from freetimegs_model import NativeFreeTimeModel
        from freetimegs_training import load_training
        scene, _, norm = prepare_free(FreeTimeBasketballScene(MANIFEST), ROOT/'.local/sync-pivot/basketball-static-init', a.checkout)
        arrays, frozen = load_frozen(a.initializer, a.arm, norm)
        cfg, _, _ = load_training(a.checkout)
        cfg.start_frame, cfg.end_frame = 0, 50
        model = NativeFreeTimeModel(a.checkout, cfg, {k: torch.from_numpy(arrays[k]) for k in NATIVE}, scene_scale=norm['scene_scale'], device='cuda')
        del arrays
        iteration, source_hash = 0, frozen['archive_sha256']
        seed = 0
        def pixels(key):
            return model.render(scene.camera(key, device='cuda'), sh_degree=0)[0][0].permute(2,0,1)
    a.output.mkdir(parents=True, exist_ok=False)
    rows = []
    with torch.no_grad():
        for camera in (1, 11, 21, 31):
            for frame in PILOT:
                raw = pixels((str(camera), frame)).permute(1,2,0).cpu().numpy()
                if raw.shape != (540,960,3) or not np.isfinite(raw).all():
                    raise ValueError('invalid diagnostic render')
                path = a.output/f'camera{camera}-frame{frame}.png'
                Image.fromarray((np.clip(raw,0,1)*255).round().astype(np.uint8)).save(path)
                rows.append(dict(camera=camera,frame=frame,path=path.name,sha256=digest(path)))
    write_new(a.output/'result.json',dict(arm=a.arm,seed=seed,iteration=iteration,source_sha256=source_hash,
        scope='training-view diagnostics; not held-out quality evidence', records=rows,
        wall_seconds=time.monotonic()-started,peak_allocated_bytes=torch.cuda.max_memory_allocated()))


if __name__ == '__main__':
    main()

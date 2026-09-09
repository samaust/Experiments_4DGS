"""Native foreground-only untrained renders for Plan 026 pilot inspection."""
import argparse
import json
from pathlib import Path
import time

import numpy as np
from PIL import Image
import torch

from basketball_study import MANIFEST, PILOT, ROOT, digest, write_new
from basketball_scene import FreeTimeBasketballScene
from freetimegs_model import NativeFreeTimeModel
from freetimegs_normalization import load_normalization, normalize_camera
from freetimegs_training import load_training


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--cloud', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    a.output.mkdir(parents=True, exist_ok=False)
    result = json.loads((a.cloud / 'result.json').read_text())
    normalization = json.loads((a.cloud / 'config.json').read_text())['normalization']
    transform = np.array(normalization['transform'])
    checkout = ROOT / '.local/FreeTimeGsVanilla'
    helper, source = load_normalization(checkout)
    cfg, _, _ = load_training(checkout)
    cfg.start_frame, cfg.end_frame = 0, 50
    scene = FreeTimeBasketballScene(MANIFEST)
    records = []
    started = time.monotonic()
    for frame in PILOT:
        arrays = []
        for r in result['records']:
            if r['frame'] == frame and 'path' in r:
                if digest(a.cloud / r['path']) != r['sha256']:
                    raise ValueError('cloud changed')
                arrays.append(dict(np.load(a.cloud / r['path'], allow_pickle=False)))
        data = {k: torch.from_numpy(np.concatenate([x[k][x['region'] == 1] for x in arrays]).copy())
                for k in ('positions', 'colors', 'velocities', 'times', 'durations')}
        if len(data['positions']) < 4:
            raise ValueError('insufficient foreground geometry for native rendering')
        torch.manual_seed(0)
        model = NativeFreeTimeModel(checkout, cfg, data, scene_scale=normalization['scene_scale'], device='cuda')
        with torch.no_grad():
            for c in (1, 11, 21, 31):
                camera = normalize_camera(scene.training_camera((str(c), frame), device='cuda', load_image=False),
                                          transform, helper['transform_cameras'])
                rgb, alpha, _ = model.render(camera, sh_degree=0)
                if not torch.isfinite(rgb).all() or not torch.isfinite(alpha).all():
                    raise ValueError('nonfinite foreground render')
                path = a.output / f'camera{c}-frame{frame}.png'
                Image.fromarray((rgb[0].clamp(0, 1)*255).round().byte().cpu().numpy()).save(path)
                np.save(a.output / f'camera{c}-frame{frame}.npy', rgb[0].cpu().numpy())
                records.append(dict(camera=c, frame=frame, points=len(data['positions']),
                                    sha256=digest(path), mean_alpha=float(alpha.mean())))
        del model, data
        torch.cuda.empty_cache()
    write_new(a.output / 'result.json', dict(status='rendered-not-accepted', records=records,
        scope='foreground-only native initialization renders at each pilot time; no optimization',
        cloud_sha256=digest(a.cloud / 'result.json'), normalization_source=source,
        wall_seconds=time.monotonic()-started, peak_allocated_bytes=torch.cuda.max_memory_allocated()))


if __name__ == '__main__':
    main()

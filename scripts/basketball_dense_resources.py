"""Project Plan 027 retention from full-initializer native save/reload evidence."""
import argparse
import json
from pathlib import Path
import shutil

from basketball_dense_training import ARTIFACTS, ARMS
from basketball_study import ROOT, digest, write_new


def projection():
    rows = []
    for arm in ARMS:
        initial = ARTIFACTS/f'initializers/{arm}'
        frozen = json.loads((initial/'result.json').read_text())
        folder = ARTIFACTS/f'validation/{arm}/reload'
        result = json.loads((folder/'worker-result.json').read_text())
        restored = json.loads((folder/'restore-validation.json').read_text())
        first = json.loads((folder.parent/'save/worker-result.json').read_text())
        if (not result['completed'] or result['iteration'] != 3 or not restored['passed']
                or not first['completed'] or first['iteration'] != 2):
            raise ValueError('full initializer save/reload validation incomplete')
        checkpoint = folder/'checkpoint-000003.pt'
        row = next(c for c in result['checkpoints'] if c['iteration'] == 3)
        if digest(checkpoint) != row['sha256']:
            raise ValueError('validation checkpoint changed')
        # Five retained curves and the restored 5000 parent for each seed.
        # Recovery generations are reserved globally because jobs are serial.
        # Ordinary native FreeTimeGS relocates but does not grow.
        rows.append(dict(arm=arm, points=frozen['total_gaussians'], checkpoint_bytes=checkpoint.stat().st_size,
            mature_checkpoint_projection_bytes=checkpoint.stat().st_size + frozen['total_gaussians']*8,
            additional_strategy_state_reserve_bytes=frozen['total_gaussians']*8,
            retained_checkpoint_projection_bytes=(checkpoint.stat().st_size + frozen['total_gaussians']*8)*6*3,
            peak_allocated_bytes=max(result['peak_allocated_bytes'], first['peak_allocated_bytes']),
            peak_reserved_bytes=max(result['peak_reserved_bytes'], first['peak_reserved_bytes']),
            restoration_sha256=digest(folder/'restore-validation.json')))
    png = 30*(350+13)*960*540*3
    visuals = 24*50*960*540*3*5  # Conservative uncompressed budget for all endpoint videos.
    reserve = 1024**3
    recovery = 2*max(r['mature_checkpoint_projection_bytes'] for r in rows)
    projected = sum(r['retained_checkpoint_projection_bytes'] for r in rows)+recovery+png+visuals+reserve
    return dict(schema='basketball-dense-training-resources/v1', rows=rows,
        projected_png_bytes=png, projected_visual_bytes=visuals, reserve_bytes=reserve,
        concurrent_recovery_reserve_bytes=recovery, gpu_job_concurrency=1,
        projected_total_bytes=projected, free_bytes=shutil.disk_usage(ROOT).free,
        fits=projected <= shutil.disk_usage(ROOT).free,
        point_count_policy='native fixed count; no pruning, growth, downsampling, or equalization',
        memory_projection='short-run peaks below; reserve two additional float32 strategy vectors per point for later updates; visibility-dependent renderer peaks remain monitored during production',
        scope='remaining production retention; full initialization and validation already resident')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    result = projection()
    write_new(a.output, result)
    if not result['fits']:
        raise SystemExit('storage pause: full measured retention projection exceeds available disk space')


if __name__ == '__main__':
    main()

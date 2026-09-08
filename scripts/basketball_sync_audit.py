"""Freeze Plan 024 calibration and audit source timing metadata without final images."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess


def digest(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def select_cameras(visible, count=8, reference=1, heldout=(0, 10, 20, 30)):
    """Greedily add new shared map tracks; ties use physical camera ID."""
    eligible = set(visible) - set(heldout)
    if reference not in eligible or count > len(eligible):
        raise ValueError('insufficient eligible cameras')
    selected, steps, covered = [reference], [], set()
    while len(selected) < count:
        seen = set().union(*(visible[c] for c in selected))
        scores = []
        for c in sorted(eligible - set(selected)):
            shared = visible[c] & seen
            if shared:
                scores.append((len(shared - covered), c, shared))
        if not scores:
            raise ValueError('overlap does not connect enough training cameras')
        gain, c, shared = min(scores, key=lambda row: (-row[0], row[1]))
        selected.append(c)
        covered |= shared
        steps.append(dict(camera_id=c, new_shared_tracks=gain, shared_tracks=len(shared)))
    return selected, steps


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    import pycolmap
    root = Path(__file__).resolve().parents[1]
    calib_path = root/'docs/experiments/basketball-calibration-alternatives/calibration.json'
    scale_path = root/'docs/experiments/basketball-rev2/scale-fit.json'
    winner_path = root/'docs/experiments/basketball-calibration-alternatives/frozen-winner.json'
    calib, scale, winner = [json.loads(p.read_text()) for p in (calib_path, scale_path, winner_path)]
    sha = digest(calib_path)
    if sha != winner['calibration_sha256'] or sha != scale['calibration_sha256']:
        raise ValueError('accepted calibration/scale provenance mismatch')
    if scale['status'] != 'passed' or sorted(c['camera_id'] for c in calib['cameras']) != list(range(34)):
        raise ValueError('invalid frozen rig')
    paths = winner['frozen_artifact_sha256']
    model_path = root/next(k for k in paths if k.endswith('/points3D.bin'))
    for name in ('points3D.bin', 'images.bin', 'cameras.bin'):
        path = model_path.with_name(name)
        if digest(path) != paths[str(path.relative_to(root))]:
            raise ValueError('frozen map changed')
    model = pycolmap.Reconstruction(str(model_path.parent))
    visible = {c: set() for c in range(34) if c not in (0, 10, 20, 30)}
    for pid, point in model.points3D.items():
        ids = {int(Path(model.images[e.image_id].name).stem.removeprefix('camera'))
               for e in point.track.elements}
        if not ids <= set(visible):
            raise ValueError('held-out or unknown map camera')
        if len(ids) >= 2:
            for c in ids:
                visible[c].add(pid)
    selected, selection = select_cameras(visible)
    sources = []
    for c in range(34):
        path = root/f'.local/data/vru-basketball/Basketball_dg/{c}.mp4'
        command = ['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_frames',
                   '-show_streams', '-show_entries',
                   'stream=width,height,r_frame_rate,avg_frame_rate,time_base:frame=best_effort_timestamp_time',
                   '-of', 'json', str(path)]
        data = json.loads(subprocess.check_output(command, timeout=60))
        stamps = [float(f['best_effort_timestamp_time']) for f in data['frames']]
        intervals = [b-a for a,b in zip(stamps, stamps[1:])]
        if len(stamps) != 250 or any(abs(t-i/25) > 1e-7 for i,t in enumerate(stamps)):
            raise ValueError(f'camera {c} cadence differs from planned 25 fps source')
        sources.append(dict(camera_id=c, path=str(path.relative_to(root)), sha256=digest(path),
                            streams=data['streams'], frame_count=len(stamps),
                            first_timestamp=stamps[0], last_timestamp=stamps[-1],
                            minimum_interval=min(intervals), maximum_interval=max(intervals),
                            duplicate_timestamps=sum(x == 0 for x in intervals)))
    result = dict(schema='basketball-sync-freeze/v1', calibration_sha256=sha,
                  calibration_path=str(calib_path.relative_to(root)), scale=scale['scale'],
                  scale_sha256=digest(scale_path), scale_path=str(scale_path.relative_to(root)),
                  scale_uncertainty=scale['uncertainty_limitation'], camera_ids=list(range(34)),
                  reference_camera=1, heldout_camera_ids=[0,10,20,30],
                  fit_frames=[50,149], development_frames=[150,199], final_frames=[200,249],
                  reconstruction_frames=[0,49], reserved_seconds=[0.8,1.0],
                  map_path=str(model_path.parent.relative_to(root)),
                  syncnerf_camera_ids=selected, selection_steps=selection,
                  overlap_tracks_per_camera={c:len(v) for c,v in visible.items()}, sources=sources,
                  cadence_conclusion='Container PTS is regular; physical exposure phase, duplicated pixel content and clock drift are not established by PTS.',
                  final_images_opened=False, script_sha256=digest(__file__))
    a.output.parent.mkdir(parents=True, exist_ok=True)
    with a.output.open('x') as stream:
        json.dump(result, stream, indent=2, allow_nan=False)
        stream.write('\n')
    print(json.dumps(dict(cameras=34, syncnerf_camera_ids=selected, calibration_sha256=sha)))


if __name__ == '__main__':
    main()

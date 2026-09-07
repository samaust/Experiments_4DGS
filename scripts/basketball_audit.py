"""Plan 005 input audit. Decode all videos, but expose no images to fitting."""
import argparse
from fractions import Fraction
import hashlib
import json
from pathlib import Path
import subprocess
import time

PIN = 'de50e6ab1066e32c96d32499a282ecaa2fbf2d90'
HELD_OUT = [0, 10, 20, 30]


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def frame_roles():
    return {'schema': 'basketball-frame-roles/v1',
            'training_cameras': [i for i in range(34) if i not in HELD_OUT],
            'held_out_cameras': HELD_OUT,
            'experiment': list(range(50)), 'fit': list(range(50, 150)),
            'selection': list(range(150, 200)), 'validation': list(range(200, 250)),
            'pilot_cameras': [4, 12, 21, 29],
            'stream_to_source_frame': list(range(50, 150)),
            'calibration_gpu_limit_seconds': 28800}


def validate_probe(probe):
    streams = probe['streams']
    if len(streams) != 1:
        raise ValueError('expected one video stream')
    stream = streams[0]
    frames = probe['frames']
    if len(frames) != 250 or int(stream['nb_read_frames']) != 250:
        raise ValueError('missing frames or unexpected decoded coverage (expected 250)')
    if (stream['width'], stream['height']) != (1920, 1080):
        raise ValueError('unexpected image dimensions')
    if any(Fraction(stream[key]) != 25 for key in ('r_frame_rate', 'avg_frame_rate')):
        raise ValueError('unexpected or variable frame rate')
    timestamps = [Fraction(f['best_effort_timestamp_time']) for f in frames]
    if any(abs(b-a-Fraction(1, 25)) > Fraction(1, 1000000)
           for a, b in zip(timestamps, timestamps[1:])):
        raise ValueError('missing frames or unresolved variable timestamps')
    if any((f['width'], f['height']) != (1920, 1080) for f in frames):
        raise ValueError('dimensions change during decoding')
    return [float(t) for t in timestamps]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--videos', type=Path, required=True)
    parser.add_argument('--vipe', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    roles = args.output / 'frame-roles.json'
    value = json.dumps(frame_roles(), indent=2) + '\n'
    if roles.exists() and roles.read_text() != value:
        raise ValueError('frame-role provenance changed')
    roles.write_text(value)
    result = {'schema': 'basketball-input-audit/v1', 'status': 'blocked',
              'estimated_calibration': True, 'videos': [], 'blockers': [],
              'frame_roles_sha256': sha256(roles)}
    started = time.monotonic()
    git = lambda *a: subprocess.check_output(['git', '-C', str(args.vipe), *a], text=True).strip()
    result['vipe'] = {'path': str(args.vipe.resolve()), 'revision': git('rev-parse', 'HEAD'),
                      'branch': git('branch', '--show-current'), 'status': git('status', '--porcelain')}
    if result['vipe']['revision'] != PIN or result['vipe']['branch'] != 'tridi' or result['vipe']['status']:
        result['blockers'].append('ViPE pin, branch or clean-tree gate failed')
    paths = sorted(args.videos.glob('*.mp4'), key=lambda p: p.name)
    if {p.name for p in paths} != {f'{i}.mp4' for i in range(34)}:
        result['blockers'].append('camera filename inventory differs from 0–33')
    for path in paths:
        entry = {'camera_id': path.stem, 'path': str(path.resolve()), 'sha256': sha256(path)}
        command = ['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-count_frames',
                   '-show_frames', '-show_streams', '-show_entries',
                   'stream=width,height,r_frame_rate,avg_frame_rate,nb_frames,nb_read_frames,time_base,start_time:frame=best_effort_timestamp_time,width,height',
                   '-of', 'json', str(path)]
        process = subprocess.run(command, capture_output=True, text=True, check=True)
        probe = json.loads(process.stdout)
        entry['stream'] = probe['streams']
        entry['decode_errors'] = process.stderr
        try:
            entry['timestamps_seconds'] = validate_probe(probe)
            if process.stderr:
                raise ValueError('decoder reported errors')
        except (ValueError, KeyError) as error:
            result['blockers'].append(f'{path.name}: {error}')
        result['videos'].append(entry)
        print(f'audited {path.name}', flush=True)
    result['wall_seconds'] = time.monotonic() - started
    result['status'] = 'blocked' if result['blockers'] else 'inputs-verified'
    result['limitations'] = ['Filename IDs verified; physical camera identity requires geometry.',
                            'Uniform timestamps do not establish inter-camera synchronization.']
    (args.output / 'input-audit.json').write_text(json.dumps(result, indent=2) + '\n')
    return bool(result['blockers'])


if __name__ == '__main__':
    raise SystemExit(main())

"""Read-only provenance gate for Plan 005 rev2; never evaluates static images."""
import argparse
import json
from pathlib import Path
import subprocess
import time

from basketball_audit import PIN, sha256, validate_probe

CALIBRATION = Path('docs/experiments/basketball-calibration-alternatives/calibration.json')
PROFILE = Path('configs/scene-manifest.vru-basketball-dg.full-rig.json')
CALIBRATION_SHA = '21139df550a6fa72c9730d4c658a58464ce00be9ff268380ab433c3d9471e74f'
PROFILE_SHA = 'c19598363821b41ea3e143a9175595a2fb7ed56f952a4f6844a01c8bdaa4de82'
WORKSPACE = Path('.local/calibration/basketball-alternatives')
AUDIT = Path('.local/calibration/basketball-v1/input-audit.json')
TRAINING = tuple(c for c in range(34) if c not in (0, 10, 20, 30))


def verify_hashes(expected):
    for name, digest in expected.items():
        if 'prompts' in Path(name).parts:
            raise ValueError('forbidden provenance path')
        if sha256(name) != digest:
            raise ValueError(f'changed provenance: {name}')


def verify_membership(profile, calibration):
    cameras = profile['cameras']
    if len(cameras) != 34 or {int(c['id']) for c in cameras} != set(range(34)):
        raise ValueError('incomplete/duplicate camera IDs')
    for camera in cameras:
        expected = 'training' if int(camera['id']) in TRAINING else 'held-out'
        if camera['role'] != expected:
            raise ValueError('camera split changed')
    if len(calibration['cameras']) != 34 or {c['camera_id'] for c in calibration['cameras']} != set(range(34)):
        raise ValueError('calibration camera IDs changed')
    if profile['frames']['start'] != 0 or profile['frames']['end'] != 50:
        raise ValueError('downstream frame range changed')
    for key, value in [('expected_images', 1700), ('expected_training_images', 1500),
                       ('expected_held_out_images', 200), ('excluded_cameras', [])]:
        if profile['variant'][key] != value:
            raise ValueError('full-rig image counts changed')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    a.output.mkdir(parents=True, exist_ok=False)
    started = time.monotonic()
    result = dict(schema='basketball-continuation-audit/v1', status='blocked',
                  blockers=[], videos=[], sha256={}, adapter_sha256=sha256(__file__))
    try:
        frozen = json.loads((WORKSPACE/'frozen-winner.json').read_text())
        marker = json.loads((WORKSPACE/'validation-consumed.json').read_text())
        expected = {str(CALIBRATION): CALIBRATION_SHA, str(PROFILE): PROFILE_SHA,
                    str(WORKSPACE/'frozen-winner.json'): marker['frozen_winner_sha256'],
                    **frozen['frozen_artifact_sha256']}
        expected[str(AUDIT)] = json.loads((WORKSPACE/'inputs/result.json').read_text())['input_audit_sha256']
        verify_hashes(expected)
        evidence = Path('docs/experiments/basketball-calibration-alternatives')
        for name in ['frozen-winner.json', 'validation.json', 'full-rig.json', 'export-reload.json']:
            expected[str(evidence/name)] = sha256(evidence/name)
        expected[str(WORKSPACE/'validation-consumed.json')] = sha256(WORKSPACE/'validation-consumed.json')
        profile = json.loads(PROFILE.read_text())
        calibration = json.loads(CALIBRATION.read_text())
        verify_membership(profile, calibration)
        from basketball_alternatives_compare import load_export
        load_export(CALIBRATION, expected=tuple(range(34)))
        audit = json.loads(AUDIT.read_text())
        if audit['status'] != 'inputs-verified' or len(audit['videos']) != 34:
            raise ValueError('original video audit incomplete')
        verify_hashes({str(AUDIT.parent/'frame-roles.json'): audit['frame_roles_sha256']})
        vipe = audit['vipe']['path']
        git = lambda *args: subprocess.check_output(['git', '-C', vipe, *args], text=True).strip()
        result['vipe'] = dict(path=vipe, revision=git('rev-parse', 'HEAD'),
                              branch=git('branch', '--show-current'), status=git('status', '--porcelain'))
        if result['vipe'] != dict(path=vipe, revision=PIN, branch='tridi', status=''):
            raise ValueError('ViPE provenance changed')
        if {int(v['camera_id']) for v in audit['videos']} != set(range(34)):
            raise ValueError('video IDs changed')
        root = (PROFILE.parent/profile['source']['video_root']).resolve()
        for video in audit['videos']:
            path = Path(video['path'])
            if path.resolve() != root/f"{int(video['camera_id'])}.mp4":
                raise ValueError('video-to-camera mapping changed')
            verify_hashes({str(path): video['sha256']})
            command = ['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-count_frames',
                       '-show_frames', '-show_streams', '-show_entries',
                       'stream=width,height,r_frame_rate,avg_frame_rate,nb_frames,nb_read_frames,time_base,start_time:frame=best_effort_timestamp_time,width,height',
                       '-of', 'json', str(path)]
            probe = subprocess.run(command, capture_output=True, text=True, check=True)
            timestamps = validate_probe(json.loads(probe.stdout))
            if probe.stderr or timestamps != video['timestamps_seconds']:
                raise ValueError(f'changed decode/timestamps: {path}')
            result['videos'].append(dict(camera_id=int(video['camera_id']), path=str(path),
                sha256=video['sha256'], decoded_frames=len(timestamps), timestamps_seconds=timestamps,
                dimensions=[1920, 1080], frame_rate=25))
            print(f"verified video {video['camera_id']}", flush=True)
        result['sha256'] = expected
        result['status'] = 'passed'
    except Exception as error:
        result['blockers'].append(f'{type(error).__name__}: {error}')
        raise
    finally:
        result['wall_seconds'] = time.monotonic()-started
        (a.output/'result.json').write_text(json.dumps(result, indent=2, allow_nan=False)+'\n')


if __name__ == '__main__':
    main()

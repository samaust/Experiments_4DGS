"""Export Plan 028 six-panel source-cadence videos and fixed crops."""
import argparse
import json
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from basketball_study import MANIFEST, ROOT, digest, write_new

ARMS = ('holdout-original', 'holdout-repaired', 'all-times-original', 'all-times-repaired')
CAMERAS = ('0', '10', '20', '30')
CROPS = {
    '0': {'court': (270, 240, 490, 450), 'display': (775, 0, 905, 72), 'players': (550, 145, 705, 320)},
    '10': {'court': (275, 245, 525, 460), 'display': (680, 125, 895, 285), 'players': (320, 50, 530, 235)},
    '20': {'court': (425, 285, 645, 345), 'display': (195, 195, 410, 380), 'players': (605, 75, 810, 305)},
    '30': {'court': (510, 250, 690, 400), 'display': (25, 45, 170, 165), 'players': (360, 270, 465, 505)},
}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--artifact-root', type=Path, default=ROOT/'.local/basketball-crossing-repair')
    p.add_argument('--output', type=Path, default=ROOT/'.local/basketball-crossing-repair/videos')
    a = p.parse_args()
    records = {}
    for path in sorted((a.artifact_root/'evaluation').rglob('record-070000.json')):
        r = json.loads(path.read_text())
        if r.get('iteration') == 70000 and r.get('reload', {}).get('complete'):
            records[r['arm'], r['seed'], r['training_policy']+'-'+r['lifetime_policy']] = r
    expected = {(arm, seed, policy) for arm in ('freetimegs-dense-coarse', 'freetimegs-dense-cropped')
                for seed in range(3) for policy in ARMS}
    if set(records) != expected:
        raise ValueError(f'visual endpoint coverage mismatch: {len(records)} of {len(expected)}')
    manifest = json.loads(MANIFEST.read_text())
    camera_map = {str(x['id']): x for x in manifest['cameras']}
    protocol = {'schema': 'basketball-crossing-visual-protocol/v1', 'source_frames': [0, 49],
                'fps': 25, 'panels': ['ground truth', 'parent-050000'] + list(ARMS), 'cameras': list(CAMERAS)}
    a.output.mkdir(parents=True, exist_ok=True)
    artifacts = []

    def source(camera, frame):
        x = camera_map[camera]['frames'][frame]
        path = MANIFEST.parent/x['path']
        if digest(path) != x['sha256']:
            raise ValueError('source image hash mismatch')
        return Image.open(path).convert('RGB')

    def render_row(record, camera, frame):
        report_path = Path(record['render'])
        report = json.loads(report_path.read_text())
        row = next(x for x in report['frames'] if str(x['camera']) == camera and x['frame_id'] == frame)
        path = report_path.parent/row['path']
        if digest(path) != row['sha256']:
            raise ValueError('render image hash mismatch')
        return Image.open(path).convert('RGB')

    def parent(recipe, seed, camera, frame):
        path = (a.artifact_root.parent/'basketball-dense-training'/'evaluation'/
                f'{recipe}-seed{seed}'/'050000'/'first'/'render.json')
        report = json.loads(path.read_text())
        row = next(x for x in report['frames'] if str(x['camera']) == camera and x['frame_id'] == frame)
        image = path.parent/row['path']
        if digest(image) != row['sha256']:
            raise ValueError('parent image hash mismatch')
        return Image.open(image).convert('RGB')

    names = ('Ground truth', 'Parent 50k', 'A holdout/orig', 'B holdout/fixed', 'C all/orig', 'D all/fixed')
    def panel(images, label):
        width, height = images[0].size
        out = Image.new('RGB', (6*width, height+52))
        draw = ImageDraw.Draw(out); font = ImageFont.load_default(size=18)
        draw.text((4, 3), label, fill='white', font=font)
        for i, image in enumerate(images):
            out.paste(image, (i*width, 52)); draw.text((i*width+4, 26), names[i], fill='white', font=font)
        return out

    for recipe in ('freetimegs-dense-coarse', 'freetimegs-dense-cropped'):
        for seed in range(3):
            for camera in CAMERAS:
                base = a.output/f'{recipe}-camera{camera}-seed{seed}'
                base.mkdir(parents=True, exist_ok=True)
                def images(frame):
                    return [source(camera, frame), parent(recipe, seed, camera, frame)] + [
                        render_row(records[recipe, seed, arm], camera, frame) for arm in ARMS]
                for crop, box in CROPS[camera].items():
                    image = panel([x.crop(box) for x in images(22)], f'{recipe} camera {camera} seed {seed} frame 22')
                    path = base/f'{crop}.png'; image.save(path)
                    artifacts.append({'path': str(path.relative_to(a.output)), 'sha256': digest(path), 'kind': crop})
                video = base/'comparison.mp4'
                command = ['ffmpeg', '-hide_banner', '-loglevel', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24',
                           '-s', '5760x592', '-framerate', '25', '-i', '-', '-an', '-c:v', 'libx264',
                           '-preset', 'medium', '-crf', '18', '-pix_fmt', 'yuv420p', '-frames:v', '50', '-y', str(video)]
                with video.with_suffix('.ffmpeg.log').open('w') as log:
                    proc = subprocess.Popen(command, stdin=subprocess.PIPE, stderr=log)
                    try:
                        for frame in range(50): proc.stdin.write(panel(images(frame), f'{recipe} camera {camera} seed {seed} frame {frame}').tobytes())
                        proc.stdin.close()
                        if proc.wait() != 0: raise RuntimeError('ffmpeg failed')
                    finally:
                        if proc.poll() is None: proc.terminate(); proc.wait(timeout=30)
                probe = json.loads(subprocess.check_output(['ffprobe', '-v', 'error', '-count_frames', '-select_streams', 'v:0',
                    '-show_entries', 'stream=nb_read_frames,r_frame_rate,width,height', '-of', 'json', str(video)], text=True))['streams'][0]
                if probe != {'nb_read_frames': '50', 'r_frame_rate': '25/1', 'width': 5760, 'height': 592}:
                    raise ValueError(f'video probe mismatch: {probe}')
                artifacts.append({'path': str(video.relative_to(a.output)), 'sha256': digest(video), 'kind': 'video', 'probe': probe})
                print(json.dumps({'recipe': recipe, 'camera': camera, 'seed': seed}), flush=True)
    write_new(a.output/'artifacts.json', dict(protocol=protocol, artifacts=artifacts, complete=True,
        endpoint_count=24, video_count=24, crop_count=72))


if __name__ == '__main__': main()

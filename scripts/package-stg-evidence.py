#!/usr/bin/env python3
"""Package SelfCap render evidence with fixed GT-selected crops and CPU videos.

Reuses contact-sheet and sequence-analysis helpers. PNGs retain their exact
resolution; H.264 videos are padded by at most one right/bottom pixel for 4:2:0.
Metrics are run separately so packaging cannot hide an evaluation failure.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

from PIL import Image


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--render-directory', type=Path, required=True)
    p.add_argument('--manifest', type=Path, required=True)
    p.add_argument('--crops', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    if a.output.exists():
        p.error('choose a new evidence directory')
    manifest = json.loads(a.manifest.read_text())
    render = json.loads((a.render_directory/'render.json').read_text())
    crops = json.loads(a.crops.read_text())
    if render['manifest_sha256'] != digest(a.manifest):
        p.error('render/manifest provenance mismatch')
    camera = next(c for c in manifest['cameras'] if c['id'] == crops['camera'])
    if camera['split'] != 'test' or crops['dimensions'] != [camera['width'], camera['height']]:
        p.error('crop camera split/dimensions mismatch')
    selected = next(f for f in camera['frames'] if f['frame_id'] == crops['selection_frame'])
    if digest(a.manifest.parent/selected['path']) != crops['selection_image_sha256']:
        p.error('crop-selection ground truth changed')
    for box in crops['crops'].values():
        if len(box) != 4 or not all(type(v) is int for v in box):
            p.error('crop bounds must be four integer coordinates')
        left, top, right, bottom = box
        if not (0 <= left < right <= camera['width'] and 0 <= top < bottom <= camera['height']):
            p.error('crop outside image')
    reference = (a.manifest.parent/selected['path']).parent
    prediction = a.render_directory/'images'/camera['id']
    expected = {f'{f["frame_id"]:06d}.png' for f in camera['frames']}
    if {f.name for f in prediction.glob('*.png')} != expected:
        p.error('incomplete held-out prediction sequence')
    if {f.name for f in (a.render_directory/'sweep').glob('*.png')} != {f'{i:05d}.png' for i in range(20)}:
        p.error('incomplete sweep sequence')
    for f in camera['frames']:
        if digest(a.manifest.parent/f['path']) != f['sha256']:
            p.error('ground-truth image hash mismatch')
    for record in render['frames']:
        if digest(a.render_directory/record['path']) != record['sha256']:
            p.error('prediction image hash mismatch')
    a.output.mkdir(parents=True)
    commands = []

    helpers = Path(__file__).resolve().parent
    with (a.output/'packaging.log').open('w') as log:
        def run_logged(command):
            commands.append(list(map(str, command)))
            subprocess.run(commands[-1], check=True, stdout=log, stderr=subprocess.STDOUT)

        for label, directory in [('ground-truth', reference), ('prediction', prediction),
                                  ('sweep', a.render_directory/'sweep')]:
            run_logged([sys.executable, helpers/'contact-sheet.py', '--input', directory,
                        '--output', a.output/(label+'-contact.png')])
            start, fps, digits, count = (0, 20, 5, 20) if label == 'sweep' else (4120, 60, 6, 60)
            run_logged(['ffmpeg', '-nostdin', '-n', '-framerate', fps, '-start_number', start,
                '-i', directory/('%0'+str(digits)+'d.png'), '-frames:v', count,
                '-vf', 'pad=ceil(iw/2)*2:ceil(ih/2)*2', '-c:v', 'libx264', '-threads', '2',
                '-crf', '18', '-pix_fmt', 'yuv420p', a.output/(label+'.mp4')])
        for label, directory in [('ground-truth', reference), ('prediction', prediction)]:
            for crop_name, box in crops['crops'].items():
                destination = a.output/'crops'/label/crop_name
                destination.mkdir(parents=True)
                for filename in sorted(expected):
                    with Image.open(directory/filename) as image:
                        if image.size != tuple(crops['dimensions']) or image.mode != 'RGB':
                            raise ValueError('unexpected image format')
                        image.crop(box).save(destination/filename)
                run_logged([sys.executable, helpers/'contact-sheet.py', '--input', destination,
                            '--output', a.output/f'{label}-{crop_name}-contact.png'])
        run_logged([sys.executable, helpers/'analyze-sequence.py', '--input', prediction,
                    '--output', a.output/'sequence-analysis.json'])
    report = dict(render_report_sha256=digest(a.render_directory/'render.json'),
        manifest_sha256=digest(a.manifest), crop_config_sha256=digest(a.crops), crops=crops,
        commands=commands, png_dimensions=crops['dimensions'],
        video_dimensions=[(v+1)//2*2 for v in crops['dimensions']],
        note='Videos are padded, never resized. Adjacent changes include real motion and are not flicker scores.')
    (a.output/'evidence.json').write_text(json.dumps(report, indent=2)+'\n')
    print(a.output)


if __name__ == '__main__':
    main()

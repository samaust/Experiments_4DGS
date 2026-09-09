"""Fixed-crop comparisons and source-cadence videos for available Plan 026 arms."""
import argparse
import json
from pathlib import Path
import subprocess

from PIL import Image, ImageDraw, ImageFont

from basketball_study import DOCS, MANIFEST, ROOT, digest, write_new


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--inputs', type=Path, required=True,
                        help='JSON records with arm, seed, iteration and render.json path')
    parser.add_argument('--iteration', type=int, choices=(5000, 50000), required=True)
    parser.add_argument('--output', type=Path, required=True)
    a = parser.parse_args()
    inputs = json.loads(a.inputs.read_text())['records']
    selected = [r for r in inputs if r['iteration'] == a.iteration]
    required = {(m, s) for m in ('stg-full', 'freetimegs-sparse') for s in range(3)}
    if len(selected) != 6 or {(r['arm'], r['seed']) for r in selected} != required:
        raise ValueError('requires all six matched sparse-arm endpoint renders')
    visual_protocol = DOCS / 'visual-protocol.json'
    protocol = json.loads(visual_protocol.read_text())
    frame = protocol['source_frame']
    manifest = json.loads(MANIFEST.read_text())
    cameras = {c['id']: c for c in manifest['cameras']}
    renders = {}
    for r in selected:
        path = Path(r['render'])
        report = json.loads(path.read_text())
        if report['iteration'] != a.iteration or not report['complete']:
            raise ValueError('incomplete or mismatched visual checkpoint')
        if digest(path) != r['render_sha256']:
            raise ValueError('render provenance changed')
        renders[r['arm'], r['seed']] = (path.parent, {(x['camera'], x['frame_id']): x for x in report['frames']})
    a.output.mkdir(parents=True, exist_ok=False)
    artifacts = []
    def read(path, sha):
        if digest(path) != sha:
            raise ValueError('visual source hash mismatch')
        image = Image.open(path).convert('RGB')
        if image.size != (960, 540):
            raise ValueError('visual source resolution changed')
        return image
    def panels(camera, f, seed):
        entry = cameras[camera]['frames'][f]
        result = [read(MANIFEST.parent / entry['path'], entry['sha256'])]
        for arm in ('stg-full', 'freetimegs-sparse'):
            directory, rows = renders[arm, seed]
            row = rows[camera, f]
            result.append(read(directory / row['path'], row['sha256']))
        return result
    def row(images, label):
        width, height = images[0].size
        canvas = Image.new('RGB', (3*width, height+52))
        draw = ImageDraw.Draw(canvas)
        font = ImageFont.load_default(size=18 if width >= 480 else 11)
        draw.text((4, 3), label, fill='white', font=font)
        for i, (image, name) in enumerate(zip(images, ('Ground truth', 'STG Full', 'FreeTimeGS sparse'))):
            canvas.paste(image, (i*width, 52))
            draw.text((i*width+4, 26), name, fill='white', font=font)
        return canvas
    for seed in range(3):
        for camera, crops in protocol['cameras'].items():
            original = panels(camera, frame, seed)
            label = f'camera {camera} seed {seed} update {a.iteration}'
            for name, box in crops.items():
                path = a.output / f'camera{camera}-seed{seed}-{name}.png'
                row([im.crop(box) for im in original], label).save(path)
                artifacts.append(dict(path=path.name, sha256=digest(path), kind=name))
            path = a.output / f'camera{camera}-seed{seed}-full.png'
            row(original, label).save(path)
            artifacts.append(dict(path=path.name, sha256=digest(path), kind='full'))
            video = a.output / f'camera{camera}-seed{seed}.mp4'
            command = ['ffmpeg', '-hide_banner', '-loglevel', 'error', '-f', 'rawvideo',
                       '-pix_fmt', 'rgb24', '-s', '2880x592', '-framerate', '25', '-i', '-',
                       '-an', '-c:v', 'libx264', '-preset', 'medium', '-crf', '18',
                       '-pix_fmt', 'yuv420p', '-frames:v', '50', '-n', str(video)]
            with (a.output / f'camera{camera}-seed{seed}-ffmpeg.log').open('w') as log:
                encoder = subprocess.Popen(command, stdin=subprocess.PIPE, stderr=log)
                try:
                    for f in range(50):
                        encoder.stdin.write(row(panels(camera, f, seed), label+f' frame {f}').tobytes())
                    encoder.stdin.close()
                    if encoder.wait() != 0:
                        raise RuntimeError('video encoder failed; inspect retained log')
                finally:
                    if encoder.poll() is None:
                        encoder.terminate()
                        encoder.wait(timeout=30)
            probe = json.loads(subprocess.check_output(['ffprobe', '-v', 'error', '-count_frames',
                '-select_streams', 'v:0', '-show_entries', 'stream=nb_read_frames,r_frame_rate,width,height',
                '-of', 'json', str(video)], text=True))['streams'][0]
            if probe['nb_read_frames'] != '50' or probe['r_frame_rate'] != '25/1':
                raise ValueError('video cadence or frame count mismatch')
            artifacts.append(dict(path=video.name, sha256=digest(video), kind='video', probe=probe))
            print(json.dumps(dict(camera=camera, seed=seed, iteration=a.iteration)), flush=True)
    write_new(a.output / 'artifacts.json', dict(schema='basketball-study-visuals/v1',
        iteration=a.iteration, protocol_sha256=digest(visual_protocol), inputs_sha256=digest(a.inputs),
        artifacts=artifacts, missing='dense arm prerequisite failed; these are available-arm comparisons'))


if __name__ == '__main__':
    main()

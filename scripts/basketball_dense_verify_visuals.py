"""Verify fixed four-arm panel pixels, provenance, and source-cadence videos."""
import argparse
import json
from pathlib import Path
import subprocess

from PIL import Image

from basketball_study import DOCS, MANIFEST, digest, write_new


def verify(inputs_path, folder):
    index_path = folder / 'artifacts.json'
    index = json.loads(index_path.read_text())
    protocol_path = DOCS / 'visual-protocol.json'
    arms = ['stg-full', 'freetimegs-sparse', 'freetimegs-dense-coarse', 'freetimegs-dense-cropped']
    if (not index['complete'] or index['arms'] != arms or
            index['inputs_sha256'] != digest(inputs_path) or
            index['protocol_sha256'] != digest(protocol_path)):
        raise ValueError('visual provenance mismatch')
    records = [r for r in json.loads(inputs_path.read_text())['records']
               if r['iteration'] == index['iteration']]
    if len(records) != 12 or {(r['arm'], r['seed']) for r in records} != {
            (arm, seed) for arm in arms for seed in range(3)}:
        raise ValueError('four-arm seed coverage mismatch')
    renders = {}
    for record in records:
        path = Path(record['render'])
        if digest(path) != record['render_sha256']:
            raise ValueError('render provenance mismatch')
        render = json.loads(path.read_text())
        if not render['complete'] or render['iteration'] != index['iteration']:
            raise ValueError('render endpoint mismatch')
        renders[record['arm'], record['seed']] = (
            path.parent, {(r['camera'], r['frame_id']): r for r in render['frames']})
    protocol = json.loads(protocol_path.read_text())
    cameras = {c['id']: c for c in json.loads(MANIFEST.read_text())['cameras']}
    frame = protocol['source_frame']
    artifacts = {r['path']: r for r in index['artifacts']}
    if len(artifacts) != len(index['artifacts']):
        raise ValueError('duplicate visual artifact')
    expected = set()

    def read(path, sha):
        if digest(path) != sha:
            raise ValueError(f'visual image changed: {path}')
        with Image.open(path) as image:
            return image.convert('RGB')

    for seed in range(3):
        for camera, crops in protocol['cameras'].items():
            gt = cameras[camera]['frames'][frame]
            sources = [read(MANIFEST.parent / gt['path'], gt['sha256'])]
            for arm in arms:
                directory, rows = renders[arm, seed]
                row = rows[camera, frame]
                sources.append(read(directory / row['path'], row['sha256']))
            for kind, box in dict(crops, full=[0, 0, 960, 540]).items():
                name = f'camera{camera}-seed{seed}-{kind}.png'
                expected.add(name)
                artifact = artifacts[name]
                if artifact['kind'] != kind:
                    raise ValueError('panel kind mismatch')
                panel = read(folder / name, artifact['sha256'])
                width, height = box[2]-box[0], box[3]-box[1]
                if panel.size != (5*width, height+52):
                    raise ValueError('panel dimensions mismatch')
                for column, source in enumerate(sources):
                    pixels = panel.crop((column*width, 52, (column+1)*width, height+52))
                    if pixels.tobytes() != source.crop(box).tobytes():
                        raise ValueError(f'panel source pixels differ: {name}, column {column}')
            name = f'camera{camera}-seed{seed}.mp4'
            expected.add(name)
            artifact = artifacts[name]
            if artifact['kind'] != 'video' or digest(folder/name) != artifact['sha256']:
                raise ValueError('video provenance mismatch')
            probe = json.loads(subprocess.check_output([
                'ffprobe', '-v', 'error', '-count_frames', '-select_streams', 'v:0',
                '-show_entries', 'stream=nb_read_frames,r_frame_rate,width,height',
                '-of', 'json', str(folder/name)], text=True))['streams'][0]
            if (probe != artifact['probe'] or probe['nb_read_frames'] != '50' or
                    probe['r_frame_rate'] != '25/1' or
                    (probe['width'], probe['height']) != (4800, 592)):
                raise ValueError('video cadence or dimensions mismatch')
    if set(artifacts) != expected or len(expected) != 60:
        raise ValueError('visual artifact coverage mismatch')
    return dict(passed=True, iteration=index['iteration'], pngs=48, videos=12,
                pixel_columns='all 48 full and fixed-crop panels match all five source columns',
                video_frames=50, fps=25, video_dimensions=[4800, 592],
                index=str(index_path), sha256=digest(index_path),
                scope='all held-out cameras and seeds; frozen crops and source cadence')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--inputs', type=Path, required=True)
    parser.add_argument('--visuals', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    write_new(args.output, verify(args.inputs, args.visuals))


if __name__ == '__main__':
    main()

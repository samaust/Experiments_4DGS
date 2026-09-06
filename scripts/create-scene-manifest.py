#!/usr/bin/env python3
"""Create and validate the shared, method-independent scene manifest.

The input metadata is deliberately JSON rather than method configuration.  This
keeps camera exclusions, frame windows, and time conversion identical for every
adapter.  Paths are recorded relative to the metadata file's directory and all
listed source files receive SHA-256 hashes.
"""
import argparse
import hashlib
import json
from pathlib import Path


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def build(metadata_path):
    metadata_path = metadata_path.resolve()
    raw = json.loads(metadata_path.read_text())
    required = ('scene', 'source', 'frames', 'cameras', 'evaluation')
    missing = [key for key in required if key not in raw]
    if missing:
        raise ValueError('manifest metadata missing: ' + ', '.join(missing))
    frames = raw['frames']
    start, end = frames.get('start'), frames.get('end')
    if type(start) is not int or type(end) is not int or not 0 <= start < end:
        raise ValueError('frames.start/end must define a non-empty half-open range')
    cameras = raw['cameras']
    ids = [str(camera['id']) for camera in cameras]
    if len(ids) != len(set(ids)):
        raise ValueError('camera IDs must be unique')
    heldout = {str(item) for item in raw['evaluation'].get('held_out_cameras', [])}
    unknown = heldout - set(ids)
    if unknown:
        raise ValueError('held-out camera is not in cameras: ' + ', '.join(sorted(unknown)))
    train = [item for item in ids if item not in heldout]
    if not train:
        raise ValueError('at least one training camera is required')
    fps = raw['source'].get('frame_rate')
    if not isinstance(fps, (int, float)) or fps <= 0:
        raise ValueError('source.frame_rate must be positive')
    root = metadata_path.parent
    files = []
    for item in raw.get('source', {}).get('files', []):
        path = (root / item).resolve()
        if not path.is_file():
            raise ValueError('source file does not exist: ' + str(path))
        # Preserve the user-supplied relative spelling (which may deliberately
        # point from configs/ into .local/) while hashing the resolved target.
        files.append({'path': Path(item).as_posix(), 'bytes': path.stat().st_size,
                      'sha256': digest(path)})
    values = dict(raw)
    values['schema'] = 'dynamic-gaussian-scene/v1'
    values['frames'] = dict(frames, ids=list(range(start, end)), count=end - start,
                            normalized_time={'formula': 'frame_offset / count',
                                              'first': 0.0,
                                              'last': (end - start - 1) / (end - start)})
    values['evaluation'] = dict(raw['evaluation'], held_out_cameras=sorted(heldout),
                                training_cameras=train)
    values['source'] = dict(raw['source'], files=files)
    calibration_root = raw['source'].get('calibration_root')
    sync_file = raw['source'].get('sync_file')
    if calibration_root:
        calibration = (root / calibration_root).resolve()
        if not calibration.is_dir():
            raise ValueError('calibration_root does not exist: ' + str(calibration))
        values['calibration'] = {'root': str(Path(calibration_root).as_posix()), 'files': {}}
        for name in raw['source'].get('calibration_files', []):
            path = calibration / name
            if not path.is_file():
                raise ValueError('calibration file does not exist: ' + str(path))
            values['calibration']['files'][name] = {
                'bytes': path.stat().st_size, 'sha256': digest(path)}
    if sync_file:
        path = (root / sync_file).resolve()
        if not path.is_file():
            raise ValueError('sync_file does not exist: ' + str(path))
        offsets = json.loads(path.read_text())
        if not isinstance(offsets, dict):
            raise ValueError('sync_file must contain a camera-to-offset JSON object')
        values['synchronization'] = {
            'formula': 'actual_timestamp_seconds = frame_index / source.frame_rate - offset',
            'offset_seconds': {str(key): float(value) for key, value in offsets.items()},
            'file': str(Path(sync_file).as_posix()), 'sha256': digest(path)}
    values['provenance'] = {'metadata': str(metadata_path), 'metadata_sha256': digest(metadata_path)}
    return values


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('metadata', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error('refusing to overwrite existing manifest: ' + str(args.output))
    try:
        manifest = build(args.metadata)
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as error:
        parser.error(str(error))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(manifest, indent=2) + '\n')
    print(args.output.resolve())


if __name__ == '__main__':
    main()

"""One-load native Marigold folder inference and exact frame-order handoff."""

import hashlib
import os
from pathlib import Path
import re
import signal
import subprocess

import numpy as np
from PIL import Image

from .files import file_record, write_json
from .depth_native_packages import qualify
from .depth_source_integrity import verify_source
from .marigold_relative import PROFILE, SOURCE_REVISION


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def _paths(setup):
    _require(setup.get('schema') == 'plan069-depth-setup-result/v1' and
             setup.get('status') == 'complete' and
             setup.get('candidate') == 'D11' and
             setup.get('source_revision') == SOURCE_REVISION,
             'D11 requires completed pinned setup')
    verify_source(setup)
    source = Path(setup['source_dir'])
    native = source / 'scripts/infer.py'
    _require(setup.get('source_archive') == file_record(setup['source_archive']['path']),
             'D11 source archive changed since setup')
    _require(setup.get('native_source') == file_record(native),
             'D11 native source changed since setup')
    root = Path(setup['source_archive']['path']).parent
    expected = root / 'assets/checkpoints'
    _require(len(setup.get('assets', [])) == 12 and
             all(file_record(row['record']['path']) == row['record'] and
                 Path(row['record']['path']).is_relative_to(expected) for row in setup['assets']),
             'D11 pinned assets changed since setup')
    checkpoint = expected / 'Marigold-V2/depth/Log-stage2'
    _require(checkpoint.is_dir() and (checkpoint / 'trainables.safetensors').is_file(),
             'D11 Log-stage2 checkpoint directory missing')
    return native, root / 'assets', checkpoint


def _supervised_run(command, *, timeout, check, reserved_group=False, **kwargs):
    """Stop the native CLI and its evaluation child together at the deadline."""
    if reserved_group and os.getpgrp() != os.getpid():
        raise ValueError('actual D11 requires reserved worker process group')
    with subprocess.Popen(command, start_new_session=not reserved_group, **kwargs) as process:
        try:
            returncode = process.wait(timeout=timeout)
        except BaseException:
            try:
                os.killpg(os.getpgrp() if reserved_group else process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            process.wait()
            raise
        if check and returncode:
            raise subprocess.CalledProcessError(returncode, command)
        return subprocess.CompletedProcess(command, returncode)


def run_folder(setup, frames, output, *, interpreter, timeout_seconds, runner=_supervised_run):
    """Run the pinned CLI once for all independent RGB frames in one model process.

    `frames` is an ordered sequence of (stable frame ID, uint8 RGB array). The
    caller must hold the exact one-use GPU ledger reservation. No fallback
    checkpoint, remote model fetch, resize override or repeated load is used.
    """
    native, assets_dir, checkpoint = _paths(setup)
    _require(isinstance(timeout_seconds, (int, float)) and 0 < timeout_seconds <= 7200,
             'D11 native timeout exceeds approved GPU attempt')
    output = Path(output)
    _require(not output.exists(), 'immutable D11 native output already exists')
    _require(frames and len(frames) <= 256, 'D11 frame count exceeds approved workload')
    interpreter = Path(interpreter).absolute()
    _require(interpreter.is_file(), 'qualified D11 interpreter missing')
    qualification = qualify('D11', interpreter)
    _require(file_record(interpreter.parent / 'python') == file_record(interpreter),
             'D11 child Python differs from qualified interpreter')
    ids = [frame_id for frame_id, _ in frames]
    _require(len(set(ids)) == len(ids) and
             all(re.fullmatch(r'[A-Za-z0-9_-]+', frame_id) for frame_id in ids),
             'D11 frame IDs must be unique safe names')
    output.mkdir(parents=True, exist_ok=False)
    image_dir = output / 'images'
    image_dir.mkdir()
    inputs = []
    for frame_id, rgb in frames:
        _require(isinstance(rgb, np.ndarray) and rgb.shape == (540, 960, 3) and
                 rgb.dtype == np.uint8, 'D11 requires accepted 960x540 uint8 RGB')
        path = image_dir / (frame_id + '.png')
        Image.fromarray(rgb, 'RGB').save(path)
        inputs.append(dict(id=frame_id, rgb_sha256=hashlib.sha256(rgb.tobytes()).hexdigest(),
                           staged=file_record(path)))
    command = [str(interpreter), str(native), '--modality', 'depth',
               '--checkpoint', str(checkpoint), '--image_dir', str(image_dir),
               '--output_dir', str(output / 'native'), '--seed', str(PROFILE['seed'])]
    env = dict(os.environ, DEPTH_ASSETS_DIR=str(assets_dir), HF_HUB_OFFLINE='1',
               TRANSFORMERS_OFFLINE='1', PYTHONDONTWRITEBYTECODE='1',
               PYTHONNOUSERSITE='1', PATH=str(interpreter.absolute().parent) + os.pathsep +
               os.environ.get('PATH', ''))
    env.pop('PYTHONPATH', None)
    env.pop('PYTHONHOME', None)
    write_json(output / 'request.json', dict(schema='plan069-D11-native-folder-request/v1',
        profile=PROFILE, native_qualification=qualification,
        setup_source=setup['native_source'], source_manifest=setup['source_manifest'],
        setup_assets=[row['record'] for row in setup['assets']],
        inputs=inputs, command=command, timeout_seconds=timeout_seconds))
    try:
        with (output / 'native.log').open('xb') as log:
            runner(command, cwd=native.parents[1], env=env, stdout=log,
                   stderr=subprocess.STDOUT, timeout=timeout_seconds, check=True,
                   reserved_group=setup.get('record_kind') == 'actual')
        results = []
        for row in inputs:
            path = output / 'native/images/predictions_npy' / (row['id'] + '.npy')
            _require(path.is_file(), 'D11 native prediction missing: ' + row['id'])
            value = np.load(path, allow_pickle=False)
            _require(value.shape == (540, 960) and value.dtype == np.float32 and
                     np.isfinite(value).any(), 'D11 native restored prediction grid invalid')
            results.append(dict(id=row['id'], rgb_sha256=row['rgb_sha256'],
                                prediction=file_record(path)))
        write_json(output / 'result.json', dict(schema='plan069-D11-native-folder-result/v1',
            status='complete', profile=PROFILE, native_qualification=qualification,
            setup_source=setup['native_source'], source_manifest=setup['source_manifest'],
            inputs=inputs, predictions=results, log=file_record(output / 'native.log')))
        return results
    except BaseException as error:
        write_json(output / 'failure.json', dict(schema='plan069-D11-native-folder-failure/v1',
            status='failed', error=f'{type(error).__name__}: {error}',
            log=file_record(output / 'native.log') if (output / 'native.log').is_file() else None))
        raise


class CachedD11Runtime:
    """Feed ordered native folder results to the existing D11 adapter."""

    profile = PROFILE
    training = False

    def __init__(self, predictions):
        self.predictions = list(predictions)
        self.next_index = 0

    def infer_image(self, rgb, *, seed):
        _require(seed == PROFILE['seed'] and self.next_index < len(self.predictions),
                 'D11 prediction order or seed changed')
        row = self.predictions[self.next_index]
        _require(row['rgb_sha256'] == hashlib.sha256(rgb.tobytes()).hexdigest(),
                 'D11 native prediction/input mismatch')
        value = np.load(row['prediction']['path'], allow_pickle=False)
        _require(file_record(row['prediction']['path']) == row['prediction'] and
                 value.shape == (540, 960) and value.dtype == np.float32,
                 'D11 native prediction changed')
        self.next_index += 1
        return value

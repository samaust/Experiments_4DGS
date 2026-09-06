"""Commit-marked native ATGS model/optimizer/loop checkpoints.

Call synchronously at a completed microstep, with training paused throughout.
An incomplete directory is preserved for diagnosis, never accepted for resume.
"""
import hashlib
import json
import os
from pathlib import Path
import re

import torch

from atgs_checkpoint import capture_auxiliary_state, inspect_native_checkpoint
from atgs_loop_state import capture_loop_state


def validate_provenance(provenance):
    lengths = dict(manifest_sha256=64, source_revision=40, config_sha256=64,
                   helper_ast_sha256=64)
    if not isinstance(provenance, dict) or provenance.keys() != lengths.keys():
        raise ValueError('bundle provenance fields mismatch')
    for name, length in lengths.items():
        if not isinstance(provenance[name], str) or not re.fullmatch('[0-9a-f]{%d}' % length, provenance[name]):
            raise ValueError(f'invalid provenance digest: {name}')


def _inventory(directory):
    result = inspect_native_checkpoint(directory, require_optimizers=True, require_auxiliary=True)
    path = directory / 'loop.pth'
    if path.is_symlink() or not path.is_file() or path.stat().st_size == 0:
        raise ValueError('missing, empty or linked loop supplement')
    with path.open('rb') as stream:
        result['loop.pth'] = dict(bytes=path.stat().st_size,
                                 sha256=hashlib.file_digest(stream, 'sha256').hexdigest())
    return result


def _sync_directory(directory):
    descriptor = os.open(directory, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def save_bundle(directory, model, sampler, loop, provenance, *, include_cuda=True):
    """Save to a new directory; atomically publish bundle.json only after fsync.

    This does not overwrite checkpoints or move a latest pointer. GPU state is
    required unless explicitly disabled for CPU fixtures. The caller supplies
    digests of its actual resolved configuration and patched update helpers.
    """
    validate_provenance(provenance)
    supplement = capture_loop_state(model, sampler, loop, include_cuda=include_cuda)
    auxiliary = capture_auxiliary_state(model)
    directory = Path(directory).absolute()
    directory.mkdir()  # Exclusive reservation; parent must already exist.
    model.save_ply(str(directory / 'point_cloud.ply'))
    model.save_mlp_checkpoints(str(directory))
    model.save_optimizer(str(directory))
    torch.save(auxiliary, directory / 'auxiliary.pth')
    torch.save(supplement, directory / 'loop.pth')
    inventory = _inventory(directory)
    for name in inventory:
        with (directory / name).open('rb') as stream:
            os.fsync(stream.fileno())
    record = dict(schema='atgs-bundle/v1', provenance=dict(provenance), files=inventory,
                  iteration=loop['iteration'], update_count=loop['update_count'])
    with (directory / 'bundle.json.pending').open('x') as stream:
        json.dump(record, stream, indent=2, allow_nan=False)
        stream.write('\n')
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(directory / 'bundle.json.pending', directory / 'bundle.json')
    _sync_directory(directory)
    _sync_directory(directory.parent)
    return record


def inspect_bundle(directory, *, expected_provenance):
    """Validate completion, provenance and all bytes before deserializing state."""
    validate_provenance(expected_provenance)
    directory = Path(directory).absolute()
    marker = directory / 'bundle.json'
    if directory.is_symlink() or marker.is_symlink() or not marker.is_file():
        raise ValueError('missing or linked bundle completion marker/directory')
    record = json.loads(marker.read_text())
    if record.get('schema') != 'atgs-bundle/v1':
        raise ValueError('unsupported bundle schema')
    if record.get('provenance') != expected_provenance:
        raise ValueError('bundle provenance mismatch')
    if record.get('files') != _inventory(directory):
        raise ValueError('bundle component inventory mismatch')
    for name in ('iteration', 'update_count'):
        if type(record.get(name)) is not int or record[name] < 0:
            raise ValueError('invalid bundle counter')
    if record['update_count'] > record['iteration']:
        raise ValueError('inconsistent bundle counters')
    return record


def load_bundle_supplements(directory, *, expected_provenance):
    """Load verified CPU supplements; caller restores native model first.

    Restore auxiliary state before constructing/loading optimizers, then call
    restore_loop_state after both optimizers have been loaded. Bundles must be
    immutable during verification and loading; hashes are not authentication.
    """
    record = inspect_bundle(directory, expected_provenance=expected_provenance)
    directory = Path(directory)
    loop = torch.load(directory / 'loop.pth', map_location='cpu', weights_only=True)
    if loop.get('schema') != 'atgs-loop/v1' or any(
            loop['loop'][name] != record[name] for name in ('iteration', 'update_count')):
        raise ValueError('bundle and loop counters mismatch')
    auxiliary = torch.load(directory / 'auxiliary.pth', map_location='cpu', weights_only=True)
    return auxiliary, loop, record

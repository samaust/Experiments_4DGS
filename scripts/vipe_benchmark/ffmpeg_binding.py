"""Bind the hash-locked imageio wheel binary without a subprocess probe."""
import base64
import csv
import importlib.metadata
import io
import os
from pathlib import Path
import sys

from .files import file_record, verify_record

VERSION = '0.6.0'
RELATIVE = 'imageio_ffmpeg/binaries/ffmpeg-linux-x86_64-v7.0.2'


def bind(expected=None, *, environment=None):
    """Verify managed wheel ownership/RECORD bytes, then force import-only lookup.

    imageio's automatic discovery executes ``ffmpeg -version``. The worker
    isolation correctly denies that subprocess. An explicit, verified wheel
    path avoids discovery while leaving the subprocess prohibition intact.
    """
    managed = Path(sys.prefix).resolve()
    if environment is not None and managed != Path(environment).resolve():
        raise ValueError('E5 FFmpeg worker differs from the qualified managed runtime')
    distribution = importlib.metadata.distribution('imageio-ffmpeg')
    if distribution.version != VERSION:
        raise ValueError('E5 requires the prescribed imageio-ffmpeg wheel version')
    entries = [entry for entry in distribution.files or [] if str(entry) == RELATIVE]
    if len(entries) != 1:
        raise ValueError('managed imageio-ffmpeg wheel binary is missing or ambiguous')
    path = Path(distribution.locate_file(entries[0]))
    if path.is_symlink() or not path.resolve().is_relative_to(managed):
        raise ValueError('imageio-ffmpeg binary is outside the managed environment')
    rows = list(csv.reader(io.StringIO(distribution.read_text('RECORD') or '')))
    records = [row for row in rows if row and row[0] == RELATIVE]
    if len(records) != 1 or len(records[0]) != 3 or not records[0][1].startswith('sha256='):
        raise ValueError('imageio-ffmpeg binary lacks a unique SHA-256 wheel RECORD')
    record = file_record(path)
    encoded = base64.urlsafe_b64encode(bytes.fromhex(record['sha256'])).decode().rstrip('=')
    if records[0][1] != 'sha256=' + encoded or records[0][2] != str(record['bytes']):
        raise ValueError('imageio-ffmpeg binary differs from its wheel RECORD')
    if not os.access(path, os.X_OK):
        raise ValueError('managed imageio-ffmpeg binary is not executable')
    result = dict(distribution='imageio-ffmpeg', distribution_version=VERSION,
                  executable=record, wheel_record_sha256=record['sha256'], subprocess_probe=False)
    if expected is not None:
        verify_record(expected['executable'])
        if result != expected:
            raise ValueError('E5 FFmpeg binding differs from qualified setup evidence')
    os.environ['IMAGEIO_FFMPEG_EXE'] = record['path']
    # A caller's absolute FFMPEG_BINARY causes MoviePy to probe again. Force
    # its imageio branch, which returns the verified path without executing it.
    os.environ['FFMPEG_BINARY'] = 'ffmpeg-imageio'
    return result


def bind_runtime(runtime):
    """Recheck the setup evidence before a D2 worker imports the pinned API."""
    from .files import read_json
    imports = read_json(verify_record(runtime['imports'])['path'])
    if (imports.get('environment') != 'E5' or imports.get('status') != 'complete'
            or imports.get('offline') is not True or imports.get('forwards') != 0
            or imports.get('cuda_context_initialized') is not False or not imports.get('ffmpeg')):
        raise ValueError('D2 runtime lacks qualified E5 FFmpeg binding')
    expected = imports['ffmpeg']
    inventory = read_json(verify_record(runtime['inventory'])['path'])
    if inventory.get('executable') != runtime['python']:
        raise ValueError('E5 inventory differs from the qualified managed interpreter')
    packages = [package for package in inventory.get('packages', [])
                if package.get('name', '').lower().replace('_', '-') == 'imageio-ffmpeg']
    if (len(packages) != 1 or packages[0].get('version') != VERSION
            or expected.get('executable') not in packages[0].get('files', [])):
        raise ValueError('E5 FFmpeg binding differs from the qualified package inventory')
    return bind(expected, environment=Path(runtime['python']).parent.parent)

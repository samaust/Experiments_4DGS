"""Explicit paths and immutable, non-pickled benchmark evidence."""
import hashlib
import json
import os
from pathlib import Path


def safe_path(path):
    path = Path(path)
    # Check both spellings, so a symlink cannot expose the forbidden directory.
    if 'prompts' in path.parts or 'prompts' in path.resolve().parts:
        raise ValueError('prompts access is prohibited')
    return path


def digest(path):
    with safe_path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False)


def object_hash(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def read_json(path):
    return json.loads(safe_path(path).read_text())


def write_json(path, value):
    path = safe_path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x') as stream:
        stream.write(json.dumps(value, indent=2, allow_nan=False) + '\n')
        stream.flush()
        os.fsync(stream.fileno())


def file_record(path, expected=None):
    path = safe_path(path).resolve()
    actual = digest(path)
    if expected is not None and actual != expected:
        raise ValueError(f'changed file: {path}; expected {expected}, got {actual}')
    return dict(path=str(path), sha256=actual, bytes=path.stat().st_size)


def verify_record(record):
    return file_record(record['path'], record['sha256'])


def load_array(record):
    import numpy as np
    verify_record(record)
    return np.load(safe_path(record['path']), allow_pickle=False)

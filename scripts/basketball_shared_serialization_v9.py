"""Finite, deterministic NumPy-aware JSON serialization before fresh atomic publication."""
import gzip
import json
import os
from pathlib import Path
import tempfile
import numpy as np


def canonical(value):
    if isinstance(value,np.ndarray):return value.tolist()
    if isinstance(value,np.generic):return value.item()
    raise TypeError('unsupported JSON type '+type(value).__name__)


def compressed_write(path,value):
    path=Path(path)
    if path.exists():raise FileExistsError('fresh artifact required '+str(path))
    # Validate/encode first: serialization failure cannot publish an empty gzip artifact.
    payload=gzip.compress(json.dumps(value,allow_nan=False,default=canonical,separators=(',',':')).encode(),mtime=0)
    path.parent.mkdir(parents=True,exist_ok=True)
    fd,temporary=tempfile.mkstemp(prefix='.v9-',dir=path.parent)
    try:
        with os.fdopen(fd,'wb') as f:f.write(payload);f.flush();os.fsync(f.fileno())
        os.link(temporary,path) # Atomic and never replaces an existing artifact.
    finally:
        Path(temporary).unlink(missing_ok=True)

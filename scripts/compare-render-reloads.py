#!/usr/bin/env python3
"""Strictly compare complete PNG sequences from independent model reloads."""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image


def compare(first, second, expected_count):
    first, second = Path(first), Path(second)
    names = {p.name for p in first.glob('*.png')}
    other = {p.name for p in second.glob('*.png')}
    if expected_count <= 0 or len(names) != expected_count or names != other:
        raise ValueError('PNG filename sets must match exactly and have the expected nonzero count')
    rows = []
    total_error = total_values = maximum = 0
    dimensions = None
    for name in sorted(names):
        paths = [first/name, second/name]
        hashes = [hashlib.sha256(p.read_bytes()).hexdigest() for p in paths]
        arrays = []
        for path in paths:
            with Image.open(path) as im:
                if im.mode != 'RGB':
                    raise ValueError(f'expected RGB image: {path}')
                arrays.append(np.asarray(im, dtype=np.int16))
        a, b = arrays
        if a.shape != b.shape or (dimensions is not None and list(a.shape) != dimensions):
            raise ValueError('image dimensions differ within or between reloads: '+name)
        dimensions = list(a.shape)
        difference = np.abs(a-b)
        error = int(difference.sum(dtype=np.int64))
        peak = int(difference.max())
        total_error += error
        total_values += difference.size
        maximum = max(maximum, peak)
        rows.append(dict(filename=name, first_sha256=hashes[0], second_sha256=hashes[1],
                         byte_exact=hashes[0] == hashes[1], pixel_exact=peak == 0,
                         max_abs_error_0_255=peak, mean_abs_error_0_255=error/difference.size))
    return dict(count=len(rows), dimensions_hwc=dimensions,
                byte_exact_count=sum(r['byte_exact'] for r in rows),
                pixel_exact_count=sum(r['pixel_exact'] for r in rows),
                max_abs_error_0_255=maximum, mean_abs_error_0_255=total_error/total_values,
                first=str(first.resolve()), second=str(second.resolve()), per_frame=rows,
                note='Quantized RGB PNG comparison, not floating-point renderer-state equality.')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--first', type=Path, required=True)
    p.add_argument('--second', type=Path, required=True)
    p.add_argument('--expected-count', type=int, required=True)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    if a.output.exists():
        p.error('refusing to overwrite output')
    try:
        report = compare(a.first, a.second, a.expected_count)
    except ValueError as error:
        p.error(str(error))
    with a.output.open('x') as stream:
        stream.write(json.dumps(report, indent=2)+'\n')
    print(json.dumps({k: v for k, v in report.items() if k != 'per_frame'}, indent=2))


if __name__ == '__main__':
    main()

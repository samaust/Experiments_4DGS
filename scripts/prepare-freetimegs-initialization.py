#!/usr/bin/env python3
"""Assemble audited training-only clouds into normalized-time FreeTimeGS inputs."""
import argparse
import json
from pathlib import Path

import numpy as np

from freetimegs_scene import FreeTimeSelfCapScene
from freetimegs_initialization import assemble_initialization, digest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', type=Path, required=True)
    parser.add_argument('--checkout', type=Path, default=Path('.local/FreeTimeGsVanilla'))
    parser.add_argument('--cloud', nargs=2, action='append', metavar=('FRAME', 'DIRECTORY'), required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--dense-edgs', action='store_true', help='Require audited EDGS dense NPZ clouds')
    args = parser.parse_args()
    clouds = {int(frame): Path(path) for frame, path in args.cloud}
    if len(clouds) != len(args.cloud):
        parser.error('duplicate frame argument')
    if args.output.exists():
        parser.error('choose a new output directory')
    arrays, report = assemble_initialization(args.checkout, FreeTimeSelfCapScene(args.manifest), clouds,
                                             dense=args.dense_edgs)
    args.output.mkdir(parents=True)
    archive = args.output / 'initialization.npz'
    np.savez(archive, **arrays)
    report.update(status='prepared', archive_sha256=digest(archive))
    (args.output / 'result.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({k: report[k] for k in ('status', 'points', 'valid_velocity_points', 'archive_sha256')}))


if __name__ == '__main__':
    main()

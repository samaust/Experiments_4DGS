#!/usr/bin/env python3
"""Compare completed matched-profile STG/ATGS evaluations without inventing rankings."""
import argparse
import json
import math
from pathlib import Path


def read_evaluation(directory):
    directory = Path(directory)
    evaluation = json.loads((directory/'evaluation.json').read_text())
    metrics = json.loads((directory/'metrics.json').read_text())
    render = json.loads((directory/'reload-a/render.json').read_text())
    if evaluation['status'] != 'completed':
        raise ValueError('evaluation is not complete')
    identity_fields = ('bundle', 'runtime') if evaluation['model'] == 'atgs' else ('checkpoint_sha256',)
    for key in ('model', 'iteration', 'manifest_sha256', 'incomplete_training', *identity_fields):
        if evaluation[key] != render[key]:
            raise ValueError('evaluation/render metadata mismatch: '+key)
    if evaluation['metrics'] != metrics['aggregate']:
        raise ValueError('evaluation/metrics aggregate mismatch')
    rows = metrics['per_frame']
    frames = [row['frame'] for row in rows]
    expected = [f'{row["frame_id"]:06d}' for row in render['frames']]
    if (not frames or len(set(frames)) != len(frames) or len(set(expected)) != len(expected) or
            set(frames) != set(expected) or metrics['count'] != len(frames)):
        raise ValueError('metric frames must match rendered frames exactly without duplicates')
    for row in [metrics['aggregate'], *rows]:
        for name in ('psnr', 'ssim', 'lpips_alex'):
            value = row[name]
            if value == 'Infinity' and name == 'psnr':
                continue
            if isinstance(value, bool) or not isinstance(value, (float, int)) or not math.isfinite(value):
                raise ValueError('invalid metric value: '+name)
    return evaluation, metrics, render


def difference(first, second):
    # Infinite PSNR subtraction is not a meaningful finite delta.
    return {key: None if 'Infinity' in (first[key], second[key]) else second[key]-first[key]
            for key in ('psnr', 'ssim', 'lpips_alex')}


def compare(first, second):
    a, am, ar = read_evaluation(first)
    b, bm, br = read_evaluation(second)
    if a['manifest_sha256'] != b['manifest_sha256'] or am['protocol'] != bm['protocol']:
        raise ValueError('different manifests or metric protocols')
    # The same manifest must be rendered at the same camera/time samples.
    samples = lambda r: [(f['camera'], f['frame_id'], f['normalized_time']) for f in r['frames']]
    if sorted(samples(ar)) != sorted(samples(br)) or ar['sweep'] != br['sweep']:
        raise ValueError('different rendered camera/time samples or sweep')
    b_rows = {r['frame']: r for r in bm['per_frame']}
    if {r['frame'] for r in am['per_frame']} != set(b_rows):
        raise ValueError('different metric frame sets')
    def summary(directory, report):
        return dict(directory=str(Path(directory).resolve()), model=report['model'],
            iteration=report['iteration'], incomplete_training=report['incomplete_training'],
            metrics=report['metrics'], checkpoint_sha256=report.get('checkpoint_sha256'),
            checkpoint_bundle=report.get('bundle'),
            checkpoint_bytes=report['checkpoint_bytes'], benchmark=report['benchmark'])
    return dict(first=summary(first, a), second=summary(second, b),
        manifest_sha256=a['manifest_sha256'], protocol=am['protocol'], count=am['count'],
        equal_iterations=a['iteration'] == b['iteration'],
        delta_second_minus_first=difference(am['aggregate'], bm['aggregate']),
        per_frame=[dict(frame=r['frame'], delta_second_minus_first=difference(r, b_rows[r['frame']]))
                   for r in am['per_frame']],
        note='Arithmetic differences only; equal steps do not imply equal training time. '
             'Higher PSNR/SSIM and lower LPIPS are better. Null deltas involve infinite PSNR. '
             'Incomplete runs do not establish final-budget rankings.')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--first', type=Path, required=True)
    p.add_argument('--second', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    if a.output.exists():
        p.error('refusing to overwrite output')
    try:
        report = compare(a.first, a.second)
    except (ValueError, KeyError) as error:
        p.error(str(error))
    with a.output.open('x') as stream:
        stream.write(json.dumps(report, indent=2, allow_nan=False)+'\n')
    print(json.dumps({k: v for k, v in report.items() if k != 'per_frame'}, indent=2))


if __name__ == '__main__':
    main()

"""Compare complete native endpoint states from continuous and split resumes."""
import argparse
from pathlib import Path

import torch

from basketball_study import digest, write_new


def differences(left, right, key='state'):
    if isinstance(left, torch.Tensor):
        return [] if isinstance(right, torch.Tensor) and left.dtype == right.dtype and left.shape == right.shape and torch.equal(left, right) else [key]
    if type(left) is not type(right):
        return [key + ':type']
    if isinstance(left, dict):
        if left.keys() != right.keys():
            return [key + ':keys']
        return [d for k in left for d in differences(left[k], right[k], key+'.'+str(k))]
    if isinstance(left, (list, tuple)):
        if len(left) != len(right):
            return [key + ':length']
        return [d for i, (a, b) in enumerate(zip(left, right)) for d in differences(a, b, key+'.'+str(i))]
    return [] if left == right else [key]


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--continuous', type=Path, required=True)
    p.add_argument('--split', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    left = torch.load(a.continuous, map_location='cpu', weights_only=True)
    right = torch.load(a.split, map_location='cpu', weights_only=True)
    changed = differences(left, right)
    write_new(a.output, dict(schema='basketball-study-resume-validation/v1', passed=not changed,
        continuous_sha256=digest(a.continuous), split_sha256=digest(a.split),
        iteration=left['iteration'], differences=changed,
        checked='complete saved parameters, optimizers, schedulers, RNG, sampler/loop, method-specific state and provenance'))
    if changed:
        raise SystemExit('resume mismatch: '+', '.join(changed[:20]))


if __name__ == '__main__':
    main()

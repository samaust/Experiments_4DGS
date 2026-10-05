"""Build the hash-bound Triton cuda_utils helper cache with the setup interpreter; CPU only."""
import argparse

from vipe_benchmark.triton_helper_cache import build


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cache', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    print(build(args.cache, args.output))

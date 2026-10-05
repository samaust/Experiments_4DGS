"""Build the hash-bound Triton cuda_utils helper cache with the setup interpreter; CPU only."""
import argparse

from vipe_benchmark.triton_helper_cache import build, build_v2


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cache', required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--v2', action='store_true', help='Triton >= 3.3: build via CudaUtils with a fixed libcuda path')
    args = parser.parse_args()
    print((build_v2 if args.v2 else build)(args.cache, args.output))

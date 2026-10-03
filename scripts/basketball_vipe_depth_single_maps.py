"""Execute a reserved D5/D6/D8 native PointMap workload."""
import argparse

from vipe_benchmark.depth_single_run import run_maps
from vipe_benchmark.files import read_json


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--request', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    run_maps(read_json(args.request), args.output, request_path=args.request)


if __name__ == '__main__':
    main()

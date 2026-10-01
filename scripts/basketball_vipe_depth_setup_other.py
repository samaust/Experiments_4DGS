"""Run a single reserved D8 or D11 native asset setup."""

import argparse

from vipe_benchmark.depth_setup_other import run_setup
from vipe_benchmark.files import read_json


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--request', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    run_setup(read_json(args.request), args.output, request_path=args.request)


if __name__ == '__main__':
    main()

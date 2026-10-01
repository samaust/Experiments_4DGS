"""Execute one reserved native D7 map request."""
import argparse

from vipe_benchmark.depth_d7_run import run_d7_maps
from vipe_benchmark.files import read_json


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--request', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    run_d7_maps(read_json(args.request), args.output, request_path=args.request)


if __name__ == '__main__':
    main()

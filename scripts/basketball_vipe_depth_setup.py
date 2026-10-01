"""Execute one approved Plan 069 D7 setup transaction."""

import argparse

from vipe_benchmark.depth_setup import run_d7_setup
from vipe_benchmark.files import read_json


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--request', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    request = read_json(args.request)
    if request.get('record_kind') != 'actual':
        raise ValueError('native setup worker requires an actual reserved request')
    run_d7_setup(request, args.output, request_path=args.request)


if __name__ == '__main__':
    main()

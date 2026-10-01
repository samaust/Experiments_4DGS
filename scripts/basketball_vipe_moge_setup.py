"""Execute one ledger-supervised, approved D5/D6 MoGe setup request."""

import argparse
from pathlib import Path

from vipe_benchmark.files import read_json
from vipe_benchmark.moge_setup import run_moge_setup


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--request', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    request = read_json(args.request)
    if request.get('record_kind') != 'actual':
        raise ValueError('CLI only accepts an actual ledger-bound request')
    run_moge_setup(request, args.output, request_path=args.request)


if __name__ == '__main__':
    main()

"""Execute a reserved Plan 069 native video setup."""

import argparse

from vipe_benchmark.files import read_json
from vipe_benchmark.video_setup import run_video_setup


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--request', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    request = read_json(args.request)
    if request.get('record_kind') != 'actual':
        raise ValueError('actual reserved video setup request required')
    run_video_setup(request, args.output, request_path=args.request)


if __name__ == '__main__':
    main()

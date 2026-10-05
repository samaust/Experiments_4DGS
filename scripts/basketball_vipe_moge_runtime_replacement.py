"""Execute the separately reserved D6 runtime replacement; no dispatch authority."""
import argparse
from vipe_benchmark.files import read_json


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--request', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    request = read_json(args.request)
    if request.get('record_kind') != 'actual':
        raise ValueError('actual explicitly reserved runtime replacement request required')
    from vipe_benchmark.depth_moge_runtime_replacement import run_runtime_replacement
    run_runtime_replacement(request, args.output, request_path=args.request)


if __name__ == '__main__':
    main()

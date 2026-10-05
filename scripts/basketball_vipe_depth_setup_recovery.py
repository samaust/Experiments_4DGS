"""Execute a separately reserved native-depth setup recovery; no dispatch authority."""
import argparse
from vipe_benchmark.files import read_json


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--request', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    request = read_json(args.request)
    if request.get('record_kind') != 'actual':
        raise ValueError('actual explicitly reserved recovery request required')
    from vipe_benchmark.depth_setup_other import run_setup_recovery
    run_setup_recovery(request, args.output, request_path=args.request)


if __name__ == '__main__':
    main()

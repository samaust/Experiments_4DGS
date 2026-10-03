"""Capture CPU-only installed dependency evidence for a prepared video model."""

import argparse

from vipe_benchmark.video_native import write_dependency_inventory


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--candidate', required=True, choices=('D9', 'D10'))
    parser.add_argument('--setup-result', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    from vipe_benchmark.files import file_record
    write_dependency_inventory(args.candidate,
                               file_record(args.setup_result), args.output)


if __name__ == '__main__':
    main()

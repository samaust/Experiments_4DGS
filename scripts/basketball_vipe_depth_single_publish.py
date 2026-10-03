"""Publish matched D5/D6/D8 clips from an accepted finished map result."""
import argparse

from vipe_benchmark.depth_single_publish import publish_after_gpu
from vipe_benchmark.files import file_record


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--result', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    publish_after_gpu(file_record(args.result), args.output)


if __name__ == '__main__':
    main()

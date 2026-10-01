"""Publish D7 native maps as matched qualitative clips after GPU completion."""
import argparse
from pathlib import Path

from vipe_benchmark.depth_d7_publish import publish_d7_after_gpu
from vipe_benchmark.files import file_record


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--map-result', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    publish_d7_after_gpu(file_record(args.map_result), Path(args.output))


if __name__ == '__main__':
    main()

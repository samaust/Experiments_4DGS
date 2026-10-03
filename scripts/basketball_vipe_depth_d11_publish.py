"""Publish matched D11 relative-log clips after its accepted GPU ledger finish."""
import argparse
from pathlib import Path

from vipe_benchmark.depth_single_publish import publish_after_gpu
from vipe_benchmark.files import file_record, read_json


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--map-result', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    record = file_record(args.map_result)
    if read_json(record['path']).get('candidate') != 'D11':
        raise ValueError('D11 publisher requires exact candidate result')
    publish_after_gpu(record, Path(args.output))


if __name__ == '__main__':
    main()

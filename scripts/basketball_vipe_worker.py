"""Explicit file-based Plan 031 CPU workers; no inference during preparation."""
import argparse
from pathlib import Path

from vipe_benchmark.config import load
from vipe_benchmark.files import read_json, verify_record


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path, required=True)
    parser.add_argument('--request', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--operation', choices=['prepare', 'annotations'], required=True)
    args = parser.parse_args()
    config = load(args.config)
    request = read_json(args.request)
    verify_record(request['configuration'])
    if Path(request['configuration']['path']).resolve() != args.config.resolve():
        raise ValueError('worker configuration differs from its frozen request')
    if args.operation == 'prepare':
        from vipe_benchmark.prepare import prepare
        verify_record(request['exposure'])
        prepare(args.output, config, exposure=request['exposure'])
    else:
        from vipe_benchmark.annotations import validate
        from vipe_benchmark.files import file_record, write_json
        verify_record(request['inputs'])
        verify_record(request['annotations'])
        result = validate(read_json(request['annotations']['path']), read_json(request['inputs']['path']), config)
        args.output.mkdir(parents=True, exist_ok=False)
        write_json(args.output / 'annotations.json', result)
        write_json(args.output / 'result.json', dict(status='complete', annotations=file_record(args.output / 'annotations.json')))


if __name__ == '__main__':
    main()

#!/usr/bin/env python3
"""Export and import the extended depth review and freeze its metric choice."""
import argparse
import json
from pathlib import Path

from vipe_benchmark.files import file_record, write_json


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    for name in ('blank-review', 'import-review', 'decision'):
        command = commands.add_parser(name)
        command.add_argument('input', type=Path)
        command.add_argument('output', type=Path)
        if name == 'import-review':
            command.add_argument('--package', type=Path, required=True)
    args = parser.parse_args(argv)
    from vipe_benchmark.depth_review import blank_review, import_review, freeze_decision
    record = file_record(args.input)
    if args.command == 'blank-review':
        result = blank_review(record)
        write_json(args.output, result)
    elif args.command == 'import-review':
        result = import_review(file_record(args.package), record, args.output)
    else:
        result = freeze_decision(record, args.output)
    print(json.dumps(result, indent=2, allow_nan=False))


if __name__ == '__main__':
    main()

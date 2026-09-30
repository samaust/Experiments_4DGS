#!/usr/bin/env python3
"""Explicit qualitative preparation, publication and actual human review CLI."""
import argparse
import json
from pathlib import Path

from vipe_benchmark.files import file_record, read_json, write_json


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    commands=parser.add_subparsers(dest='command',required=True)
    for name in ('generate','publish','blank-review','import-review','decision','report'):
        command=commands.add_parser(name)
        command.add_argument('input',type=Path)
        command.add_argument('output',type=Path)
        if name=='import-review': command.add_argument('--package',type=Path,required=True)
        if name=='decision':
            command.add_argument('--engineering',type=Path,required=True)
            command.add_argument('--choice',type=Path)
        if name=='report': command.add_argument('--decision',type=Path,required=True)
    args=parser.parse_args(argv)
    if args.command=='generate':
        from vipe_benchmark.qualitative_generation import generate
        request=read_json(args.input)
        if request['record_kind']!='actual': parser.error('CLI only generates actual packages')
        result=generate(request,args.output)
    elif args.command=='publish':
        from vipe_benchmark.qualitative_generation import publish_generation
        manifest=read_json(args.input)
        if manifest['record_kind']!='actual': parser.error('CLI only publishes actual packages')
        result=publish_generation(file_record(args.input),args.output)
    else:
        from vipe_benchmark.qualitative_review import blank_review, import_review, freeze_decision, build_report
        record=file_record(args.input)
        if args.command=='blank-review':
            result=blank_review(record);write_json(args.output,result)
        elif args.command=='import-review': result=import_review(file_record(args.package),record,args.output)
        elif args.command=='decision':
            result=freeze_decision(record,read_json(args.engineering),args.output,
                choice=read_json(args.choice) if args.choice else None)
        else: result=build_report(record,file_record(args.decision),args.output)
    print(json.dumps(result,indent=2,allow_nan=False))


if __name__=='__main__': main()

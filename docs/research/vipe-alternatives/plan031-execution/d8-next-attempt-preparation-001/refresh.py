"""Write metadata-only D8 source-review input; never grant execution approval."""
import argparse
from pathlib import Path
import subprocess
import sys
import time


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--run', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    started = time.monotonic()
    root = args.root.absolute()
    run = args.run.absolute()
    output = args.output.absolute()
    for path in (root, run, output):
        if 'prompts' in path.parts or 'prompts' in path.resolve().parts or path != path.resolve():
            raise ValueError('absolute paths without symlinks or prompts required')
    if output.exists():
        raise FileExistsError('immutable preparation output already exists')
    sys.path.insert(0, str(root / 'scripts'))
    from vipe_benchmark.depth_admission import local_source_records
    from vipe_benchmark.depth_authorization import execution_authorization
    from vipe_benchmark.depth_native_runtime import recipe
    from vipe_benchmark.files import file_record, write_json
    review, authorization, proposal, _ = execution_authorization('D8')
    environment = recipe('D8', run)
    sources = local_source_records('D8')
    commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=root, text=True).strip()
    output.mkdir(parents=True)
    write_json(output / 'environment.json', environment)
    write_json(output / 'source-review-input.json', dict(
        schema='plan069-depth-source-review-input/v1', candidate='D8',
        status='awaiting_independent_review', canonical_commit=commit,
        source_revision=proposal['candidate_config']['code']['revision'],
        profile_inventory=proposal['profile_inventory'], local_sources=sources,
        review=review, authorization=authorization,
        environment=file_record(output / 'environment.json'),
        source_config=proposal['candidate_config'], allocation=proposal['allocation']))
    write_json(output / 'measurement.json', dict(
        schema='plan069-depth-preparation-measurement/v1', candidate='D8',
        elapsed_seconds=time.monotonic() - started,
        timing_scope='refresh process entry through source input publication',
        ledger_charged=False, no_setup_or_model_execution=True,
        environment=file_record(output / 'environment.json'),
        source_review_input=file_record(output / 'source-review-input.json')))


if __name__ == '__main__':
    main()

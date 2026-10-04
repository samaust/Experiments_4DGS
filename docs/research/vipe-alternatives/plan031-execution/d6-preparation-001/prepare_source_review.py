"""Create a D6 source-review draft; independent review must pass it before use."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys


def record(path):
    path = Path(path).absolute()
    if 'prompts' in path.parts or 'prompts' in path.resolve().parts:
        raise ValueError('prompts prohibited')
    return dict(path=str(path), sha256=hashlib.sha256(path.read_bytes()).hexdigest(), bytes=path.stat().st_size)


def prepare(root, output, setup=None):
    root = Path(root).absolute()
    if root != root.resolve():
        raise ValueError('canonical checkout must not traverse symlinks')
    sys.path.insert(0, str(root / 'scripts'))
    from vipe_benchmark.depth_admission import local_source_records
    from vipe_benchmark.depth_authorization import execution_authorization
    candidate = 'D6'
    review, authorization, proposal, _ = execution_authorization(candidate)
    previous = root / 'docs/research/vipe-alternatives/plan031-execution/depth-D6-source-review-003.json'
    draft = json.loads(previous.read_text())
    draft.update(status='review', reviewer='', independent_reviews={},
        independent_review_report=None,
        root_source_commit=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=root, text=True).strip(),
        local_sources=local_source_records(candidate),
        profile_inventory=proposal['profile_inventory'],
        setup_sources=[record(item['path']) for item in draft['setup_sources']],
        runtime_recipe=record(root / 'docs/specs/plan031-execution/moge-runtime-recipes-001/D6-runtime-environment.json'),
        review=review, authorization=authorization,
        qualification_scope='Draft current-source contracts only; no model qualification or execution authority is granted.')
    if setup is not None:
        accepted = json.loads(Path(setup).read_text())
        if accepted.get('candidate') != candidate or accepted.get('status') != 'complete' or accepted.get('record_kind') != 'actual':
            raise ValueError('actual accepted D6 setup required')
        draft.update(source_archive=accepted['source_archive'], source_files=accepted['source_tree'])
        if record(draft['source_archive']['path']) != draft['source_archive']:
            raise ValueError('source archive changed')
        for item in draft['source_files']:
            if record(item['record']['path']) != item['record']:
                raise ValueError('accepted source file changed')
    else:
        draft.pop('source_archive', None)
        draft.pop('source_files', None)
    with Path(output).open('x') as stream:
        json.dump(draft, stream, indent=2)
        stream.write('\n')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--setup')
    args = parser.parse_args()
    prepare(args.root, args.output, args.setup)

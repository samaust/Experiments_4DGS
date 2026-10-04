"""Read-only D6 post-setup audit; never read model weights or partial outputs."""
import argparse
import json
from pathlib import Path
from prepare_source_review import record


def read(path):
    return json.loads(Path(path).read_text())


def audit(root, run, draft_path):
    root, run = Path(root).absolute(), Path(run).absolute()
    draft = read(draft_path)
    setup_path = run / 'jobs/plan069-D6-setup-001/result.json'
    setup = read(setup_path)
    if setup.get('candidate') != 'D6' or setup.get('record_kind') != 'actual' or setup.get('status') != 'complete':
        raise ValueError('complete actual D6 setup required; partial output must not be reviewed')
    dispatch = read(root / 'docs/research/vipe-alternatives/plan031-20260913T032700Z/plan069-D6-setup-001.json')
    if dispatch.get('status') != 'complete' or dispatch.get('result') != record(setup_path):
        raise ValueError('accepted supervised setup record required')
    review = read(draft['review']['path'])
    proposal = next(item for item in review['proposals'] if item['candidate'] == 'D6')
    assets_record = proposal['required_assets']
    if record(assets_record['path']) != assets_record:
        raise ValueError('required asset inventory changed')
    asset = read(assets_record['path'])['candidates']['D6']['files'][0]
    checkpoint = setup['checkpoint']
    if checkpoint['sha256'] != asset['lfs_sha256'] or checkpoint['bytes'] != asset['bytes']:
        raise ValueError('accepted checkpoint metadata differs from pinned D6 weights')
    if setup.get('source_revision') != proposal['candidate_config']['code']['revision'] or setup.get('weight_revision') != proposal['candidate_config']['weights']['revision']:
        raise ValueError('accepted source/weights revision differs from D6 proposal')
    previous = read(run / 'jobs/plan069-D5-setup-001/result.json')
    if checkpoint['sha256'] == previous['checkpoint']['sha256']:
        raise ValueError('D5 weights cannot be reused as D6')
    if setup['source_archive']['sha256'] != previous['source_archive']['sha256']:
        raise ValueError('D5/D6 pinned common source archive differs')
    def tree_identity(tree):
        return [(item['relative_path'], item['record']['sha256'], item['record']['bytes']) for item in tree]
    if len(setup['source_tree']) != 123 or tree_identity(setup['source_tree']) != tree_identity(previous['source_tree']):
        raise ValueError('exact pinned 123-source tree differs')
    if draft.get('candidate') != 'D6' or draft.get('source_archive') != setup['source_archive'] or draft.get('source_files') != setup['source_tree']:
        raise ValueError('post-setup draft archive/tree differs')
    for item in draft['local_sources'] + draft['setup_sources']:
        if record(item['path']) != item:
            raise ValueError('current helper changed')
    if record(setup['source_archive']['path']) != setup['source_archive']:
        raise ValueError('accepted archive changed')
    for item in setup['source_tree']:
        if record(item['record']['path']) != item['record']:
            raise ValueError('accepted source tree changed')
    return dict(status='passed', candidate='D6', source_count=123,
        current_helpers=len(draft['local_sources']), setup_helpers=len(draft['setup_sources']),
        checkpoint_metadata=checkpoint, checkpoint_content_read=False,
        accepted_setup=record(setup_path), draft=record(draft_path),
        scope='Read-only accepted setup metadata, archive/source files and canonical helpers; not runtime qualification')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('root', 'run', 'draft'):
        parser.add_argument('--' + name, required=True)
    args = parser.parse_args()
    print(json.dumps(audit(args.root, args.run, args.draft), indent=2))

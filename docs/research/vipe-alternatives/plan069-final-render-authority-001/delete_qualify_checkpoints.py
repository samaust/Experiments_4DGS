"""Delete the QUALIFY arm's two checkpoint files after recording their hashes (user choice, 2026-10-06).

They duplicate qualification-only state. The native qualification binds only its
result, supervision and timing records, so `verify` must still pass afterwards.
This frees space for QF-N2 under the 260 GiB artifact cap.
"""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT/'scripts'))
from vipe_benchmark.files import file_record, write_json  # noqa: E402
from vipe_benchmark.final_render_native_qualification import verify  # noqa: E402
from vipe_benchmark.ledger import Ledger  # noqa: E402
from vipe_benchmark.config import load  # noqa: E402

RUN = Path('/home/auss/git_repos/samaust/Experiments_4DGS/.local/vipe-alternatives/plan031-20260913T032700Z')
ARM = RUN/'final-render/plan069-final-render-D8-qualification-001/QF-B'
HERE = Path(__file__).resolve().parent
QUALIFICATION = HERE/'qualify-20261006T043836Z/qualification/qualification.json'
PRODUCTION = ROOT/'docs/research/vipe-alternatives/plan069-final-render-review-002/production/request.json'


def check():
    ledger = Ledger(RUN/'ledger.jsonl', dict(load(), new_download_gib_limit=110, new_artifact_disk_gib_limit=260))
    events = ledger.events()
    return verify(file_record(QUALIFICATION), file_record(PRODUCTION), events, ledger.states(events))['status']


def main():
    targets = [ARM/'train/checkpoint-005000.pt', ARM/'render/restored-checkpoint.pt']
    before = check()
    records = [file_record(path) for path in targets]
    write_json(HERE/'qualify-checkpoint-deletion-001.json', dict(schema='plan069-final-render-qualify-deletion/v1',
        reason='Free artifact space for QF-N2 under the approved 260 GiB cap (user choice, 2026-10-06).',
        deleted=records, freed_bytes=sum(r['bytes'] for r in records), qualification=file_record(QUALIFICATION),
        verify_before=before))
    for path in targets:
        path.unlink()
    print('verify after deletion:', check(), 'freed GiB:', round(sum(r['bytes'] for r in records)/2**30, 2))


if __name__ == '__main__':
    main()

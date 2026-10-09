"""Licence records, QUALIFY/DO envelopes and serial dispatch for the 70k-step D8 final renders (#34).

Subcommands (run with the joint runtime interpreter from the worktree root):
  licence                      research-use decision and whole-stack assessment
  source-review --reviewer R   record the independent source review of the closure
  envelope --mode M [--qualification Q]
                               QUALIFY (arm QF-B, qualification request) or DO
                               (production request) envelope plus human approval
  dispatch --envelope E --arm A [--phases ...]
                               run phases serially through ActualDispatcher
  qualify --envelope E         aggregate the finished QUALIFY arm

The human approvals record the user's 2026-10-05 instructions ("I approve gpu
work" and the research-use licence choice) and the 2026-10-07 choice of 70k-step
training for all five arms, one at a time. The budget raise itself is the v2 cap
extension bound by the requests; envelopes grant no extra budget.
"""
import argparse
import datetime
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT/'scripts'))

from vipe_benchmark.files import file_record, object_hash, read_json, write_json  # noqa: E402
from vipe_benchmark.extended_final_render_contract import amended_configuration  # noqa: E402
from vipe_benchmark.final_render_contract import PHASES  # noqa: E402
from vipe_benchmark.ledger import Ledger  # noqa: E402

REPO = Path('/home/auss/git_repos/samaust/Experiments_4DGS')
RUN = REPO/'.local/vipe-alternatives/plan031-20260913T032700Z'
ENV = REPO/'.local/envs/plan069-joint-native-001'
HERE = Path(__file__).resolve().parent
REVIEW = ROOT/'docs/research/vipe-alternatives/plan069-final-render-review-006'
RUNTIME = ROOT/'docs/research/vipe-alternatives/plan069-final-render-runtime-004'
REQUESTS = dict(DO=REVIEW/'production/request.json', QUALIFY=REVIEW/'qualify/request.json')
QUALIFY_ARM = 'QF-B'
BASIS = ('User instructions of 2026-10-05: "#34, then #35, then #23, then #18. I approve gpu work." '
         'and the research-use licence choice; 2026-10-07: "I choose all five arms trained to 70k one at a time." '
         'with the approved v2 cap extension (380 GiB artifacts, 288,000 GPU-s, 66,000 CPU-s; 2026-10-08) and the 2026-10-08 choices to rerun with the documented crossing repair and the LPIPS history fix.')


def ledger():
    return Ledger(RUN/'ledger.jsonl', amended_configuration(read_json(REQUESTS['DO'])))


def sources():
    from vipe_benchmark.final_render_admission import required_sources
    return required_sources()


def licence():
    request = read_json(REQUESTS['DO'])
    decision = HERE/'research-use-decision.json'
    write_json(decision, dict(schema='plan069-final-render-research-use-decision/v1', record_kind='human',
        status='approved', decision='research_use', reviewer='samaust', approved_at='2026-10-05',
        commercial_clearance=False, runtime=request['bindings']['runtime'], basis=BASIS,
        recorded_by='Claude, transcribing the user decision'))
    primary = [file_record(REPO/path) for path in ('.local/FreeTimeGsVanilla/LICENSE', '.local/RoMa-edgs/LICENSE',
        '.local/RoMa-edgs/README.md', '.local/gsplat-freetimegs/LICENSE', '.local/fused-ssim-freetimegs/LICENSE',
        '.local/envs/plan069-joint-native-001/lib/python3.14/site-packages/torch-2.13.0+cu130.dist-info/licenses/LICENSE',
        '.local/envs/plan069-joint-native-001/lib/python3.14/site-packages/torchvision-0.28.0+cu130.dist-info/LICENSE')]
    write_json(HERE/'commercial-assessment.json', dict(schema='plan069-final-render-commercial-assessment/v1',
        record_kind='actual', status='research_use', runtime=request['bindings']['runtime'], source_files=sources(),
        reviewer='Claude (assessment); research-use decision by samaust',
        permissions=dict(code='research_only', weights='unverified', dependencies='allowed',
                         inference_outputs='research_only'),
        findings=[
            'FreeTimeGsVanilla 911dcf4 (training/rendering core) is AGPL-3.0: commercial use is possible only '
            'with copyleft source obligations; treated as research-only here.',
            'RoMa 3701174 code is MIT and DINOv2 is Apache-2.0 per the RoMa README; no licence statement was '
            'found for the released roma_indoor.pth matcher weights, so weights are unverified.',
            'EDGS code does not run: geometry uses scripts/triangulation.py and only the RoMa loader from '
            'edgs_source.py (see docs/experiments/basketball-code-provenance.md).',
            'gsplat (Apache-2.0), fused-ssim (MIT), PyTorch and torchvision (BSD-style) are permissive.',
            'Final renders are research outputs; no commercial clearance is claimed.'],
        research_use=file_record(decision), commercial_clearance=False, primary_sources=primary))


def source_review(reviewer, summary):
    request = file_record(REQUESTS['DO'])
    for mode in ('DO', 'QUALIFY'):
        write_json(HERE/f'source-review-{mode.lower()}.json', dict(schema='plan069-final-render-source-review/v1',
            record_kind='actual', status='passed', reviewer=reviewer, summary=summary,
            request=file_record(REQUESTS[mode]), source_files=sources()))
    return request


def paths(request, arm, phase):
    base = RUN/'final-render'/request['id']/arm
    return base/f'{phase}-invocation.json', base/phase


def envelope(mode, qualification=None):
    from vipe_benchmark.final_render_actual_dispatch import native_command
    request_record = file_record(REQUESTS[mode])
    request = read_json(request_record['path'])
    interpreter = file_record(ENV/'bin/python')
    worker = file_record(ROOT/'scripts/final-render-actual-worker.py')
    arms = [QUALIFY_ARM] if mode == 'QUALIFY' else list(request['compositions'])
    commands = {}
    for arm in arms:
        for phase in PHASES:
            invocation, _ = paths(request, arm, phase)
            commands[arm+'/'+phase] = native_command(interpreter, worker, invocation,
                invocation.with_name(invocation.stem+'-release.json'), interpreter_invocation=str(ENV/'bin/python'))
    head = ledger().events()[-1]['event_sha256']
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    folder = HERE/f'{mode.lower()}-{stamp}'
    folder.mkdir()
    value = dict(schema='plan069-final-render-do/v1', record_kind='actual', mode=mode, request=request_record,
        qualification=None if qualification is None else file_record(qualification),
        commercial=file_record(HERE/'commercial-assessment.json'),
        source_review=file_record(HERE/f'source-review-{mode.lower()}.json'), commands=commands,
        interpreter=interpreter, interpreter_invocation=str(ENV/'bin/python'),
        checkout=str(REPO/'.local/FreeTimeGsVanilla'), source_files=sources(), ledger_head_sha256=head,
        matcher_runtime=file_record(RUNTIME/'matcher-runtime.json'))
    write_json(folder/'approval.json', dict(schema='plan069-final-render-do-approval/v1', record_kind='human',
        status='approved', reviewer='samaust', approved_at='2026-10-07', basis=BASIS,
        recorded_by='Claude, under the user standing GPU approval; not separately reviewed by the user',
        proposal_sha256=object_hash(value), request=request_record, allocations=request['allocations']))
    value['approval'] = file_record(folder/'approval.json')
    write_json(folder/'envelope.json', value)
    print(folder/'envelope.json')


def dispatch(envelope_path, arm, phases):
    from vipe_benchmark.final_render_actual_dispatch import ActualDispatcher
    record = file_record(envelope_path)
    value = read_json(envelope_path)
    request = read_json(value['request']['path'])
    dispatcher = ActualDispatcher(record, ledger())
    width = file_record(Path(value['request']['path']).with_name('voxel-width.json'))
    for phase in phases:
        index = tuple(PHASES).index(phase)
        parent = initializer = None
        if index:
            parent = file_record(paths(request, arm, tuple(PHASES)[index-1])[1]/'result.json')
            if phase in ('train', 'render'):
                initializer_result = read_json(paths(request, arm, 'initializer')[1]/'result.json')
                initializer = initializer_result['initializer']
        invocation, output = paths(request, arm, phase)
        invocation.parent.mkdir(parents=True, exist_ok=True)
        started = datetime.datetime.now(datetime.timezone.utc).isoformat()
        print(f'{started} dispatch {arm}/{phase}', flush=True)
        outcome = dispatcher.dispatch(arm, phase, invocation, output, parent_result=parent,
            initializer=initializer, voxel_width=width if phase == 'initializer' else None)
        print(f'{arm}/{phase} complete: {outcome["finish"]["elapsed_seconds"]:.1f}s', flush=True)


def qualify(envelope_path):
    from vipe_benchmark.final_render_native_qualification import build
    folder = Path(envelope_path).parent/'qualification'
    print(build(file_record(REQUESTS['DO']), file_record(envelope_path), ledger(), folder))


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    commands = parser.add_subparsers(dest='command', required=True)
    commands.add_parser('licence')
    review = commands.add_parser('source-review')
    review.add_argument('--reviewer', required=True)
    review.add_argument('--summary', required=True)
    build = commands.add_parser('envelope')
    build.add_argument('--mode', choices=('QUALIFY', 'DO'), required=True)
    build.add_argument('--qualification')
    run = commands.add_parser('dispatch')
    run.add_argument('--envelope', required=True)
    run.add_argument('--arm', required=True)
    run.add_argument('--phases', nargs='+', default=list(PHASES), choices=list(PHASES))
    aggregate = commands.add_parser('qualify')
    aggregate.add_argument('--envelope', required=True)
    args = parser.parse_args()
    if args.command == 'licence':
        licence()
    elif args.command == 'source-review':
        source_review(args.reviewer, args.summary)
    elif args.command == 'envelope':
        envelope(args.mode, args.qualification)
    elif args.command == 'dispatch':
        dispatch(args.envelope, args.arm, args.phases)
    else:
        qualify(args.envelope)


if __name__ == '__main__':
    main()

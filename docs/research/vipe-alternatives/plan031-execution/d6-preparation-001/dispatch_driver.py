"""Invoke the approved D6 dispatcher; meter CPU work around its GPU reservation."""
import json
import hashlib
from pathlib import Path
import signal
import sys
import time

if len(sys.argv) != 6:
    raise SystemExit('usage: dispatch_driver.py CHECKOUT SOURCE_REVIEW QUALIFICATION QUALITATIVE_ADMISSION RECEIPT')
started = time.monotonic()
root = Path(sys.argv[1]).absolute()
source_review = Path(sys.argv[2]).absolute()
qualification = Path(sys.argv[3]).absolute()
qualitative_admission = Path(sys.argv[4]).absolute()
sys.path.insert(0, str(root / 'scripts'))
output = Path(sys.argv[5]).absolute()
if output.exists():
    raise FileExistsError(output)


def record(path):
    path = Path(path).absolute()
    return dict(path=str(path), bytes=path.stat().st_size,
                sha256=hashlib.sha256(path.read_bytes()).hexdigest())


def deadline(signum, frame):
    raise TimeoutError('D6 dispatcher CPU preparation deadline')


signal.signal(signal.SIGALRM, deadline)
signal.setitimer(signal.ITIMER_REAL, 160)
error = None
try:
    import basketball_vipe_depth_single_dispatch as driver
    from vipe_benchmark.config import load
    from vipe_benchmark.files import file_record
    from vipe_benchmark.ledger import Ledger
    run = driver.shared_run_root() / '.local/vipe-alternatives' / driver.RUN
    ledger = Ledger(run / 'ledger.jsonl', dict(load(), new_download_gib_limit=110,
                                            new_artifact_disk_gib_limit=210))
    ledger_start_sequence = ledger.events()[-1]['sequence']
    original = driver.supervise
    original_reserve = Ledger.reserve

    def reserved(owner, job_id, *args, **kwargs):
        reservation = original_reserve(owner, job_id, *args, **kwargs)
        if job_id == 'plan069-D6-maps-001':
            signal.setitimer(signal.ITIMER_REAL, 0)
        return reservation

    Ledger.reserve = reserved

    def supervised(*args, **kwargs):
        try:
            return original(*args, **kwargs)
        finally:
            finishes = [e for e in ledger.events() if e.get('event') == 'finish' and
                e.get('job_id') == 'plan069-D6-maps-001' and
                e['sequence'] > ledger_start_sequence]
            gpu_elapsed = finishes[0]['elapsed_seconds'] if len(finishes) == 1 else 0.
            cpu_elapsed = time.monotonic() - started - gpu_elapsed
            signal.setitimer(signal.ITIMER_REAL, max(.001, 160 - cpu_elapsed))

    driver.supervise = supervised
    driver.dispatch('D6', run / 'jobs/plan069-depth-context-003/context.json',
        qualification,
        run / 'jobs/plan069-D6-setup-001/result.json',
        source_review,
        qualitative_admission=qualitative_admission)
except BaseException as exc:
    error = type(exc).__name__ + ': ' + str(exc)
finally:
    signal.setitimer(signal.ITIMER_REAL, 0)
    elapsed = time.monotonic() - started
    finishes = [e for e in ledger.events() if e.get('event') == 'finish' and
                e.get('job_id') == 'plan069-D6-maps-001' and
                e['sequence'] > ledger_start_sequence] if 'ledger' in globals() else []
    gpu = finishes[0]['elapsed_seconds'] if len(finishes) == 1 else 0.
    cpu = elapsed - gpu
    receipt = dict(schema='plan069-D6-dispatch-metering/v1', candidate='D6',
        status='passed' if error is None and 0 <= cpu <= 160 else 'failed', error=error,
        dispatcher=record(root / 'scripts/basketball_vipe_depth_single_dispatch.py'),
        driver=record(__file__), elapsed_seconds=elapsed,
        gpu_reservation_elapsed_seconds=gpu, cpu_preparation_elapsed_seconds=cpu,
        cpu_seconds_limit=160, gpu_finish_event_sha256=finishes[0]['event_sha256'] if len(finishes) == 1 else None,
        timing_scope='Measured complete driver duration minus the same-host monotonic GPU reservation duration; receipt/ledger terminal writes excluded',
        gpu_cleanup_confirmed=finishes[0].get('cleanup_confirmed') if len(finishes) == 1 else None,
        charge_owner='root', cpu_charge_applied=False)
    with output.open('x') as stream:
        json.dump(receipt, stream, indent=2)
        stream.write('\n')
    if 'ledger' in globals():
        ledger.charge_cpu_preparation(max(0., cpu), file_record(output))
    print(json.dumps({k:receipt[k] for k in ('status','error','elapsed_seconds','cpu_preparation_elapsed_seconds','gpu_cleanup_confirmed')}), flush=True)
if receipt['status'] != 'passed':
    raise SystemExit(1)

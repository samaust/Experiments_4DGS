"""Plan046 launch gate: publish and verify durable evidence before a test launch."""
import ast
import datetime
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[3]
RUN = Path(__file__).resolve().parent
START_RAW = json.loads((RUN / 'iteration-016-timing-start.json').read_text())
START = dict(utc=START_RAW['utc'], monotonic=START_RAW['monotonic'])


def stamp():
    return dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(), monotonic=time.monotonic())


def publish(path, value):
    raw = (json.dumps(value, indent=2, allow_nan=False) + "\n").encode()
    with path.open("xb") as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    observed = path.read_bytes()
    assert observed == raw and hashlib.sha256(observed).digest() == hashlib.sha256(raw).digest()
    return dict(path=str(path), sha256=hashlib.sha256(raw).hexdigest(), bytes=len(raw))


def main():
    kind, index, reason = sys.argv[1], int(sys.argv[2]), sys.argv[3]
    assert kind in ("diagnostic", "aggregate")
    timeout = 120 if kind == "diagnostic" else 300
    limits = dict(diagnostic=3, aggregate=2)
    counts = {k: len(list(RUN.glob("s1-recovery-launch-note-016-" + k + "-*.json"))) for k in limits}
    assert counts[kind] < limits[kind] and index == counts[kind] + 1
    directory = RUN / ("s1-recovery-" + kind + "-016-" + str(index).zfill(3))
    assert not directory.exists()
    for relative in ("scripts/vipe_benchmark/s1_helper_session.py", "scripts/vipe_benchmark/s1_cpu_helper.py", "scripts/vipe_benchmark/supervisor.py", "scripts/vipe_benchmark/s1_validation_runner.py", "tests/test_vipe_benchmark_s1_helper_fixtures.py", "tests/test_vipe_benchmark_supervisor.py", "tests/test_vipe_benchmark_s1_recovery.py"):
        ast.parse((ROOT / relative).read_text())
    status = (RUN / "status.md").read_bytes()
    assert len(status) == 1172 and hashlib.sha256(status).hexdigest() == "5111315d438adaba923be45dd9b87ffe78bb29e36ba111f8cff8e8a6025a8431"
    command = [str(ROOT / ".local/envs/stg-colmap/bin/python"), "-B", "-m", "vipe_benchmark.s1_validation_capture", str(directory), "--timeout", str(timeout)]
    if kind == "diagnostic":
        command.append("--diagnostic")
    env = os.environ.copy()
    settings = {key: "1" for key in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS", "VIPE_CPU_VALIDATION")}
    settings["PYTHONPATH"] = str(ROOT / "scripts")
    settings["OPENCV_FOR_THREADS_NUM"] = "1"
    env.update(settings)
    for key in ("S1_HELPER_DIAGNOSTIC", "S1_RECEIPT_DIAGNOSTIC"):
        env.pop(key, None)
    after = dict(counts)
    after[kind] += 1
    contract = ast.parse((ROOT / "scripts/vipe_benchmark/s1_validation_contract.py").read_text())
    stdin_bytes = ast.literal_eval(next(n.value for n in contract.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=="STDIN" for t in n.targets))).encode()
    bindings = []
    for relative in ("plans/plan_046.md", "docs/continuous-improvement/plan031-s1-recovery-20260919/implementation-dispatch-016.json"):
        path = ROOT/relative; raw=path.read_bytes()
        bindings.append(dict(path=str(path),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest()))
    source_paths=[]
    baseline=json.loads((RUN/'s1-recovery-validation-013.json').read_text())
    source_set={Path(entry['path']) for entry in baseline['sources']}
    source_set.update((ROOT/'scripts/vipe_benchmark').glob('*.py'))
    for path in sorted(source_set):
        raw=path.read_bytes()
        source_paths.append(dict(path=str(path),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest()))
    now = stamp()
    elapsed = now["monotonic"] - START["monotonic"]
    reserve = 300 if kind == "diagnostic" or reason != "final current-source acceptance" else 0
    assert elapsed + timeout + reserve < 4800
    boot=Path('/proc/sys/kernel/random/boot_id').read_text().strip()
    def proc(pid):
        fields=Path('/proc',str(pid),'stat').read_text().rsplit(')',1)[1].split()
        return dict(boot_id=boot,pid=pid,ppid=int(fields[1]),pgid=int(fields[2]),start_ticks=int(fields[19]))
    ownership_root=proc(os.getpid());ancestors=[];cursor=ownership_root['ppid']
    while cursor:
        row=proc(cursor);row['threads']=sorted(int(t.name) for t in Path('/proc',str(cursor),'task').iterdir())
        assert row['start_ticks']<=ownership_root['start_ticks']
        ancestors.append(row);cursor=row['ppid']
    note = dict(ownership_root=ownership_root,retained_wrappers=[],preexisting_ancestors=ancestors,schema="plan046-prospective-launch/v1", stage_start=START, observed=now,
        elapsed_seconds=elapsed, execution_remaining_seconds=4800-elapsed, wall_remaining_seconds=5400-elapsed,
        bindings=bindings, sources=source_paths, status=dict(bytes=len(status),sha256=hashlib.sha256(status).hexdigest()), kind=kind, attempt_index=index, counts_before=counts, counts_after=after,
        remaining_before={k: limits[k]-counts[k] for k in limits}, remaining_after={k: limits[k]-after[k] for k in limits},
        command=command, cwd=str(ROOT), run_directory=str(directory), timeout_seconds=timeout, reason=reason,
        final_aggregate_reserved=kind=="diagnostic", final_aggregate_reserve_seconds=reserve,
        stdin_identity=dict(bytes=len(stdin_bytes),sha256=hashlib.sha256(stdin_bytes).hexdigest(), content=stdin_bytes.decode()), output_paths=[str(directory/name) for name in ("receipt.json","execution.json","process-stdout.log","process-stderr.log","stdout.log","stderr.log","stdin.py","runner.py","capture.py")]+[str(RUN/("s1-recovery-driver-016-"+kind+"-"+str(index).zfill(3)+suffix)) for suffix in ("-exec-start.json","-stdout.log","-stderr.log")], existing_scenarios_limit=36, new_scenarios_limit=6, combined_scenarios_limit=42, new_scenario_execution_seconds=2, new_scenario_cleanup_seconds=1, environment=settings, unset_environment=["S1_HELPER_DIAGNOSTIC", "S1_RECEIPT_DIAGNOSTIC"], cpu_workers_max=8,
        preparation="AST parsed; target directory vacant; frozen status matches; exclusive fsync note and exact readback required before launch")
    note_record = publish(RUN / ("s1-recovery-launch-note-016-" + kind + "-" + str(index).zfill(3) + ".json"), note)
    env['S1_OWNED_ROOT_NOTE']=note_record['path']
    env['S1_OWNED_ROOT_SHA256']=note_record['sha256']
    before_launch = stamp()
    assert before_launch["monotonic"] - START["monotonic"] + timeout + reserve < 4800
    prefix = RUN / ("s1-recovery-driver-016-" + kind + "-" + str(index).zfill(3))
    launch = dict(schema="plan046-exec-launch/v1", note=note_record, before_launch=before_launch,
        command=command, replacement="driver execs unchanged capture to remove one counted CPU process")
    publish(Path(str(prefix)+"-exec-start.json"), launch)
    with Path(str(prefix)+"-stdout.log").open("xb") as out, Path(str(prefix)+"-stderr.log").open("xb") as err:
        os.dup2(out.fileno(),1)
        os.dup2(err.fileno(),2)
    # Last check includes all durable preparation; exec creates no extra worker.
    assert time.monotonic() - START["monotonic"] + timeout + reserve < 4800
    os.execve(command[0],command,env)



if __name__ == "__main__":
    raise SystemExit(main())

"""Plan042 launch gate: publish and verify durable evidence before a test launch."""
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
START = dict(utc="2026-09-20T08:21:16.606625+00:00", monotonic=76294.047193781)


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
    counts = {k: len(list(RUN.glob("s1-recovery-launch-note-012-" + k + "-*.json"))) for k in limits}
    assert counts[kind] < limits[kind] and index == counts[kind] + 1
    directory = RUN / ("s1-recovery-" + kind + "-012-" + str(index).zfill(3))
    assert not directory.exists()
    for relative in ("scripts/vipe_benchmark/s1_validation_contract.py", "scripts/vipe_benchmark/s1_validation_runner.py", "tests/test_vipe_benchmark_s1_recovery.py"):
        ast.parse((ROOT / relative).read_text())
    status = (RUN / "status.md").read_bytes()
    assert len(status) == 1026 and hashlib.sha256(status).hexdigest() == "b8fbcacf1d0cdf0efe7347d9e763a58f7988f63ee8f1f242e6eb5fdf942b253a"
    command = [str(ROOT / ".local/envs/stg-colmap/bin/python"), "-B", "-m", "vipe_benchmark.s1_validation_capture", str(directory), "--timeout", str(timeout)]
    if kind == "diagnostic":
        command.append("--diagnostic")
    env = os.environ.copy()
    settings = {key: "1" for key in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS", "VIPE_CPU_VALIDATION")}
    settings["PYTHONPATH"] = str(ROOT / "scripts")
    env.update(settings)
    for key in ("S1_HELPER_DIAGNOSTIC", "S1_RECEIPT_DIAGNOSTIC"):
        env.pop(key, None)
    after = dict(counts)
    after[kind] += 1
    now = stamp()
    elapsed = now["monotonic"] - START["monotonic"]
    reserve = 300 if kind == "diagnostic" else 0
    assert elapsed + timeout + reserve < 1620
    note = dict(schema="plan042-prospective-launch/v1", stage_start=START, observed=now,
        elapsed_seconds=elapsed, execution_remaining_seconds=1620-elapsed, wall_remaining_seconds=1800-elapsed,
        kind=kind, attempt_index=index, counts_before=counts, counts_after=after,
        remaining_before={k: limits[k]-counts[k] for k in limits}, remaining_after={k: limits[k]-after[k] for k in limits},
        command=command, cwd=str(ROOT), run_directory=str(directory), timeout_seconds=timeout, reason=reason,
        final_aggregate_reserved=kind=="diagnostic", final_aggregate_reserve_seconds=reserve,
        environment=settings, unset_environment=["S1_HELPER_DIAGNOSTIC", "S1_RECEIPT_DIAGNOSTIC"], cpu_workers_max=8,
        preparation="AST parsed; target directory vacant; frozen status matches; exclusive fsync note and exact readback required before launch")
    note_record = publish(RUN / ("s1-recovery-launch-note-012-" + kind + "-" + str(index).zfill(3) + ".json"), note)
    before_launch = stamp()
    assert before_launch["monotonic"] - START["monotonic"] + timeout + reserve < 1620
    prefix = RUN / ("s1-recovery-driver-012-" + kind + "-" + str(index).zfill(3))
    with Path(str(prefix)+"-stdout.log").open("xb") as out, Path(str(prefix)+"-stderr.log").open("xb") as err:
        process = subprocess.run(command, cwd=ROOT, env=env, stdout=out, stderr=err)
    end = stamp()
    result = dict(schema="plan042-driver-completion/v1", note=note_record, before_launch=before_launch,
        end=end, stage_elapsed_seconds=end["monotonic"]-START["monotonic"], command=command,
        tool_driver_returncode=process.returncode, completion_observed=True)
    publish(Path(str(prefix)+"-completion.json"), result)
    print(json.dumps(result))
    return process.returncode


if __name__ == "__main__":
    raise SystemExit(main())

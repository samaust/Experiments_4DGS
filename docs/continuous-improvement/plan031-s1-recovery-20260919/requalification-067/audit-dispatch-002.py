"""Preserve the observed outcome of the consumed S1 recovery 002 attempt."""

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path.cwd()
sys.path.insert(0, str(ROOT / "scripts"))

from vipe_benchmark import s1_recovery
from vipe_benchmark.config import load
from vipe_benchmark.files import file_record
from vipe_benchmark.ledger import Ledger

HERE = Path(__file__).resolve().parent
LOCAL = ROOT / ".local/vipe-alternatives/plan031-20260913T032700Z"
LEDGER = LOCAL / "ledger.jsonl"
JOB = "S1-calibration-recovery-002"

raw = LEDGER.read_bytes()
prior = (HERE.parent / "requalification-066/post-dispatch-ledger.jsonl").read_bytes()
assert hashlib.sha256(prior).hexdigest() == "68412ed6711f31552d8ae3f849dc03636336c781045a14eae902c68109cb7ba3"
assert raw.startswith(prior)
events = Ledger(LEDGER, load()).events()
assert len(events) == 459
assert [row["event"] for row in events[453:]] == [
    "admission", "component_recovery_authorized", "reserve",
    "temporary_directory", "started", "finish",
]
admission, authorization, reservation, temporary, started, finish = events[453:]
assert all(row.get("job_id") == JOB for row in (authorization, reservation, temporary, started, finish))
assert reservation["evidence"]["authorization"]["sha256"] == "b0bf2f76970f84d1a85f2387e5f0b37e695045db0bd416a45caaadb93c766972"
assert reservation["evidence"]["request"]["bytes"] == 353132
assert finish["status"] == "failed" and finish["failure_kind"] == "job_deadline"
assert finish["primary_failure"]["phase"] == "worker_sample"
assert finish["cleanup_confirmed"] and not finish["cleanup_uncertain"]
assert finish["surviving_pids"] == finish["helper_ownership"] == finish["helper_cleanup_errors"] == []
assert finish["result"] is finish["acceptance"] is finish["terminal_receipt"] is None
assert started["pid"] == started["pgid"] == 558824
assert finish["reservation"] == {"sequence": 455, "event_sha256": reservation["event_sha256"]}

authorization_record = reservation["evidence"]["authorization"]
s1_recovery.validate_binding(LOCAL, load(), authorization_record, consumed=True)
try:
    s1_recovery.validate_binding(LOCAL, load(), authorization_record)
except ValueError as exc:
    refusal = str(exc)
    assert "consumed" in refusal
else:
    raise AssertionError("consumed identity remained dispatchable")

totals = Ledger(LEDGER, load()).totals(events)
assert totals["gpu"]["attempts"] == 32 and totals["gpu"]["reserved_seconds"] == 0
snapshot = HERE / "post-dispatch-ledger-002.jsonl"
with snapshot.open("xb") as stream:
    stream.write(raw)
assert file_record(snapshot)["sha256"] == file_record(LEDGER)["sha256"]

job_dir = LOCAL / "jobs" / JOB
temporary_files = sorted(str(path.relative_to(ROOT)) for path in Path(temporary["path"]).rglob("*") if path.is_file())
result = {
    "status": "failed_after_worker_launch",
    "attempt_consumed": True,
    "redispatch_authorized": False,
    "prior_453_event_prefix_unchanged": True,
    "ledger": file_record(snapshot),
    "live_ledger": file_record(LEDGER),
    "events": len(events),
    "admission": admission,
    "authorization": authorization,
    "reservation": reservation,
    "temporary_directory": temporary,
    "started": started,
    "finish": finish,
    "totals": totals,
    "validate_binding_consumed_passed": True,
    "unconsumed_binding_refusal": refusal,
    "worker_log": file_record(job_dir.with_suffix(".log")),
    "initial_runtime": file_record(job_dir / "initial-runtime.json"),
    "worker_config": file_record(job_dir / "config.json"),
    "temporary_files": temporary_files,
    "host_observations": {
        "worker_pid_query": {"command": "ps -p 558824 -o pid,ppid,pgid,stat,comm,args", "exit_code": 1, "rows": []},
        "gpu_compute_query": {"command": "nvidia-smi --query-compute-apps=pid,process_name,used_memory --format=csv,noheader", "exit_code": 0, "rows": []},
    },
}
assert LEDGER.read_bytes() == raw
with (HERE / "dispatch-outcome-002.json").open("x") as stream:
    json.dump(result, stream, indent=2)
    stream.write("\n")
print(json.dumps({key: result[key] for key in ("status", "attempt_consumed", "events", "totals", "unconsumed_binding_refusal")}, indent=2))

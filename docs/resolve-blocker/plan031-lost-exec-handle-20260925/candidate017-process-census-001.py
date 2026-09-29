"""Read-only scoped Plan049 process/thread census for candidate017 preflight."""
import datetime
import json
import os
import sys
from pathlib import Path

DRIVER = "/home/auss/git_repos/samaust/Experiments_4DGS/docs/resolve-blocker/plan031-progress-20260922/launch-049-exec.py"


def read_process(pid):
    base = Path("/proc") / str(pid)
    status = (base / "status").read_text(errors="replace")
    fields = {
        line.split(":", 1)[0]: line.split(":", 1)[1].strip()
        for line in status.splitlines() if ":" in line
    }
    stat = (base / "stat").read_text().split()
    argv = [part.decode(errors="replace") for part in (base / "cmdline").read_bytes().split(b"\0") if part]
    env = (base / "environ").read_bytes().split(b"\0")
    owned = [part.decode(errors="replace") for part in env if part.startswith((b"S1_JOB_LEDGER=", b"S1_OWNED_ROOT_NOTE="))]
    return {
        "pid": pid,
        "ppid": int(fields.get("PPid", "0")),
        "pgid": int(stat[4]),
        "state": fields.get("State", "?").split()[0],
        "threads": int(fields.get("Threads", "1")),
        "argv": argv,
        "owned_env": owned,
    }


def main():
    proc = Path("/proc")
    pids = sorted(int(entry.name) for entry in proc.iterdir() if entry.name.isdigit())
    observed = {}
    errors = []
    for pid in pids:
        try:
            observed[pid] = read_process(pid)
        except (OSError, ValueError, IndexError) as exc:
            errors.append({"pid": pid, "error": repr(exc)})

    observer = os.getpid()
    ancestors = []
    cursor = observer
    while cursor in observed:
        row = observed[cursor]
        ancestors.append(cursor)
        if row["ppid"] in (0, cursor):
            break
        cursor = row["ppid"]
    ancestor_set = set(ancestors)

    matching = []
    for pid, row in observed.items():
        if pid in ancestor_set:
            continue
        argv = row["argv"]
        has_driver = DRIVER in argv
        has_capture = any(argv[i:i + 2] == ["-m", "vipe_benchmark.s1_validation_capture"] for i in range(max(0, len(argv) - 1)))
        has_owned_ledger = any("S1_JOB_LEDGER=" in value and ".job-ledger-" in value for value in row["owned_env"])
        has_owned_note = any("S1_OWNED_ROOT_NOTE=" in value and "launch-note-049-" in value for value in row["owned_env"])
        if has_driver or has_capture or has_owned_ledger or has_owned_note:
            matching.append({
                "pid": pid,
                "argv0": argv[0] if argv else "",
                "driver_argv": argv if has_driver else None,
                "capture_argv": argv if has_capture else None,
                "owned_env": row["owned_env"],
            })

    value = {
        "schema": "candidate017-process-census/v1",
        "checked_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "scope": "Visible local /proc namespace; self and its ancestor tool-wrapper chain are excluded only from workload matching, not from process/thread totals.",
        "observer_pid": observer,
        "observer_ancestor_pids": ancestors,
        "visible_proc_count": len(observed),
        "visible_thread_count": sum(row["threads"] for row in observed.values()),
        "visible_proc_rows": [
            {key: row[key] for key in ("pid", "ppid", "pgid", "state", "threads")}
            | {"argv0": row["argv"][0] if row["argv"] else ""}
            for pid, row in sorted(observed.items()) if pid != observer
        ],
        "matching_plan049_workloads": matching,
        "errors": errors,
        "prompts_content_read": False,
    }
    destination = Path(sys.argv[1]) if len(sys.argv) == 2 else Path(__file__).with_name("candidate017-process-census-001.json")
    if destination.parent != Path(__file__).parent or not destination.name.startswith("candidate017-process-census-"):
        raise ValueError("process census output must use a fresh sibling evidence path")
    encoded = (json.dumps(value, indent=2, allow_nan=False) + "\n").encode()
    with destination.open("xb", buffering=0) as stream:
        if stream.write(encoded) != len(encoded):
            raise OSError("short process census write")
        stream.flush()
        os.fsync(stream.fileno())
    if destination.read_bytes() != encoded:
        raise OSError("process census readback mismatch")
    print(json.dumps({"path": str(destination), "bytes": len(encoded), "matching": len(matching), "errors": len(errors)}))


if __name__ == "__main__":
    main()

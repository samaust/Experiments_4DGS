"""Conservative run-scoped storage and acquisition accounting, without inference.

Direct receipt bytes include failed/undurable reads. Active intent files bridge
partial-to-output renames; inode identities distinguish retained failures from
new attempts. UV acquisition is max(metered TLS bytes, retained extracted cache
plus managed Python size). Those directories must persist without pruning for
the run. Storage counts each inode once using max(logical, allocated bytes);
symlinks and prompts trees are never traversed. Ambiguous evidence fails closed.
"""
from contextlib import contextmanager
import fcntl
import json
import os
from pathlib import Path
import re
import stat
import tempfile
import threading
import time

from .files import safe_path


class BudgetAccountingError(RuntimeError):
    pass


_LOCK_STATE = threading.local()


def _footprint(files):
    sizes = {}
    for info in files.values():
        key = info.st_dev, info.st_ino
        sizes[key] = max(sizes.get(key, 0), info.st_size, getattr(info, 'st_blocks', 0) * 512)
    return sum(sizes.values())


def _root(path):
    return safe_path(path).resolve()


def _scan_once(root):
    files = {}
    pending = [root]
    while pending:
        base = pending.pop()
        with os.scandir(base) as entries:
            for entry in entries:
                if entry.name == 'prompts':
                    continue
                info = entry.stat(follow_symlinks=False)
                path = base / entry.name
                if stat.S_ISDIR(info.st_mode):
                    pending.append(path)
                elif stat.S_ISREG(info.st_mode):
                    files[path] = info
    return files


def _inventory(root):
    if not root.exists():
        return {}
    return _scan_once(root)


def directory_bytes(root):
    """Count regular-file storage once per inode; rescan concurrent renames."""
    root = _root(root)
    for _ in range(3):
        try:
            return _footprint(_inventory(root))
        except FileNotFoundError:
            continue
    raise BudgetAccountingError('storage tree kept changing during byte accounting')


def _fingerprint(info):
    return info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns


def _document(path, expected, *, mutable=False):
    with path.open('rb') as stream:
        before = os.fstat(stream.fileno())
        data = stream.read()
        after = os.fstat(stream.fileno())
    if ((not mutable and _fingerprint(expected) != _fingerprint(before)) or
            _fingerprint(before) != _fingerprint(after)):
        raise FileNotFoundError('accounting record changed during snapshot')
    value = json.loads(data)
    if not isinstance(value, dict):
        raise BudgetAccountingError(f'accounting record is not an object: {path}')
    return value


def _bytes(value, name):
    if type(value) is not int or value < 0:
        raise BudgetAccountingError(f'{name} must be a nonnegative integer')
    return value


def _inside(root, value):
    path = _root(value)
    if not path.is_relative_to(root):
        raise BudgetAccountingError('transfer path is outside its run root')
    return path


def _partial(output):
    return output.with_suffix(output.suffix + '.partial')


def _same_file(info, identity):
    if not isinstance(identity, dict):
        return False
    return (info.st_dev, info.st_ino) == (identity.get('device'), identity.get('inode'))


def _publish_counter(path, value):
    """Atomically and durably replace a single mutable transfer counter."""
    path = safe_path(path)
    payload = json.dumps(value, sort_keys=True, allow_nan=False).encode() + b'\n'
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, prefix='.' + path.name + '.',
                                         suffix='.tmp', delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        descriptor = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def record_download_progress(run_root, transfer_id, output, bytes_received, reserved_bytes):
    """Durably reserve a direct read; publish actual bytes/zero after its flush.

    Call under download_lock. On read/write failure retain the reservation;
    neither a final receipt nor a later attempt cancels that uncertain charge.
    The actual received count must never decrease for one transfer identity.
    """
    root = _root(run_root)
    if not isinstance(transfer_id, str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,128}', transfer_id):
        raise BudgetAccountingError('invalid direct progress identity')
    output = _inside(root, output)
    received = _bytes(bytes_received, 'progress bytes_received')
    reserved = _bytes(reserved_bytes, 'progress reserved_bytes')
    path = root / 'transfers' / f'progress-{transfer_id}.json'
    if path.parent.is_symlink() or path.is_symlink():
        raise BudgetAccountingError('transfer counters cannot use symbolic links')
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        previous = _document(path, path.stat(), mutable=True)
        if previous.get('transfer_id') != transfer_id or previous.get('output') != str(output):
            raise BudgetAccountingError('direct progress identity or output changed')
        if received < _bytes(previous.get('bytes_received'), 'previous bytes_received'):
            raise BudgetAccountingError('direct received counter cannot decrease')
    _publish_counter(path, dict(transfer_id=transfer_id, output=str(output),
                              bytes_received=received, reserved_bytes=reserved))


def _snapshot_once(root):
    files = _inventory(root)
    receipts, active, uv_sessions, direct_progress = [], [], {}, {}
    for path, info in files.items():
        relative = path.relative_to(root)
        parts, name = relative.parts, path.name
        direct = ((parts[0] == 'transfers' and name.startswith('transfer-')) or
                  (parts[0] == 'assets' and '.transfer-' in name)) and name.endswith('.json')
        intent = parts[0] == 'transfers' and name.startswith('active-') and name.endswith('.json')
        progress_record = parts[0] == 'transfers' and name.startswith('progress-') and name.endswith('.json')
        uv = parts[0] == 'uv-transfers' and name.startswith(('active-', 'transfer-')) and name.endswith('.json')
        if not (direct or intent or uv or progress_record):
            continue
        value = _document(path, info, mutable=progress_record or (uv and name.startswith('active-')))
        if uv:
            identifier = value.get('transfer_id')
            if not isinstance(identifier, str) or not identifier:
                raise BudgetAccountingError('UV meter record lacks transfer identity')
            charge = _bytes(value.get('bytes_received'), 'UV bytes_received') + _bytes(
                value.get('reserved_bytes', 0), 'UV reserved_bytes')
            uv_sessions[identifier] = max(uv_sessions.get(identifier, 0), charge)
        elif direct:
            received = _bytes(value.get('bytes_received'), 'bytes_received')
            charge = received + _bytes(value.get('reserved_bytes', 0), 'reserved_bytes')
            output = _inside(root, value['output']) if value.get('output') else None
            receipts.append(dict(value, received=received, charge=charge, output_path=output, receipt_stat=info))
        elif progress_record:
            identifier = value.get('transfer_id')
            if not isinstance(identifier, str) or not identifier or identifier in direct_progress:
                raise BudgetAccountingError('missing or duplicate direct progress identity')
            charge = _bytes(value.get('bytes_received'), 'progress bytes_received') + _bytes(
                value.get('reserved_bytes'), 'progress reserved_bytes')
            direct_progress[identifier] = dict(value, charge=charge, output_path=_inside(root, value['output']))
        else:
            identifier = value.get('transfer_id')
            if not isinstance(identifier, str) or not identifier:
                raise BudgetAccountingError('active transfer lacks identity')
            output = _inside(root, value['output'])
            partial = _inside(root, value.get('partial', str(_partial(output))))
            active.append(dict(value, output_path=output, partial_path=partial))

    by_id = {}
    for row in receipts:
        if row.get('transfer_id'):
            if row['transfer_id'] in by_id:
                raise BudgetAccountingError('duplicate direct transfer receipt identity')
            by_id[row['transfer_id']] = row
    total = sum(row['charge'] for row in receipts if not row.get('transfer_id'))
    total += sum(max(by_id.get(identifier, {}).get('charge', 0),
                     direct_progress.get(identifier, {}).get('charge', 0))
                 for identifier in by_id.keys() | direct_progress.keys())
    if len({row['transfer_id'] for row in active}) != len(active):
        raise BudgetAccountingError('duplicate active transfer identity')
    claimed, progress = set(), {}
    known_outputs = {row['output_path'] for row in receipts if row['output_path']}
    known_outputs.update(row['output_path'] for row in direct_progress.values())
    active_ids = {row['transfer_id'] for row in active}
    for identifier, row in direct_progress.items():
        if identifier not in active_ids:
            active.append(dict(transfer_id=identifier, output_path=row['output_path'],
                               partial_path=_partial(row['output_path'])))
    for row in active:
        output, partial = row['output_path'], row['partial_path']
        recorded = direct_progress.get(row['transfer_id'])
        if recorded is not None and recorded['output_path'] != output:
            raise BudgetAccountingError('direct progress and intent outputs disagree')
        known_outputs.add(output)
        if row['transfer_id'] in by_id:
            continue
        # Both names may coexist while a writer publishes a hardlink. This is
        # one transfer, so count its payload once, including after rename.
        size = max((files[p].st_size for p in (partial, output) if p in files), default=0)
        recorded_charge = recorded['charge'] if recorded is not None else 0
        total += max(0, size - recorded_charge)
        progress[output] = max(progress.get(output, 0), size, recorded_charge)
        claimed.update((partial, output))

    cache_roots = (root / 'setup-cache', root / 'managed-python')
    direct_paths = claimed | known_outputs | {_partial(p) for p in known_outputs}
    for path, info in files.items():
        if path in claimed or not path.name.endswith('.partial'):
            continue
        if any(path.is_relative_to(cache) for cache in cache_roots) and path not in direct_paths:
            continue  # Already in the retained package/cache acquisition proxy.
        matching = [r for r in receipts if r['output_path'] and _partial(r['output_path']) == path]
        covered = 0
        for receipt in matching:
            identity = receipt.get('partial_identity')
            if _same_file(info, identity):
                covered = max(covered, min(receipt['received'], _bytes(identity.get('size'), 'partial identity size')))
            elif identity is None and info.st_mtime_ns <= receipt['receipt_stat'].st_mtime_ns:
                # Frozen legacy teacher receipts predate explicit inode records.
                # A newer retry intent takes precedence above; a rewritten
                # legacy partial has a newer mtime and receives a new charge.
                covered = max(covered, min(receipt['received'], info.st_size))
        extra = max(0, info.st_size - covered)
        total += extra
        output = path.with_suffix('')
        progress[output] = max(progress.get(output, 0), extra)
        direct_paths.add(path)

    # Legacy teacher acquisition can rename its payload before the attempt
    # receipt exists. Count unreceipted non-JSON asset payloads conservatively.
    for path, info in files.items():
        if (path.is_relative_to(root / 'assets') and path not in direct_paths and
                not path.name.endswith(('.json', '.partial')) and not path.name.startswith('.')):
            total += info.st_size

    cache_bytes = sum(info.st_size for path, info in files.items() if path not in direct_paths and
                      any(path.is_relative_to(cache) for cache in cache_roots))
    uv_bytes = sum(uv_sessions.values())
    return dict(download_bytes=total + max(uv_bytes, cache_bytes),
                artifact_bytes=_footprint(files), logical_artifact_bytes=sum(info.st_size for info in files.values()),
                direct_download_bytes=total, uv_metered_bytes=uv_bytes,
                retained_package_bytes=cache_bytes, active_progress=progress, uv_progress=uv_sessions)


def _snapshot(root):
    root = _root(root)
    for _ in range(3):
        try:
            return _snapshot_once(root)
        except (FileNotFoundError, json.JSONDecodeError):
            continue
    raise BudgetAccountingError('accounting files are unstable or contain incomplete JSON; refusing an undercount')


def budget_snapshot(run_root):
    result = _snapshot(run_root)
    return {name: result[name] for name in ('download_bytes', 'artifact_bytes', 'logical_artifact_bytes')}


def download_remaining(run_root, limit, *, active_output=None, bytes_received=0, artifact_limit=None,
                       uv_transfer_id=None):
    """Allowance for the next read, including bytes received but not yet written.

    Call while holding download_lock; never request remaining+1 to probe EOF.
    active_output names the final output of this attempt, not a prior receipt.
    Inside the exclusive lock, wait one second after each completed scan and charge all intervening
    received/reserved bytes locally. This bounds wire reads without a tree walk
    per chunk. Outside a lock, always take a fresh snapshot (read-only callers).
    """
    limit = _bytes(limit, 'download limit')
    received = _bytes(bytes_received, 'active bytes_received')
    root = _root(run_root)
    state = getattr(_LOCK_STATE, 'runs', {}).get(root)
    now = time.monotonic()
    if state is None or state['snapshot'] is None or now - state['checked'] >= 1:
        result = _snapshot(root)
        if state is not None:
            # A large inventory can itself take over a second. Start the
            # reuse interval at completion so that one slow scan cannot turn
            # every subsequent socket read into another full tree walk.
            state.update(snapshot=result, checked=time.monotonic())
    else:
        result = state['snapshot']
    if active_output is not None and uv_transfer_id is not None:
        raise BudgetAccountingError('a read cannot be both direct and UV-metered')
    durable = (result['uv_progress'].get(uv_transfer_id, 0) if uv_transfer_id is not None else
               result['active_progress'].get(_inside(root, active_output), 0) if active_output else 0)
    unwritten = max(0, received - durable)
    charged = (result['direct_download_bytes'] + max(result['uv_metered_bytes'] + unwritten,
                result['retained_package_bytes']) if uv_transfer_id is not None else
               result['download_bytes'] + unwritten)
    if state is not None:
        charged = max(charged, state['highwater'])
        state['highwater'] = charged
    remaining = limit - charged
    if artifact_limit is not None:
        remaining = min(remaining, _bytes(artifact_limit, 'artifact limit') - result['artifact_bytes'] - unwritten)
    return max(0, remaining)


@contextmanager
def download_lock(run_root, *, cancel_event=None):
    """Serialize direct transfers and UV proxy sessions sharing one allowance."""
    root = _root(run_root)
    root.mkdir(parents=True, exist_ok=True)
    runs = getattr(_LOCK_STATE, 'runs', None)
    if runs is None:
        runs = _LOCK_STATE.runs = {}
    if root in runs:
        raise BudgetAccountingError('nested download locks for one run are prohibited')
    with (root / '.download-budget.lock').open('a+b') as stream:
        if cancel_event is None:
            fcntl.flock(stream.fileno(), fcntl.LOCK_EX)
        else:
            while True:
                try:
                    fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                    break
                except BlockingIOError:
                    if cancel_event.wait(.05):
                        raise BudgetAccountingError('download lock acquisition was cancelled')
        runs[root] = dict(snapshot=None, checked=0., highwater=0)
        try:
            yield
        finally:
            del runs[root]
            fcntl.flock(stream.fileno(), fcntl.LOCK_UN)

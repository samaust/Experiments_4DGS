"""Fixed S1 CPU roles: bounded control transport and retained launch ownership.

The OS/native-thread boundary is measured, not asserted to be hard real time.
An unresolved launcher remains in OWNERS even after a timed-out caller returns.
"""
import _thread
import json
import math
import os
from pathlib import Path
import signal
import socket
import struct
import sys
import time
import uuid

THREADS = ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS', 'NUMEXPR_NUM_THREADS')
MAX_FRAME = 65536
IO_SLICE = 16384
OWNERS = []


def tokens(value, depth=0, count=None):
    """Bounded primitive traversal; callers advance at most 256 nodes per tick."""
    count = [0] if count is None else count
    count[0] += 1
    if count[0] > 4096 or depth > 16:
        raise ValueError('control item/depth limit')
    typ = type(value)
    if typ is dict:
        yield '{'
        for index, (key, item) in enumerate(value.items()):
            if type(key) is not str:
                raise ValueError('control key type')
            if index:
                yield ','
            yield from tokens(key, depth+1, count)
            yield ':'
            yield from tokens(item, depth+1, count)
        yield '}'
    elif typ is list:
        yield '['
        for index, item in enumerate(value):
            if index:
                yield ','
            yield from tokens(item, depth+1, count)
        yield ']'
    elif value is None or typ is bool:
        yield json.dumps(value)
    elif typ is str:
        if len(value) > 2048:
            raise ValueError('control string limit')
        yield json.dumps(value, ensure_ascii=True)
    elif typ is int:
        if not -(10**20) < value < 10**20:
            raise ValueError('control integer limit')
        yield str(value)
    elif typ is float and math.isfinite(value):
        yield json.dumps(value, allow_nan=False)
    else:
        raise ValueError('control primitive type')


def pairs(items):
    result = {}
    for key, value in items:
        if key in result:
            raise ValueError('duplicate control key')
        result[key] = value
    return result


def number(token):
    if len(token) > 64:
        raise ValueError('control number token limit')
    value = float(token)
    if not math.isfinite(value):
        raise ValueError('control nonfinite number')
    return value


def integer(token):
    if len(token.lstrip('-')) > 20:
        raise ValueError('control integer token limit')
    return int(token)


class LexicalGuard:
    def __init__(self):
        self.depth = self.nodes = self.length = 0
        self.quoted = self.escaped = self.scalar = False
    def feed(self, raw):
        for byte in raw:
            if self.quoted:
                self.length += 1
                if self.length > 24578:
                    raise ValueError('control string lexical limit')
                if self.escaped: self.escaped = False
                elif byte == 92: self.escaped = True
                elif byte == 34: self.quoted = False
                continue
            if byte in (32,9,10,13,44,58,93,125):
                self.scalar = False
            elif not self.scalar:
                self.nodes += 1
                if self.nodes > 4096: raise ValueError('control lexical item limit')
                if byte == 34:
                    self.quoted = True; self.length = 0
                elif byte not in (91,123):
                    self.scalar = True; self.length = 0
            if self.scalar:
                self.length += 1
                if self.length > 64: raise ValueError('control number token limit')
            if byte in (91,123):
                self.depth += 1
                if self.depth > 17: raise ValueError('control depth limit')
            elif byte in (93,125): self.depth -= 1


def decode(raw, *, guarded=False):
    if not 0 < len(raw) <= MAX_FRAME:
        raise ValueError('control frame limit')
    if not guarded:
        LexicalGuard().feed(raw)
    return json.loads(raw.decode('utf-8'), object_pairs_hook=pairs,
        parse_int=integer, parse_float=number,
        parse_constant=lambda v: (_ for _ in ()).throw(ValueError('nonfinite control token')))


class Wire:
    def __init__(self, channel):
        self.channel = channel
        channel.setblocking(False)
        self.out = bytearray()
        self.encoder = None
        self.encode_part = b''
        self.guard = LexicalGuard()
        self.encoded = bytearray()
        self.header = bytearray()
        self.body = bytearray()
        self.length = None
        self.validator = None
        self.decoded = None
        self.sent_bytes = self.received_bytes = 0
        self.blocked_writes = 0

    def queue(self, message):
        if self.encoder is not None or self.out:
            raise ValueError('control writer busy')
        self.encoder = tokens(message)
        self.encoded = bytearray()

    def tick(self):
        if self.encoder is not None:
            budget = IO_SLICE
            for _ in range(256):
                if not self.encode_part:
                    try:
                        self.encode_part = next(self.encoder).encode('ascii')
                    except StopIteration:
                        self.out = bytearray(struct.pack('!I', len(self.encoded))) + self.encoded
                        self.encoded = bytearray()
                        self.encoder = None
                        break
                    if len(self.encoded) + len(self.encode_part) > MAX_FRAME:
                        raise ValueError('encoded control frame limit')
                part = self.encode_part[:budget]
                self.encoded.extend(part)
                self.encode_part = self.encode_part[len(part):]
                budget -= len(part)
                if not budget:
                    break
        if self.out:
            try:
                size = self.channel.send(memoryview(self.out)[:IO_SLICE])
                del self.out[:size]
                self.sent_bytes += size
            except BlockingIOError:
                self.blocked_writes += 1
        if self.validator is not None:
            for _ in range(256):
                try:
                    next(self.validator)
                except StopIteration:
                    try:
                        trailing = self.channel.recv(1, socket.MSG_PEEK)
                    except BlockingIOError:
                        trailing = None
                    if trailing:
                        raise ValueError('unsolicited trailing control frame')
                    if trailing == b'':
                        raise EOFError('helper exited at complete frame')
                    value = self.decoded
                    self.validator = self.decoded = None
                    self.header.clear(); self.body.clear(); self.length = None
                    self.guard = LexicalGuard()
                    return value
            return None
        budget = IO_SLICE
        while budget:
            target = self.header if self.length is None else self.body
            remaining = (4 if self.length is None else self.length) - len(target)
            try:
                chunk = self.channel.recv(min(remaining, budget))
            except BlockingIOError:
                return None
            if not chunk:
                raise EOFError('helper EOF during transport')
            if self.length is not None:
                self.guard.feed(chunk)
            target.extend(chunk)
            budget -= len(chunk)
            self.received_bytes += len(chunk)
            if self.length is None and len(self.header) == 4:
                self.length = struct.unpack('!I', self.header)[0]
                if not 0 < self.length <= MAX_FRAME:
                    raise ValueError('control advertised frame limit')
            if self.length is not None and len(self.body) == self.length:
                self.decoded = decode(bytes(self.body), guarded=True)
                self.validator = tokens(self.decoded)
                return None
        return None


def identity(pid):
    fields = Path('/proc', str(pid), 'stat').read_text().rsplit(')', 1)[1].split()
    return dict(pid=pid, pgid=int(fields[2]), start_ticks=int(fields[19]))


def census():
    rows = {}
    for entry in Path('/proc').iterdir():
        if entry.name.isdigit():
            try:
                f = (entry/'stat').read_text().rsplit(')', 1)[1].split()
                rows[int(entry.name)] = dict(pid=int(entry.name), ppid=int(f[1]),
                    pgid=int(f[2]), start_ticks=int(f[19]), state=f[0])
            except (FileNotFoundError, ProcessLookupError):
                pass
    return rows


class Owner:
    """Only this retained thread creates/reaps children and scans ownership."""
    def __init__(self, session):
        self.session = session
        self.cancelled = False
        self.done = False
        self.errors = []
        self.records = {role: dict(role=role, state='pending', pid=None) for role in ('work', 'sample')}
        self.members = {}
        self.groups = {}
        self.census_ok = False
        self.signals = []
        self.boot_id = None
        self.handle = None
        self.cancel_time = None

    def spawn(self, role, actions, env):
        return os.posix_spawn(sys.executable,
            [sys.executable, '-B', '-m', 'vipe_benchmark.s1_cpu_helper', role, self.session.token, '100'],
            env, file_actions=actions, setsid=True)

    def observe_identity(self, pid):
        return identity(pid)

    def observe(self):
        return census()

    def signal_group(self, pid, sig):
        os.killpg(pid, sig)

    def reap_child(self, pid):
        return os.waitpid(pid, os.WNOHANG)

    def run(self):
        try:
            self.boot_id = Path('/proc/sys/kernel/random/boot_id').read_text().strip()
            for role in ('work', 'sample'):
                if self.cancelled:
                    break
                self.records[role] = dict(role=role, state='spawning', pid=None)
                child = self.session.channels[role][1]
                actions = [(os.POSIX_SPAWN_DUP2, child.fileno(), 100)]
                for pair in self.session.channels.values():
                    for channel in pair:
                        if channel.fileno() >= 0 and channel.fileno() != 100:
                            actions.append((os.POSIX_SPAWN_CLOSE, channel.fileno()))
                env = dict(os.environ, PYTHONPATH=str(Path(__file__).resolve().parents[1]))
                env.update({key: '1' for key in THREADS})
                try:
                    pid = self.spawn(role, actions, env)
                except OSError:
                    self.records[role] = dict(role=role, state='pending', pid=None, failed=True)
                    raise
                # Publish returned PID before *any* fallible operation or seam.
                self.records[role] = dict(role=role, state='pid_owned', pid=pid)
                child.close()
                observed = self.observe_identity(pid)
                if observed['pgid'] != pid:
                    raise ValueError('spawn did not establish owned group')
                self.records[role] = dict(role=role, state='pid_owned', **observed)
                if self.cancelled:
                    break
            while True:
                self.maintain()
                if self.cancelled and all(r['state'] in ('pending', 'reaped') for r in self.records.values()):
                    break
                time.sleep(.005)
        except BaseException as exc:
            self.errors.append(dict(error_class=type(exc).__name__, message=str(exc), phase='startup'))
            self.cancelled = True
            self.maintain()
            # Keep the sole owner alive to clean a PID published before failure.
            while any(r.get('pid') and r['state'] != 'reaped' for r in self.records.values()):
                self.maintain()
                time.sleep(.005)
        finally:
            for pair in self.session.channels.values():
                try:
                    pair[1].close()
                except OSError:
                    pass
            self.done = True

    def maintain(self):
        try:
            rows = self.observe()
            groups = {}
            for pid, row in rows.items():
                groups.setdefault(row["pgid"], []).append(pid)
            self.groups = groups
            leaders = {r['pid'] for r in self.records.values() if r.get('pid') and r['state'] != 'reaped'}
            owned = set(leaders) | set(self.members)
            for _ in range(len(rows)+1):
                added = {pid for pid, row in rows.items() if row['ppid'] in owned or row['pgid'] in leaders} - owned
                if not added:
                    break
                owned.update(added)
            members = {pid: rows[pid] for pid in owned if pid in rows}
            for pid, old in self.members.items():
                if pid in rows and rows[pid]['start_ticks'] != old['start_ticks']:
                    raise ValueError('owned descendant identity changed')
            self.members = members
            self.census_ok = True
            if not self.cancelled:
                return
            now = time.monotonic()
            if self.cancel_time is None:
                self.cancel_time = now
            sig = signal.SIGTERM if now-self.cancel_time < self.session.term_grace else signal.SIGKILL
            for role, record in list(self.records.items()):
                pid = record.get('pid')
                if not pid or record['state'] == 'reaped':
                    continue
                # Unreaped direct-child PID pins its setsid group even if identity
                # reads failed. Never signal a PGID supplied by the helper.
                group = [v for v in members.values() if v['pgid'] == pid and v['state'] != 'Z']
                escaped = [v for v in members.values() if v['pgid'] not in leaders and v['pid'] not in leaders]
                if escaped:
                    raise RuntimeError('escaped descendant ownership unresolved')
                if group:
                    try:
                        self.signal_group(pid, sig)
                    except ProcessLookupError:
                        pass
                    self.signals.append(dict(pid=pid, signal=int(sig), monotonic=now))
                else:
                    observed = os.waitid(os.P_PID, pid, os.WEXITED | os.WNOHANG | os.WNOWAIT)
                    if observed is not None:
                        reaped, status = self.reap_child(pid)
                        if reaped == pid:
                            self.records[role] = dict(record, state='reaped', wait_status=status)
        except BaseException as exc:
            self.census_ok = False
            observation = dict(error_class=type(exc).__name__, message=str(exc), phase='helper_cleanup')
            if observation not in self.errors:
                self.errors.append(observation)


class Session:
    def __init__(self, *, ready_seconds=1., setup_seconds=2., total_seconds=3., owner_factory=Owner):
        self.t0 = time.monotonic()
        if not (0 < ready_seconds <= 1 and ready_seconds < setup_seconds <= 2 and setup_seconds < total_seconds <= 3):
            raise ValueError('invalid session setup cutoffs')
        self.ready_deadline = self.t0+ready_seconds
        self.setup_deadline = self.t0+setup_seconds
        self.cleanup_deadline = self.t0+total_seconds
        self.token = uuid.uuid4().hex
        self.channels = {}
        self.wires = {}
        self.ready = {}
        self.pending_ready = {}
        self.requests = {'work': None, 'sample': None}
        self.sequences = {'work': 0, 'sample': 0}
        self.events = []
        self.ticks = [self.t0]
        self.poisoned = False
        self.term_grace = .2
        self.closed = False
        self.owner = owner_factory(self)
        if not hasattr(_thread, 'start_joinable_thread'):
            raise RuntimeError('S1 requires native joinable ownership thread')
        try:
            for role in ('work', 'sample'):
                pair = socket.socketpair()
                self.channels[role] = pair
                self.wires[role] = Wire(pair[0])
            OWNERS.append(self.owner)
            self.owner.handle = _thread.start_joinable_thread(self.owner.run, daemon=False)
        except BaseException:
            self.poisoned = self.owner.cancelled = True
            if self.owner.handle is None:
                for pair in self.channels.values():
                    for channel in pair:
                        channel.close()
                if self.owner in OWNERS:
                    OWNERS.remove(self.owner)
            raise

    def envelope(self, role, request_id, kind, payload):
        return dict(version=1, session=self.token, boot_id=self.owner.boot_id,
            role=role, request_id=request_id, kind=kind, payload=payload)

    def correlate(self, role, message, kind, request_id):
        if type(message) is not dict or set(message) != {'version','session','boot_id','role','request_id','kind','payload'}:
            raise ValueError('invalid control envelope fields')
        if (type(message['version']) is not int or message['version'] != 1 or
                type(message['request_id']) is not int or message['request_id'] != request_id or
                message['session'] != self.token or message['boot_id'] != self.owner.boot_id or
                message['role'] != role or message['kind'] != kind):
            raise ValueError('control correlation mismatch')
        return message['payload']

    def tick(self, deadline):
        now = time.monotonic()
        gap = now-self.ticks[-1]
        self.ticks.append(now)
        if gap > .1:
            raise TimeoutError('S1 monitor tick overrun')
        if now >= deadline:
            raise TimeoutError('S1 phase deadline reached')
        if self.owner.errors and not self.owner.cancelled:
            raise RuntimeError(str(self.owner.errors))
        if self.owner.cancelled or self.poisoned:
            raise RuntimeError('S1 helper session poisoned: '+str(self.owner.errors))
        found = []
        for role in ('work', 'sample') if len(self.ticks)%2 else ('sample', 'work'):
            try:
                message = self.pending_ready.pop(role, None)
                if message is None:
                    message = self.wires[role].tick()
                received = time.monotonic()
                if received >= deadline:
                    raise TimeoutError('S1 phase deadline reached at receipt')
                if received-now > .1:
                    raise TimeoutError('S1 control tick overrun')
                request = self.requests[role]
                if request and received >= request['deadline']:
                    raise TimeoutError('S1 resource sample timeout' if role == 'sample' else 'S1 work timeout')
                if message is None:
                    continue
                if role not in self.ready:
                    if received >= self.ready_deadline:
                        raise TimeoutError('S1 ready deadline reached')
                    payload = self.correlate(role, message, 'ready', 0)
                    expected = self.owner.records[role]
                    if expected.get('start_ticks') is None:
                        self.pending_ready[role] = message
                        continue
                    if (set(payload) != {'pid','pgid','start_ticks','threads'} or
                            any(type(payload[k]) is not int or payload[k] != expected.get(k) for k in ('pid','pgid','start_ticks')) or
                            payload['threads'] != {key:'1' for key in THREADS}):
                        raise ValueError('S1 ready ownership/thread mismatch')
                    self.ready[role] = payload
                    self.events.append(dict(event='ready', role=role, received=received, identity=payload))
                else:
                    if request is None:
                        raise ValueError('unsolicited helper response')
                    payload = self.correlate(role, message, 'response', request['id'])
                    if type(payload) is not dict or set(payload) != {'operation','ok','value','acquisition_start','acquisition_end'} or payload['operation'] != request['operation'] or type(payload['ok']) is not bool:
                        raise ValueError('invalid helper response payload')
                    if not payload['ok']:
                        raise RuntimeError('helper operation failed: '+str(payload['value']))
                    if role == 'sample':
                        validate_acquisition(payload, request['dispatch'], received, request['deadline'])
                    self.requests[role] = None
                    self.events.append(dict(event='response', role=role, request_id=request['id'], dispatch=request['dispatch'], received=received,
                        acquisition_start=payload['acquisition_start'], acquisition_end=payload['acquisition_end']))
                    found.append((role, payload['value'], received, request['dispatch']))
            except BaseException as exc:
                exc.helper_role = role
                exc.helper_pid = self.owner.records[role].get('pid')
                raise
        return found

    def await_ready(self):
        while len(self.ready) != 2:
            self.tick(self.ready_deadline)
            time.sleep(min(.005, max(0., self.ready_deadline-time.monotonic())))
        return self

    def submit(self, role, operation, deadline):
        now = time.monotonic()
        if self.poisoned or self.owner.cancelled or len(self.ready) != 2:
            raise ValueError('helper session unavailable')
        if self.requests[role] is not None:
            raise ValueError('helper role busy')
        if now >= deadline:
            raise TimeoutError('S1 work dispatch deadline')
        if type(operation) is not dict or set(operation) - {'operation','args'}:
            raise ValueError('invalid helper operation')
        name = operation['operation']
        allowed = ('resources', 'constant') if role == 'sample' else ('prelaunch','accept','reconcile','publish','constant')
        if name not in allowed or (name == 'constant' and os.environ.get('VIPE_CPU_VALIDATION') != '1'):
            raise ValueError('helper operation not permitted')
        self.sequences[role] += 1
        sequence = self.sequences[role]
        self.requests[role] = dict(id=sequence, operation=name, dispatch=now,
            deadline=min(deadline, now+1.) if role == 'sample' else deadline)
        self.wires[role].queue(self.envelope(role, sequence, 'request', operation))
        self.events.append(dict(event='dispatch', role=role, request_id=sequence, dispatch=now))

    def close(self, deadline):
        self.poisoned = self.owner.cancelled = True
        self.term_grace = min(.2, max(0., deadline-time.monotonic())/2)
        while (not self.owner.done or not self.owner.handle.is_done()) and time.monotonic() < deadline:
            time.sleep(min(.005, max(0., deadline-time.monotonic())))
        if self.owner.done and self.owner.handle.is_done():
            self.owner.handle.join(0)
            for wire in self.wires.values():
                wire.channel.close()
            self.closed = True
            if self.owner in OWNERS:
                OWNERS.remove(self.owner)
        return self.closed and self.owner.census_ok and all(r['state'] in ('pending','reaped') for r in self.owner.records.values())

    def ownership(self):
        return [dict(record, ownership_unknown=record['state']=='spawning' and not record.get('pid'))
                for record in self.owner.records.values() if record['state'] not in ('pending','reaped')]


def validate_acquisition(payload, dispatch, received, deadline):
    start, end = payload.get('acquisition_start'), payload.get('acquisition_end')
    if any(type(v) not in (int,float) or not math.isfinite(v) or v < 0 for v in (start,end,dispatch,received,deadline)):
        raise ValueError('invalid sample acquisition type/value')
    if not dispatch <= start <= end <= received or not received < min(dispatch+1., deadline):
        raise ValueError('invalid/stale/late sample acquisition interval')

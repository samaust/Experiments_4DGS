"""Fixed S1 CPU roles: bounded control transport and retained launch ownership.

The OS/native-thread boundary is measured, not asserted to be hard real time.
An unresolved launcher remains in OWNERS even after a timed-out caller returns.
"""
import _thread
from collections import deque
from dataclasses import dataclass
import hashlib
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

UINT64_MAX = (1 << 64) - 1


class Counter:
    def __init__(self):
        self.value = 0
        self.saturated = False
    def add(self, amount=1):
        if amount > UINT64_MAX-self.value:
            self.saturated = True
        self.value = min(UINT64_MAX, self.value+amount)


class Trace(deque):
    """Recent diagnostics; authority and primary failures never live here."""
    def __init__(self, capacity, *, errors=False):
        super().__init__(maxlen=capacity)
        self.total = Counter()
        self.dropped = Counter()
        self.first = self.last = None
        self.errors = errors
        self.primary = None
    def append(self, value):
        now = time.monotonic()
        if self.first is None: self.first = now
        self.last = now
        if self.errors:
            value = dict(value, message=str(value.get('message', ''))[:1024])
            if self.primary is None: self.primary = value
        if len(self) == self.maxlen: self.dropped.add()
        self.total.add()
        super().append(value)
    def extend(self, values):
        for value in values: self.append(value)
    def __getitem__(self, index):
        return list(self)[index] if isinstance(index, slice) else super().__getitem__(index)
    def facts(self):
        return dict(capacity=self.maxlen, total=self.total.value, dropped=self.dropped.value,
                    saturated=self.total.saturated or self.dropped.saturated, first=self.first, last=self.last)


@dataclass(frozen=True)
class ProcessIdentity:
    pid: int
    start_ticks: int
    pgid: int
    ppid: int
    state: str


@dataclass(frozen=True)
class Census:
    session: str
    boot_id: str
    generation: int
    request_id: int
    worker_generation: int
    acquisition_start: float
    completed: float
    status: str
    helpers: tuple
    worker: object
    rows: tuple
    exit_code: object = None
    exit_observed: object = None
    error: str = ''
    helper_rows: tuple = ()


def process_identity(row):
    for key in ('pid', 'start_ticks', 'pgid', 'ppid'):
        if type(row.get(key)) is not int or row[key] < (0 if key == 'ppid' else 1):
            raise ValueError('invalid process identity')
    if row.get('state') not in ('R','S','D','Z','T','t','X','I','W','P'):
        raise ValueError('invalid process state')
    return ProcessIdentity(**{k: row[k] for k in ('pid','start_ticks','pgid','ppid','state')})


def same_root(a, b):
    return a is not None and b is not None and (a.pid,a.start_ticks,a.pgid)==(b.pid,b.start_ticks,b.pgid)


class GPUOwnershipError(ValueError):
    pass


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
        self.io_saturated = False
        self.turn = False
        self.peek_bytes = Counter()
        self.combined_bytes = Counter()
        self.turn_sent = self.turn_received = self.turn_peek = 0
        self.last_frame = None

    def queue(self, message):
        if self.encoder is not None or self.out:
            raise ValueError('control writer busy')
        self.encoder = tokens(message)
        self.encoded = bytearray()

    def tick(self, request=None, *, allowance=IO_SLICE):
        self.turn_started = time.monotonic()
        self.turn = not self.turn
        self.turn_sent = self.turn_received = self.turn_peek = 0
        if type(allowance) is not int or not 0<allowance<=IO_SLICE: raise ValueError('invalid turn I/O allowance')
        remaining = allowance
        unfinished = request is not None and request.get('transmitted_observed') is None
        self.preturn_transmitted = not unfinished
        def peek(early=False):
            nonlocal remaining
            if not remaining: return False
            try: raw = self.channel.recv(1, socket.MSG_PEEK)
            except BlockingIOError: return True
            remaining -= len(raw)
            self.turn_peek += len(raw); self.peek_bytes.add(len(raw)); self.combined_bytes.add(len(raw))
            if raw:
                if early:
                    request['early_observed'] = time.monotonic()
                    request['early_bytes'] = len(raw)
                    raise ValueError('premature helper response before completed request turn')
                raise ValueError('unsolicited trailing control frame')
            raise EOFError('helper exited at complete frame')
        if unfinished: peek(early=True)
        if self.encoder is not None:
            budget = IO_SLICE
            for _ in range(256):
                if not self.encode_part:
                    try: self.encode_part = next(self.encoder).encode('ascii')
                    except StopIteration:
                        self.out = bytearray(struct.pack('!I', len(self.encoded))) + self.encoded
                        self.encoded = bytearray(); self.encoder = None
                        break
                    if len(self.encoded) + len(self.encode_part) > MAX_FRAME:
                        raise ValueError('encoded control frame limit')
                part = self.encode_part[:budget]
                self.encoded.extend(part); self.encode_part = self.encode_part[len(part):]
                budget -= len(part)
                if not budget: break
        def send(share):
            nonlocal remaining
            if not self.out or share <= 0: return
            entered = time.monotonic()
            if request is not None:
                request.setdefault('first_send_entered', entered)
                request['state'] = 'partially_sent'
            try:
                size = self.channel.send(memoryview(self.out)[:share])
                del self.out[:size]
                remaining -= size; self.turn_sent += size; self.combined_bytes.add(size)
                self.io_saturated |= self.sent_bytes+size>UINT64_MAX
                self.sent_bytes = min(UINT64_MAX,self.sent_bytes+size)
                if request is not None and not self.out:
                    request.update(state='transmitted', final_send_entered=entered,
                                   transmitted_observed=time.monotonic())
            except BlockingIOError:
                self.io_saturated |= self.blocked_writes==UINT64_MAX
                self.blocked_writes=min(UINT64_MAX,self.blocked_writes+1)
        def receive(share):
            nonlocal remaining
            if self.validator is not None or self.decoded is not None: return
            while share > 0:
                target = self.header if self.length is None else self.body
                needed = (4 if self.length is None else self.length)-len(target)
                try: chunk = self.channel.recv(min(needed,share))
                except BlockingIOError: return
                if not chunk: raise EOFError('helper EOF during transport')
                if self.length is not None: self.guard.feed(chunk)
                target.extend(chunk)
                remaining -= len(chunk); share -= len(chunk)
                self.turn_received += len(chunk); self.combined_bytes.add(len(chunk))
                self.io_saturated |= self.received_bytes+len(chunk)>UINT64_MAX
                self.received_bytes=min(UINT64_MAX,self.received_bytes+len(chunk))
                if self.length is None and len(self.header)==4:
                    self.length = struct.unpack('!I',self.header)[0]
                    if not 0 < self.length <= MAX_FRAME: raise ValueError('control advertised frame limit')
                if self.length is not None and len(self.body)==self.length:
                    self.decoded = decode(bytes(self.body),guarded=True)
                    self.last_frame = dict(bytes=4+len(self.body), sha256=hashlib.sha256(bytes(self.header+self.body)).hexdigest(), complete_observed=time.monotonic())
                    self.validator = tokens(self.decoded)
                    return
        # Each direction gets a first bounded share. Reserve a byte for mandatory peeks.
        for direction in (('send','receive') if self.turn else ('receive','send')):
            share = min(IO_SLICE//2, max(0,remaining-(1 if unfinished else 0)))
            if direction=='send': send(share)
            elif not unfinished: receive(share)
        if unfinished:
            peek(early=True)
            return None
        # Validate only frames completed on an earlier turn (bounded CPU work).
        if self.validator is not None and self.last_frame['complete_observed'] < self.turn_started:
            for _ in range(256):
                try: next(self.validator)
                except StopIteration:
                    self.validator = None
                    break
        if self.decoded is not None and self.validator is None and peek():
            value = self.decoded; self.decoded = None
            self.header.clear(); self.body.clear(); self.length = None
            self.guard = LexicalGuard()
            return value
        return None


def identity(pid):
    fields = Path('/proc', str(pid), 'stat').read_text().rsplit(')', 1)[1].split()
    return dict(pid=pid, pgid=int(fields[2]), start_ticks=int(fields[19]))


def census():
    rows = {}
    count = 0
    for entry in Path('/proc').iterdir():
        if entry.name.isdigit():
            count += 1
            if count > 16384: raise ValueError('census process capacity uncertainty')
            try:
                f = (entry/'stat').read_text().rsplit(')', 1)[1].split()
                rows[int(entry.name)] = dict(pid=int(entry.name), ppid=int(f[1]),
                    pgid=int(f[2]), start_ticks=int(f[19]), state=f[0])
            except (FileNotFoundError, ProcessLookupError):
                pass
    return rows


class InvocationRegistry:
    """One runner-owned identity registry; caller dictionaries cannot reset it."""
    def __init__(self):
        self.records={};self.anchor=None;self.lock=_thread.RLock()
    def register(self,pid,event='spawn'):
        with self.lock:
            # The returned PID is charged before the first fallible identity read.
            value=dict(boot_id=None,pid=pid,creation_parent=os.getpid(),creation_event=event,
                state='unresolved',threads=[pid])
            self.records[(None,pid,None)]=value
            boot=Path('/proc/sys/kernel/random/boot_id').read_text().strip()
            observed=identity(pid)
            value.update(observed,boot_id=boot,state='live')
            del self.records[(None,pid,None)]
            self.records[(boot,pid,observed['start_ticks'])]=value
            return value


INVOCATION = InvocationRegistry()


def owned_charge(B,H):
    if type(B) is not int or type(H) is not int or min(B,H)<0 or B+max(1,H)>8:
        raise ValueError('owned CPU thread ceiling')
    return B+max(1,H)


def predispatch_owned(event):
    observed=owned_workload(os.environ['S1_OWNED_ROOT_NOTE'])
    if observed['total_workers']+1>8:raise ValueError('owned '+event+' dispatch CPU capacity')
    return observed


def create_owned_process(event,create,*args,deadline=None,**kwargs):
    """Common real creation gate; callers retain the returned handle immediately."""
    if os.environ.get('S1_OWNED_ROOT_NOTE'):predispatch_owned(event)
    from .s1_progress import before
    before(deadline)
    return create(*args,**kwargs)


def register_owned(pid,event='spawn'):
    if os.environ.get('S1_OWNED_ROOT_NOTE'):
        return INVOCATION.register(pid,event)


def retire_owned(pid):
    """Called only after a matching child wait, including registration failure."""
    with INVOCATION.lock:
        for key,record in list(INVOCATION.records.items()):
            if record['pid']==pid:
                record.update(state='retired',retirement='matching child wait')
                if key[2] is None:del INVOCATION.records[key]


def validation_sources(repository):
    """Read the unchanged contract expression, including both current globs."""
    import ast
    tree=ast.parse((repository/'scripts/vipe_benchmark/s1_validation_contract.py').read_text())
    function=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='source_paths')
    expression=function.body[0].value
    if not isinstance(expression,ast.Call) or not isinstance(expression.func,ast.Name) or expression.func.id!='sorted':
        raise ValueError('owned source contract shape')
    items=expression.args[0].elts;paths=[]
    for item in items:
        if isinstance(item,ast.BinOp) and isinstance(item.left,ast.Name) and item.left.id=='ROOT':
            paths.append(repository/ast.literal_eval(item.right))
        elif isinstance(item,ast.Starred) and isinstance(item.value,ast.Call):
            call=item.value
            if not isinstance(call.func,ast.Attribute) or call.func.attr!='glob':raise ValueError('owned source glob')
            root=call.func.value
            if not isinstance(root,ast.BinOp) or not isinstance(root.left,ast.Name) or root.left.id!='ROOT':raise ValueError('owned source root')
            paths.extend((repository/ast.literal_eval(root.right)).glob(ast.literal_eval(call.args[0])))
        else:raise ValueError('owned source contract item')
    return sorted(paths)


def source_membership(records,repository):
    expected=[str(path) for path in validation_sources(repository)]
    if [record['path'] for record in records]!=expected:raise ValueError('owned source membership')
    return expected


def _launch_anchor(rows,boot,repository):
    import ast,hashlib,re
    run=repository/'docs/resolve-blocker/plan031-progress-20260922'
    def cmd(pid):return Path('/proc',str(pid),'cmdline').read_bytes().rstrip(b'\0').split(b'\0')
    cursor=os.getpid();seen=set()
    while cursor in rows and cursor not in seen:
        seen.add(cursor)
        argv=cmd(cursor)
        if len(argv)==3 and argv[1:]==[b'-B',b'-']:break
        cursor=rows[cursor]['ppid']
    else:raise ValueError('owned actual stdin runner unavailable')
    runner=cursor;capture=rows[runner]['ppid']
    if capture not in rows:raise ValueError('owned capture unavailable')
    interpreter=repository/'.local/envs/stg-colmap/bin/python'
    if Path(os.fsdecode(cmd(runner)[0])).resolve()!=interpreter.resolve() or Path('/proc',str(runner),'exe').resolve()!=interpreter.resolve():raise ValueError('owned runner interpreter')
    if Path('/proc',str(runner),'cwd').resolve()!=repository:raise ValueError('owned runner cwd')
    descriptor=Path('/proc',str(runner),'fd/0');stdin=Path(os.readlink(descriptor))
    directory=stdin.parent
    matched=re.fullmatch(r'(diagnostic|aggregate)-049-(\d{3,})',directory.name)
    if stdin.name!='stdin.py' or directory.parent!=run or not matched:raise ValueError('owned stdin location')
    kind,index=matched.groups()
    if int(index)<1:raise ValueError('owned positive attempt index')
    command=[str(interpreter),'-B','-m','vipe_benchmark.s1_validation_capture',str(directory),'--no-timeout']
    if kind=='diagnostic':command.append('--diagnostic')
    if cmd(capture)!=[v.encode() for v in command]:raise ValueError('owned capture argv')
    if Path('/proc',str(capture),'cwd').resolve()!=repository or Path('/proc',str(capture),'exe').resolve()!=interpreter.resolve():raise ValueError('owned capture identity')
    contract=ast.parse((repository/'scripts/vipe_benchmark/s1_validation_contract.py').read_text())
    expected=ast.literal_eval(next(n.value for n in contract.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='STDIN' for t in n.targets))).encode()
    named=stdin.stat();opened=descriptor.stat()
    if (named.st_dev,named.st_ino,named.st_size)!=(opened.st_dev,opened.st_ino,opened.st_size) or stdin.read_bytes()!=expected:raise ValueError('owned stdin descriptor identity')
    prefix=run/('driver-049-'+kind+'-'+index)
    start=json.loads(Path(str(prefix)+'-exec-start.json').read_bytes())
    for number,suffix in [(1,'-stdout.log'),(2,'-stderr.log')]:
        live=Path('/proc',str(capture),'fd',str(number)).stat();named=Path(str(prefix)+suffix).stat()
        if (live.st_dev,live.st_ino)!=(named.st_dev,named.st_ino) or start['logs'][str(number)]!={'device':live.st_dev,'inode':live.st_ino}:raise ValueError('owned driver log descriptor identity')
    note_path=run/('launch-note-049-'+kind+'-'+index+'.json')
    raw=note_path.read_bytes()
    if start['note']!={'path':str(note_path),'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}:raise ValueError('owned exec-start note correlation')
    return dict(runner=runner,capture=capture,note_path=str(note_path),raw=raw,directory=str(directory),command=command,stdin=(opened.st_dev,opened.st_ino,opened.st_size))


def thread_identity(pid,tid):
    fields=Path('/proc',str(pid),'task',str(tid),'stat').read_text().rsplit(')',1)[1].split()
    return dict(tid=tid,start_ticks=int(fields[19]))


def stable_process_identity(pid):
    """Complete live identity, rechecked around task enumeration."""
    boot=Path('/proc/sys/kernel/random/boot_id').read_text().strip()
    def process():
        fields=Path('/proc',str(pid),'stat').read_text().rsplit(')',1)[1].split()
        return dict(boot_id=boot,pid=pid,ppid=int(fields[1]),pgid=int(fields[2]),start_ticks=int(fields[19]))
    first=process()
    tids=sorted(int(path.name) for path in Path('/proc',str(pid),'task').iterdir())
    tasks=[dict(boot_id=boot,pid=pid,process_start_ticks=first['start_ticks'],**thread_identity(pid,tid)) for tid in tids]
    again=sorted(int(path.name) for path in Path('/proc',str(pid),'task').iterdir())
    repeated=[dict(boot_id=boot,pid=pid,process_start_ticks=first['start_ticks'],**thread_identity(pid,tid)) for tid in again]
    last=process()
    if first!=last or tasks!=repeated or not tasks or boot!=Path('/proc/sys/kernel/random/boot_id').read_text().strip():raise ValueError('unstable process/thread identity')
    return dict(first,threads=tasks,threads_before=[dict(task) for task in tasks],threads_after=repeated,process_before=first,process_after=last)


def creation_identity_snapshot(root_pid):
    """Fresh complete subtree census, with stable identity around enumeration."""
    rows=census();owned={root_pid}
    if root_pid not in rows:raise ValueError('creation root missing')
    for _ in range(len(rows)):
        additions={pid for pid,row in rows.items() if row['ppid'] in owned}-owned
        if not additions:break
        owned.update(additions)
    records=[stable_process_identity(pid) for pid in sorted(owned)]
    after=census();again={root_pid}
    for _ in range(len(after)):
        additions={pid for pid,row in after.items() if row['ppid'] in again}-again
        if not additions:break
        again.update(additions)
    if again!=owned:raise ValueError('creation subtree changed during enumeration')
    for record in records:
        pid=record['pid']
        if pid not in after or any(rows[pid][key]!=after[pid][key] or after[pid][key]!=record[key] for key in ('pid','ppid','pgid','start_ticks')):raise ValueError('creation PID identity changed')
    B=sum(len(record['threads']) for record in records)
    return dict(root_pid=root_pid,processes=records,B=B,H=0,charge=owned_charge(B,0),complete=True)


def owned_workload(note_path, *, extra=(), retained=None):
    """Kernel/dispatch anchor and persistent full-identity ownership at every call."""
    import hashlib
    with INVOCATION.lock:
        rows=census()  # Enumeration failure cannot be hidden by any caller note.
        boot=Path('/proc/sys/kernel/random/boot_id').read_text().strip()
        repository=Path(__file__).resolve().parents[2]
        if INVOCATION.anchor is None:
            INVOCATION.anchor=_launch_anchor(rows,boot,repository)
        anchor=INVOCATION.anchor
        fresh_anchor=_launch_anchor(rows,boot,repository)
        if fresh_anchor!=anchor:raise ValueError('owned live launch anchor changed')
        root_pid=anchor['capture']
        owned={root_pid}
        unresolved=[]
        for key,rec in INVOCATION.records.items():
            pid=rec['pid']
            if pid in rows:
                if key[2] is None or rows[pid]['start_ticks']!=key[2] or rows[pid]['pgid']!=rec['pgid']:
                    rec['state']='unresolved';unresolved.append(rec);continue
                owned.add(pid)
            elif key[2] is not None:
                # A complete matching identity previously seen, now absent from
                # a successful whole census, is retired without forgetting it.
                rec['state']='retired'
            else:unresolved.append(rec)
        for _ in range(len(rows)):
            added={pid for pid,row in rows.items() if row['ppid'] in owned}-owned
            if not added:break
            owned.update(added)
        for pid in extra:
            if type(pid) is not int or pid not in owned:raise ValueError('unproven detached ownership')
        records=[];threads={}
        for pid in sorted(owned):
            if pid not in rows:raise ValueError('owned process missing')
            row=rows[pid];process_before=identity(pid)
            tids=sorted(int(t.name) for t in Path('/proc',str(pid),'task').iterdir())
            if not tids or len(tids)!=len(set(tids)):raise ValueError('owned CPU thread ceiling enumeration ambiguity')
            task_identities=[dict(boot_id=boot,pid=pid,process_start_ticks=process_before['start_ticks'],**thread_identity(pid,tid)) for tid in tids]
            process_after=identity(pid)
            if process_before!=process_after or process_after!={k:row[k] for k in ('pid','pgid','start_ticks')}:raise ValueError('owned task identity changed')
            key=(boot,pid,row['start_ticks']);rec=INVOCATION.records.get(key,{})
            rec.update(boot_id=boot,**{k:row[k] for k in ('pid','ppid','pgid','start_ticks')},threads=tids,thread_identities=task_identities,process_before=process_before,process_after=process_after,state='live')
            rec.setdefault('creation_parent',row['ppid']);rec.setdefault('creation_event','owned descendant census')
            INVOCATION.records[key]=rec;records.append(dict(rec));threads[pid]=len(tids)
        B=sum(threads.values())+sum(max(1,len(r['threads'])) for r in unresolved);H=0
        owned_charge(B,H)
        if unresolved:raise ValueError('owned unresolved process identity blocks dispatch')
        raw=Path(note_path).read_bytes()
        if hashlib.sha256(raw).hexdigest()!=os.environ.get('S1_OWNED_ROOT_SHA256'):raise ValueError('owned root note digest')
        note=json.loads(raw)
        if str(note_path)!=anchor['note_path'] or raw!=anchor['raw']:raise ValueError('owned note differs from kernel anchor')
        if note.get('schema')!='plan049-prospective-launch/v1':raise ValueError('owned root schema')
        if note.get('execution_mode')!='no-timeout' or 'timeout_seconds' not in note or note['timeout_seconds'] is not None:raise ValueError('owned no-timeout mode')
        root=note['ownership_root']
        expected=dict(boot_id=boot,**{k:rows[root_pid][k] for k in ('pid','ppid','pgid','start_ticks')})
        if any(root.get(k)!=v for k,v in expected.items()) or any(type(root[k]) is not int for k in ('pid','ppid','pgid','start_ticks')):raise ValueError('owned capture root binding')
        from .s1_validation_contract import identity_record,no_timeout_launch
        identity_record(root)
        no_timeout_launch(dict(path=str(note_path),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest()),anchor['directory'],diagnostic=note['kind']=='diagnostic')
        if note['run_directory']!=anchor['directory'] or note['command']!=anchor['command']:raise ValueError('owned output/command binding')
        if os.environ.get('S1_OWNED_ROOT_NOTE')!=anchor['note_path'] or os.environ.get('S1_VALIDATION_RUN_DIRECTORY',anchor['directory'])!=anchor['directory']:raise ValueError('owned environment locator')
        run=repository/'docs/resolve-blocker/plan031-progress-20260922'
        dispatch_path=run/'implementation-dispatch-049.json';dispatch_raw=dispatch_path.read_bytes();dispatch=json.loads(dispatch_raw)
        dispatch_record=dict(path=str(dispatch_path),bytes=len(dispatch_raw),sha256=hashlib.sha256(dispatch_raw).hexdigest())
        status=dispatch['implementation_status_snapshot'];plan=dispatch['plan']
        if dispatch.get('schema')!='plan049-implementation-dispatch/v1' or plan['path']!=str(repository/'plans/plan_049.md') or status['path']!=str(run/'implementation-status-049.md'):raise ValueError('owned fixed Plan049 authority')
        if dispatch_record not in note['bindings'] or not any(rec['path']==plan['path'] and rec['sha256']==plan['sha256'] for rec in note['bindings']) or note['status']!={k:status[k] for k in ('bytes','sha256')}:raise ValueError('owned dispatch/plan/status binding')
        if note['cwd']!=str(repository) or str(run/'launch-049-exec.py')!=note['driver']['path']:raise ValueError('owned launch authority')
        source_membership(note['sources'],repository)
        for rec in note['bindings']+note['sources']+[note['driver'],status]:
            current=Path(rec['path']).read_bytes()
            if len(current)!=rec['bytes'] or hashlib.sha256(current).hexdigest()!=rec['sha256']:raise ValueError('owned source/dispatch bytes changed')
        ancestors=[];cursor=root['ppid'];seen=set()
        for recorded in note['preexisting_ancestors']:
            if cursor in seen or cursor!=recorded['pid'] or cursor not in rows:raise ValueError('owned truncated/cyclic ancestry')
            seen.add(cursor)
            expected=dict(boot_id=boot,**{k:rows[cursor][k] for k in ('pid','ppid','pgid','start_ticks')})
            if any(recorded[k]!=v for k,v in expected.items()) or recorded['start_ticks']>root['start_ticks']:raise ValueError('owned ancestry changed')
            ancestors.append(dict(recorded,exclusion_reason='pre-existing kernel ancestry'));cursor=rows[cursor]['ppid']
        if cursor!=0 or not ancestors or note['ancestry_terminal']!={'pid':ancestors[-1]['pid'],'ppid':0}:raise ValueError('owned incomplete ancestry termination')
        if note['retained_wrappers']:raise ValueError('unvalidated retained wrapper ownership')
        if retained is not None:
            retained.update({rec['pid']:dict(rec) for rec in records})
        return dict(processes=records,process_threads=threads,ancestors=ancestors,B=B,H=H,measured_total=B+H,reserve=max(0,1-H),total_workers=B+max(1,H),root=root,registry_identity=id(INVOCATION),unresolved=[])


class Owner:
    """Only this retained thread creates/reaps children and scans ownership."""
    def __init__(self, session):
        self.session = session
        self.cancelled = False
        self.done = False
        self.errors = Trace(32, errors=True)
        self.records = {role: dict(role=role, state='pending', pid=None) for role in ('work', 'sample')}
        self.members = {}
        self.groups = {}
        self.census_ok = False
        self.signals = Trace(128)
        self.census_request = self.census_reply = self.last_success = None
        self.census_generation = 0
        self.census_failures = Counter()
        self.worker_root = None
        self.worker_generation = 0
        self.worker_members = {}
        self.boot_id = None
        self.handle = None
        self.cancel_time = None
        self.progress_install = None
        self.progress_consumer = None
        self.progress_ready = False
        self.progress_error = None
        self.progress_request_id = None

    def spawn(self, role, actions, env):
        return create_owned_process('Owner.run '+role,os.posix_spawn,sys.executable,
            [sys.executable, '-B', '-m', 'vipe_benchmark.s1_cpu_helper', role, self.session.token, '100'],
            env,deadline=self.session.ready_deadline,file_actions=actions,setsid=True)

    def observe_identity(self, pid):
        return identity(pid)

    def observe(self):
        return census()

    def signal_group(self, pid, sig):
        os.killpg(pid, sig)

    def reap_child(self, pid):
        result=os.waitpid(pid, os.WNOHANG)
        if result[0]==pid:retire_owned(pid)
        return result

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
                env['OPENCV_FOR_THREADS_NUM'] = '1'
                try:
                    if os.environ.get('S1_OWNED_ROOT_NOTE'):
                        observed=predispatch_owned('Owner.run '+role)
                        self.session.events.append(dict(event='owned_dispatch',role=role,**observed))
                    from .s1_progress import before
                    before(self.session.ready_deadline)
                    pid = self.spawn(role, actions, env)
                except OSError:
                    self.records[role] = dict(role=role, state='pending', pid=None, failed=True)
                    raise
                # Publish returned PID before *any* fallible operation or seam.
                self.records[role] = dict(role=role, state='pid_owned', pid=pid)
                register_owned(pid,'Owner.run '+role)
                child.close()
                observed = self.observe_identity(pid)
                if observed['pgid'] != pid:
                    raise ValueError('spawn did not establish owned group')
                self.records[role] = dict(role=role, state='pid_owned', **observed)
                if self.cancelled:
                    break
            while True:
                self.maintain()
                self.maintain_progress()
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
            if self.progress_consumer is not None:
                self.progress_consumer.close()
            for pair in self.session.channels.values():
                try:
                    pair[1].close()
                except OSError:
                    pass
            self.done = True

    def maintain_progress(self):
        if self.cancelled or self.session.progress_cache.frozen: return
        if not self.session.progress_io_turn.acquire(False):return
        try:self._maintain_progress()
        finally:self.session.progress_io_turn.release()

    def _maintain_progress(self):
        if self.cancelled or self.session.progress_cache.frozen:return
        from .s1_progress import Consumer, process_binding
        def bindings(producer):
            if producer == 'worker':
                root=self.worker_root
                if root is None or self.worker_generation != 1: return None
                return (dict(pid=root.pid,start_ticks=root.start_ticks,pgid=root.pgid),1)
            if self.progress_request_id is None: return None
            return (process_binding(self.records['work']),self.progress_request_id)
        try:
            if self.progress_install is not None and self.progress_consumer is None:
                self.progress_consumer=Consumer(self.progress_install,self.session.progress_cache,
                    lambda:self.cancelled,bindings)
                if self.progress_consumer.context['session'] != self.session.token or self.progress_consumer.context['work'] != process_binding(self.records['work']):
                    raise ValueError('progress installed context differs from retained owner')
                self.progress_ready=True
            if self.progress_consumer is not None: self.progress_consumer.tick()
        except BaseException as exc:
            self.progress_error=dict(error_class=type(exc).__name__,message=str(exc)[:1024])
            self.session.progress_cache.freeze(exc,integrity=not isinstance(exc,(TimeoutError,BlockingIOError)))

    def lineage(self, rows, roots, previous):
        children = {}
        for row in rows.values(): children.setdefault(row['ppid'], []).append(row['pid'])
        owned = set(roots) | set(previous)
        owned.update(pid for pid,row in rows.items() if row['pgid'] in roots)
        work = list(owned)
        while work:
            if len(owned)>64: raise ValueError('census lineage capacity uncertainty')
            for pid in children.get(work.pop(), ()):
                if pid not in owned: owned.add(pid); work.append(pid)
        members = {pid:rows[pid] for pid in owned if pid in rows}
        for pid,old in previous.items():
            if pid in rows and (rows[pid]['start_ticks'],rows[pid]['pgid']) != (old['start_ticks'],old['pgid']):
                raise ValueError('owned descendant identity changed')
        return members

    def maintain(self):
        request = self.census_request
        started = time.monotonic()
        try:
            exited = None; exit_observed = None
            if request and request['worker_pid'] is not None:
                # WNOWAIT retains the direct-child pin through all active phases.
                exited = os.waitid(os.P_PID,request['worker_pid'],os.WEXITED|os.WNOHANG|os.WNOWAIT)
                exit_observed = time.monotonic() if exited is not None else None
            started = time.monotonic()
            rows = self.observe()
            leaders = {r['pid'] for r in self.records.values() if r.get('pid') and r['state']!='reaped'}
            self.members = self.lineage(rows,leaders,self.members)
            self.census_ok = True
            if request and not self.cancelled:
                helpers = []
                for role in ('work','sample'):
                    retained = self.records[role]
                    row = rows.get(retained.get('pid'))
                    if row is None or retained.get('start_ticks') != row['start_ticks'] or row['pgid'] != row['pid']:
                        raise ValueError('helper census identity mismatch')
                    helpers.append(process_identity(row))
                worker = None; relevant = {}
                if request['worker_pid'] is not None:
                    row = rows.get(request['worker_pid'])
                    if row is None or row['ppid'] != os.getpid() or row['pgid'] != row['pid']:
                        raise ValueError('worker census identity unknown')
                    worker = process_identity(row)
                    if self.worker_generation == request['worker_generation']:
                        if not same_root(worker,self.worker_root): raise ValueError('worker start identity changed')
                    else:
                        self.worker_root = worker; self.worker_generation = request['worker_generation']; self.worker_members = {}
                    relevant = self.lineage(rows,{worker.pid},self.worker_members)
                    self.worker_members = relevant
                else:
                    self.worker_root = None; self.worker_members = {}; self.worker_generation=request['worker_generation']
                if len(relevant)+len(self.members)>64: raise ValueError('census combined identity capacity uncertainty')
                snapshot = Census(self.session.token,self.boot_id,request['generation'],request['request_id'],
                    request['worker_generation'],started,time.monotonic(),'success',tuple(helpers),worker,
                    tuple(process_identity(row) for _,row in sorted(relevant.items())),
                    None if exited is None else (exited.si_status if exited.si_code==os.CLD_EXITED else -exited.si_status),exit_observed,
                    helper_rows=tuple(process_identity(row) for _,row in sorted(self.members.items())))
                self.last_success = snapshot
                self.census_reply = snapshot
                self.census_request = None
            if not self.cancelled: return
            now = time.monotonic()
            if self.cancel_time is None: self.cancel_time = now
            sig = signal.SIGTERM if now-self.cancel_time < self.session.term_grace else signal.SIGKILL
            for role,record in list(self.records.items()):
                pid = record.get('pid')
                if not pid or record['state']=='reaped': continue
                group = [v for v in self.members.values() if v['pgid']==pid and v['state']!='Z']
                escaped = [v for v in self.members.values() if v['pgid'] not in leaders and v['pid'] not in leaders]
                if escaped: raise RuntimeError('escaped descendant ownership unresolved')
                if group:
                    try: self.signal_group(pid,sig)
                    except ProcessLookupError: pass
                    self.signals.append(dict(pid=pid,signal=int(sig),monotonic=now))
                else:
                    observed=os.waitid(os.P_PID,pid,os.WEXITED|os.WNOHANG|os.WNOWAIT)
                    if observed is not None:
                        reaped,status=self.reap_child(pid)
                        if reaped==pid: self.records[role]=dict(record,state='reaped',wait_status=status)
        except BaseException as exc:
            self.census_ok=False
            self.census_failures.add()
            if request:
                self.census_reply=Census(self.session.token,self.boot_id,request['generation'],request['request_id'],
                    request['worker_generation'],started,time.monotonic(),'failed',(),None,(),error=str(exc)[:1024])
                self.census_request=None
            self.errors.append(dict(error_class=type(exc).__name__,message=str(exc),phase='helper_cleanup'))


class NativeNotStarted(RuntimeError):
    """Native adapter explicitly guarantees that no ownership thread started."""


class Session:
    def __init__(self, *, ready_seconds=1., setup_seconds=2., total_seconds=3., owner_factory=Owner):
        self.t0 = time.monotonic()
        self.cleanup_deadline = self.t0
        self.channels = {}; self.wires = {}; self.ready = {}; self.pending_ready = {}
        self.owner = self.handle = None
        self.state = 'not_started'; self.primary = None
        self.closed = False; self.poisoned = False; self.term_grace = .2
        self.requests = {'work':None,'sample':None}; self.sequences = {'work':0,'sample':0}
        self.events = Trace(256); self.ticks = Trace(128); self.ticks.append(self.t0)
        self.role_turn = False; self.last_tick = self.t0
        self.max_gap = self.max_turn = 0.
        self.dispatch_counts = {r:Counter() for r in self.requests}
        self.response_counts = {r:Counter() for r in self.requests}
        self.census_requests = Counter(); self.census_sequence = 0
        self.worker_pid = None; self.worker_generation = 0; self.worker_root = None
        self.last_sample = None; self.accepted_initial = False
        self.decision_clock = time.monotonic
        self.fixture_action_end = self.fixture_safety_end = None
        from .s1_progress import RetainedProgress
        self.progress_cache = RetainedProgress()
        self.progress_io_turn = _thread.allocate_lock()
        self.progress_context = None
        try:
            if not (0 < ready_seconds <= 1 and ready_seconds < setup_seconds <= 2 and setup_seconds < total_seconds <= 3):
                raise ValueError('invalid session setup cutoffs')
            self.ready_deadline=self.t0+ready_seconds; self.setup_deadline=self.t0+setup_seconds; self.cleanup_deadline=self.t0+total_seconds
            self.token=uuid.uuid4().hex
            self.owner=owner_factory(self)
            if not hasattr(_thread,'start_joinable_thread'):
                raise RuntimeError('S1 requires native joinable ownership thread')
            for role in ('work','sample'):
                pair=socket.socketpair(); self.channels[role]=pair
                self.wires[role]=Wire(pair[0])
            OWNERS.append(self.owner)
            self.state='launch_entered'
            self.handle=_thread.start_joinable_thread(self.owner.run,daemon=False)
            self.owner.handle=self.handle; self.state='running'
        except BaseException as exc:
            self.primary=dict(error_class=type(exc).__name__,message=str(exc)[:1024],phase='startup',cause=None if exc.__cause__ is None else dict(error_class=type(exc.__cause__).__name__,message=str(exc.__cause__)[:1024]))
            self.poisoned=True
            if self.owner is not None: self.owner.cancelled=True
            if self.state=='launch_entered' and not isinstance(exc,NativeNotStarted):
                self.state='launch_unknown'
            else:
                self.state='not_started'; self.close(self.cleanup_deadline)
            raise

    def install_progress(self, reference, deadline):
        if self.progress_context is not None: raise ValueError('progress context already installed')
        self.progress_context=reference
        self.owner.progress_install=reference
        while not self.owner.progress_ready:
            if self.owner.progress_error: raise ValueError(str(self.owner.progress_error))
            self.tick(deadline)
            time.sleep(min(.005,max(0.,deadline-time.monotonic())))
        return reference

    def resume(self):
        now=time.monotonic(); self.last_tick=now; self.ticks.append(now)
        self.events.append(dict(event='monitor_resume',monotonic=now))

    def set_worker(self, worker):
        pid=None if worker is None else worker.pid
        if pid==self.worker_pid: return
        if self.requests['sample'] is not None: raise ValueError('worker change during sample')
        if self.worker_generation>=UINT64_MAX: raise ValueError('worker generation exhausted')
        self.worker_generation+=1; self.worker_pid=pid; self.worker_root=None
        self.last_sample=None

    def retire_worker(self):
        # Terminal invalidation cannot be blocked by a failed outstanding sample.
        # Retain that bounded request for diagnostics; no later generation accepts it.
        self.retired_request=self.requests['sample']
        self.requests['sample']=None
        self.set_worker(None)
        self.events.append(dict(event='worker_retired',generation=self.worker_generation))

    def request_census(self, request, stage):
        if self.owner.census_request is not None: raise ValueError('census mailbox busy')
        if self.census_sequence>=UINT64_MAX: raise ValueError('census generation exhausted')
        self.census_sequence+=1; self.census_requests.add()
        request['census_generation']=self.census_sequence; request['stage']=stage
        self.owner.census_reply=None
        self.owner.census_request=dict(generation=self.census_sequence,request_id=request['id'],
            worker_generation=self.worker_generation,worker_pid=self.worker_pid)

    def validate_census(self, snap, request, decision):
        if not isinstance(snap,Census) or snap.status!='success': raise ValueError('required census failed/unknown')
        if any(type(v) is not int or not 0<v<=UINT64_MAX for v in (snap.generation,snap.request_id)) or type(snap.worker_generation) is not int or not 0<=snap.worker_generation<=UINT64_MAX:
            raise ValueError('invalid census generation type')
        if type(snap.session) is not str or type(snap.boot_id) is not str: raise ValueError('invalid census binding type')
        if (snap.session!=self.token or snap.boot_id!=self.owner.boot_id or
                snap.generation!=request['census_generation'] or snap.request_id!=request['id'] or
                snap.worker_generation!=self.worker_generation): raise ValueError('census binding mismatch')
        if any(type(v) not in (int,float) or not math.isfinite(v) for v in (snap.acquisition_start,snap.completed,decision)):
            raise ValueError('invalid census timestamp')
        if not request['dispatch']<=snap.acquisition_start<=snap.completed<=decision<request['deadline']:
            raise ValueError('stale census interval/deadline')
        if type(snap.rows) is not tuple or type(snap.helpers) is not tuple or type(snap.helper_rows) is not tuple or len(snap.rows)+len(snap.helper_rows)>64 or len(snap.helpers)!=2: raise ValueError('census identity capacity')
        if any(type(row) is not ProcessIdentity for row in (*snap.helpers,*snap.helper_rows,*snap.rows)): raise ValueError('invalid census immutable identity')
        helper_members={row.pid:row for row in snap.helper_rows}
        if any(not same_root(root,helper_members.get(root.pid)) for root in snap.helpers): raise ValueError('helper lineage roots absent')
        for role,row in zip(('work','sample'),snap.helpers):
            retained=self.ready[role]
            if (row.pid,row.start_ticks,row.pgid)!=(retained['pid'],retained['start_ticks'],retained['pgid']):
                raise ValueError('census retained helper mismatch')
        if self.worker_pid is None:
            if snap.worker is not None or snap.rows: raise ValueError('retired worker census')
        else:
            if snap.worker is None or snap.worker.pid!=self.worker_pid or snap.worker.pgid!=self.worker_pid or snap.worker.ppid!=os.getpid():
                raise ValueError('census captured worker mismatch')
            if self.worker_root is None: self.worker_root=snap.worker
            elif not same_root(self.worker_root,snap.worker): raise ValueError('census worker start mismatch')
        for row in (*snap.helpers,*snap.helper_rows,*snap.rows):
            process_identity(vars(row))
        if snap.exit_observed is not None and (type(snap.exit_observed) not in (int,float) or not math.isfinite(snap.exit_observed) or snap.exit_observed>snap.acquisition_start):
            raise ValueError('exit census not qualified')
        return snap

    def sample_authority(self, request, post, decision):
        pre=request['pre']; payload=request['candidate']; wire=request['transmitted_observed']
        if not (pre.generation<post.generation and pre.completed<=request['final_send_entered']<=payload['acquisition_start']<=payload['acquisition_end']<=post.acquisition_start and
                request['final_send_entered']<=wire<=request['response_observed']):
            raise ValueError('sample census bracket ordering')
        value=payload['value']; pids=value.get('gpu_pids') if type(value) is dict else None
        if type(pids) is not list or len(pids)>64 or any(type(v) is not int or v<=0 for v in pids) or len(set(pids))!=len(pids):
            raise ValueError('invalid S1 resource sample: gpu_pids')
        before={r.pid:r for r in pre.rows}; after={r.pid:r for r in post.rows}
        if pids and (pre.worker is None or post.worker is None): raise GPUOwnershipError('exclusive GPU access lost: no pinned worker')
        if self.worker_pid is not None and not same_root(pre.worker,post.worker): raise ValueError('worker bracket identity changed')
        for pid in pids:
            if not same_root(before.get(pid),after.get(pid)):
                raise GPUOwnershipError('exclusive GPU access lost: PID absent/changed across census bracket: '+str(pid))
        return dict(request_id=request['id'], dispatch=request['dispatch'], deadline=request['deadline'],
            pre=pre,post=post,acquisition_start=payload['acquisition_start'],acquisition_end=payload['acquisition_end'],decision=decision)

    def admission_guard(self):
        if (self.poisoned or self.state!='running' or self.owner is None or self.owner.cancelled or self.owner.errors or
                not self.owner.census_ok or len(self.ready)!=2 or not self.accepted_initial or self.last_sample is None):
            raise ValueError('S1 setup admission unhealthy')
        observed_members=self.owner.members
        for role in ('work','sample'):
            observed=observed_members.get(self.ready[role]['pid'])
            if observed is None or observed['state']=='Z' or any(observed[k]!=self.ready[role][k] for k in ('pid','pgid','start_ticks')):
                raise ValueError('S1 setup admission observed helper unhealthy')
            if any(self.ready[role][k]!=self.owner.records[role].get(k) for k in ('pid','pgid','start_ticks')):
                raise ValueError('S1 setup admission identity changed')
        if self.last_sample['post'].session!=self.token or self.last_sample['post'].boot_id!=self.owner.boot_id:
            raise ValueError('S1 setup admission binding mismatch')
        now=self.decision_clock()
        if type(now) not in (int,float) or not math.isfinite(now): raise ValueError('invalid admission decision time')
        if now>=self.setup_deadline: raise TimeoutError('S1 setup admission deadline reached')
        self.events.append(dict(event='admission_guard',decision=now,deadline=self.setup_deadline,request_id=self.last_sample['request_id']))
        return now

    def worker_exit(self):
        if self.last_sample is None or self.worker_pid is None: raise ValueError('worker census authority unavailable')
        snap=self.last_sample['post']
        if snap.worker_generation!=self.worker_generation or not same_root(snap.worker,self.worker_root):
            raise ValueError('worker census authority retired')
        if snap.exit_observed is None: return None
        if any(row.pid!=self.worker_pid and row.state!='Z' for row in snap.rows):
            raise RuntimeError('worker left a live child process')
        return snap.exit_code

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
        now=time.monotonic(); gap=now-self.last_tick; self.last_tick=now; self.ticks.append(now)
        self.max_gap=max(self.max_gap,gap)
        if gap>.1: raise TimeoutError('S1 monitor tick overrun')
        if self.fixture_action_end is not None: deadline=min(deadline,self.fixture_action_end)
        if now>=deadline: raise TimeoutError('S1 phase deadline reached')
        if self.owner.errors and not self.owner.cancelled: raise RuntimeError(str(list(self.owner.errors)))
        if self.owner.cancelled or self.poisoned: raise RuntimeError('S1 helper session poisoned: '+str(list(self.owner.errors)))
        found=[]; self.role_turn=not self.role_turn
        for role in (('work','sample') if self.role_turn else ('sample','work')):
            try:
                request=self.requests[role]
                if request and now>=request['deadline']:
                    raise TimeoutError('S1 resource sample timeout' if role=='sample' else 'S1 work timeout')
                if role=='sample' and request and request.get('stage') in ('pre','post'):
                    snap=self.owner.census_reply
                    if snap is not None:
                        decision=time.monotonic()
                        if decision>=request['deadline']: raise TimeoutError('S1 resource sample timeout at census decision')
                        self.validate_census(snap,request,decision)
                        if request['stage']=='pre':
                            request['pre']=snap; request['stage']='wire'
                            self.wires[role].queue(self.envelope(role,request['id'],'request',request['operation_payload']))
                        else:
                            authority=self.sample_authority(request,snap,decision)
                            decision=self.decision_clock()
                            if type(decision) not in (int,float) or not math.isfinite(decision) or decision<snap.completed:
                                raise ValueError('invalid final sample decision time')
                            if decision>=request['deadline'] or decision>=deadline:
                                raise TimeoutError('S1 resource sample timeout at census decision')
                            authority['decision']=decision
                            self.last_sample=authority
                            payload=request['candidate']
                            self.requests[role]=None
                            self.response_counts[role].add()
                            self.events.append(dict(event='response',role=role,request_id=request['id'],dispatch=request['dispatch'],received=decision,
                                acquisition_start=payload['acquisition_start'],acquisition_end=payload['acquisition_end'],pre_generation=request['pre'].generation,post_generation=snap.generation))
                            found.append((role,payload['value'],decision,request['dispatch']))
                            continue
                message=self.pending_ready.pop(role,None)
                if message is None:
                    context=request if request and request.get('stage','wire')=='wire' else None
                    # Never wait for owner I/O: keep cancellation/deadline ticks
                    # active, but do not overlap a final send/peek turn with a
                    # large metadata validation that can release/reacquire GIL.
                    if not self.progress_io_turn.acquire(False):continue
                    try:message=self.wires[role].tick(context)
                    finally:self.progress_io_turn.release()
                real_received=time.monotonic(); self.max_turn=max(self.max_turn,real_received-now)
                if self.max_turn>.1: raise TimeoutError('S1 control tick overrun')
                received=self.decision_clock() if message is not None else real_received
                if received>=deadline: raise TimeoutError('S1 phase deadline reached at receipt')
                if request and received>=request['deadline']:
                    raise TimeoutError('S1 resource sample timeout' if role=='sample' else 'S1 work timeout')
                if message is None: continue
                if role not in self.ready:
                    if received>=self.ready_deadline: raise TimeoutError('S1 ready deadline reached')
                    payload=self.correlate(role,message,'ready',0); expected=self.owner.records[role]
                    if expected.get('start_ticks') is None:
                        self.pending_ready[role]=message; continue
                    if (set(payload)!={'pid','pgid','start_ticks','threads'} or
                            any(type(payload[k]) is not int or payload[k]!=expected.get(k) for k in ('pid','pgid','start_ticks')) or
                            payload['threads']!={key:'1' for key in THREADS}): raise ValueError('S1 ready ownership/thread mismatch')
                    self.ready[role]=payload; self.events.append(dict(event='ready',role=role,received=received,identity=payload))
                else:
                    if request is None: raise ValueError('unsolicited helper response')
                    if request.get('transmitted_observed') is None: raise ValueError('premature helper response without transmission')
                    payload=self.correlate(role,message,'response',request['id'])
                    if type(payload) is not dict or set(payload)!={'operation','ok','value','acquisition_start','acquisition_end'} or payload['operation']!=request['operation'] or type(payload['ok']) is not bool:
                        raise ValueError('invalid helper response payload')
                    if not payload['ok']:
                        if type(payload['value']) is dict and payload['value'].get('error_class')=='ProgressIntegrityError':
                            from .s1_progress import ProgressIntegrityError
                            raise ProgressIntegrityError(payload['value'].get('message','progress integrity failure'))
                        raise RuntimeError('helper operation failed: '+str(payload['value']))
                    if role=='sample':
                        validate_acquisition(payload,request['dispatch'],received,request['deadline'])
                        request.update(candidate=payload,response_observed=received)
                        self.request_census(request,'post')
                    else:
                        self.requests[role]=None; self.response_counts[role].add()
                        self.events.append(dict(event='response',role=role,request_id=request['id'],dispatch=request['dispatch'],received=received,
                            acquisition_start=payload['acquisition_start'],acquisition_end=payload['acquisition_end']))
                        found.append((role,payload['value'],received,request['dispatch']))
            except BaseException as exc:
                exc.helper_role=role; exc.helper_pid=self.owner.records[role].get('pid')
                raise
        return found

    def await_ready(self):
        end=self.ready_deadline if self.fixture_action_end is None else min(self.ready_deadline,self.fixture_action_end)
        while len(self.ready)!=2:
            self.tick(end); time.sleep(min(.005,max(0.,end-time.monotonic())))
        return self

    def submit(self, role, operation, deadline):
        now=time.monotonic()
        if self.fixture_action_end is not None: deadline=min(deadline,self.fixture_action_end)
        if self.poisoned or self.owner.cancelled or len(self.ready)!=2: raise ValueError('helper session unavailable')
        if self.requests[role] is not None: raise ValueError('helper role busy')
        if now>=deadline: raise TimeoutError('S1 work dispatch deadline')
        if type(operation) is not dict or set(operation)-{'operation','args'}: raise ValueError('invalid helper operation')
        name=operation['operation']
        allowed=('resources','constant') if role=='sample' else ('prelaunch','accept','reconcile','publish','constant')
        if name not in allowed or (name=='constant' and os.environ.get('VIPE_CPU_VALIDATION')!='1'): raise ValueError('helper operation not permitted')
        if self.sequences[role]>=UINT64_MAX: raise ValueError('request sequence exhausted')
        self.sequences[role]+=1; sequence=self.sequences[role]; self.dispatch_counts[role].add()
        request=dict(id=sequence,operation=name,dispatch=now,deadline=min(deadline,now+1.) if role=='sample' else deadline,
                     state='queued',operation_payload=operation)
        self.requests[role]=request
        if role=='sample': self.request_census(request,'pre')
        else:
            if self.progress_context is not None and name in ('reconcile','accept'):
                self.owner.progress_request_id=sequence
                operation=dict(operation,args=dict(operation.get('args',{}),progress_context=self.progress_context,trusted_progress=self.progress_cache.reference()))
                request['operation_payload']=operation
            self.wires[role].queue(self.envelope(role,sequence,'request',operation))
        self.events.append(dict(event='dispatch',role=role,request_id=sequence,dispatch=now))

    def close(self, deadline):
        if self.fixture_safety_end is not None: deadline=min(deadline,self.fixture_safety_end)
        self.progress_cache.freeze('session close')
        self.poisoned=True
        if self.owner is not None: self.owner.cancelled=True
        if self.state in ('not_started','retired'):
            for pair in self.channels.values():
                for channel in pair: channel.close()
            self.closed=True; self.state='retired'
            if self.owner in OWNERS: OWNERS.remove(self.owner)
            return True
        self.term_grace=min(.2,max(0.,deadline-time.monotonic())/2)
        if self.handle is None:
            # A missing handle does not prove that native creation had no effect.
            self.state='launch_unknown'; return False
        self.state='retiring'
        while (not self.owner.done or not self.handle.is_done()) and time.monotonic()<deadline:
            time.sleep(min(.005,max(0.,deadline-time.monotonic())))
        if self.owner.done and self.handle.is_done():
            self.handle.join(0)
            for pair in self.channels.values():
                for channel in pair: channel.close()
            self.closed=True
            if self.owner in OWNERS: OWNERS.remove(self.owner)
        confirmed=self.closed and self.owner.census_ok and all(r['state'] in ('pending','reaped') for r in self.owner.records.values())
        if confirmed: self.state='retired'
        return confirmed

    def ownership(self):
        if self.state=='launch_unknown':
            return [dict(state=self.state,ownership_unknown=True,pid=None)] + ([] if self.owner is None else [dict(r) for r in self.owner.records.values() if r['state'] not in ('pending','reaped')])
        if self.owner is None: return []
        return [dict(record,ownership_unknown=record['state']=='spawning' and not record.get('pid'))
                for record in self.owner.records.values() if record['state'] not in ('pending','reaped')]


def validate_acquisition(payload, dispatch, received, deadline):
    start, end = payload.get('acquisition_start'), payload.get('acquisition_end')
    if any(type(v) not in (int,float) or not math.isfinite(v) or v < 0 for v in (start,end,dispatch,received,deadline)):
        raise ValueError('invalid sample acquisition type/value')
    if not dispatch <= start <= end <= received or not received < min(dispatch+1., deadline):
        raise ValueError('invalid/stale/late sample acquisition interval')

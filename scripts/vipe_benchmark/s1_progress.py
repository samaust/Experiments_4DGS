"""Bounded, source-bound S1 progress. Metadata recovery never reads raw arrays.

The retained owner is the only consumer. Durable disk visibility does not confer
trust: a generation becomes usable only through its credentialed notice and ack.
"""
from dataclasses import dataclass
from collections import deque
import contextvars
import functools
import hashlib
import json
import math
import os
from pathlib import Path
import socket
import stat
import struct
import threading
import time

SCHEMA = 's1-verified-progress/v2'
CHECKPOINT_BYTES = 1024 * 1024
SMALL_BYTES = 8192
CONTROL_BYTES = 4096
MAX_GENERATIONS = 1024
MAX_CANDIDATES = 2048
MAX_ENTRIES = 4096
MAX_SOURCES = 2048
MAX_METADATA = 32 * 1024 * 1024
MAX_ERRORS = 32


class ProgressIntegrityError(ValueError):
    pass


def keys(value, names):
    if type(value) is not dict or set(value) != set(names.split()):
        raise ValueError('progress exact schema keys')
    return value


def integer(value, low=0, high=2**64-1):
    if type(value) is not int or not low <= value <= high:
        raise ValueError('progress integer bound')
    return value


def number(value):
    try: valid = type(value) in (int, float) and math.isfinite(value) and value >= 0
    except OverflowError: valid = False
    if not valid:
        raise ValueError('progress finite time')
    return value


def reservation_deadline(reservation):
    """Pure early gate; full captured-clock/authority validation still follows."""
    if type(reservation) is not dict or reservation.get('event')!='reserve':raise ValueError('captured reserve event required')
    start=number(reservation.get('monotonic_start'));seconds=number(reservation.get('seconds'))
    if not 0<seconds<=3600:raise ValueError('captured reservation seconds')
    total=start+seconds;work=total-min(30.,seconds/4)
    if not start<work<total:raise ValueError('captured reservation window')
    return work


def digest(value):
    if type(value) is not str or len(value) != 64 or any(c not in '0123456789abcdef' for c in value):
        raise ValueError('progress hash')
    return value


def primitives(value, depth=0, count=None, *, max_depth=12, max_nodes=65536):
    count = [0] if count is None else count
    count[0] += 1
    if count[0] > max_nodes or depth > max_depth: raise ValueError('progress primitive capacity')
    if type(value) is dict:
        for key, item in value.items():
            if type(key) is not str: raise ValueError('progress key')
            primitives(key, depth+1, count, max_depth=max_depth, max_nodes=max_nodes); primitives(item, depth+1, count, max_depth=max_depth, max_nodes=max_nodes)
    elif type(value) in (list, tuple):
        for item in value: primitives(item, depth+1, count, max_depth=max_depth, max_nodes=max_nodes)
    elif type(value) is str:
        if 'prompts' in Path(value).parts:raise ValueError('forbidden evidence path')
        if len(value.encode()) > 2048: raise ValueError('progress string capacity')
    elif type(value) in (int, float):
        try:finite=math.isfinite(value)
        except OverflowError:finite=False
        if not finite:raise ValueError('progress nonfinite primitive')
    elif value is not None and type(value) is not bool: raise ValueError('progress primitive type')


def encode(value, limit=CHECKPOINT_BYTES):
    before()
    primitives(value)
    before()
    raw = (json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False)+'\n').encode()
    before()
    if len(raw) > limit: raise ValueError('progress byte capacity')
    return raw


def decode(raw, limit=CHECKPOINT_BYTES, *, max_depth=12, max_nodes=65536):
    before()
    if type(raw) is not bytes or len(raw) > limit: raise ValueError('progress byte capacity')
    # Bound nesting and token count before json materializes containers.
    depth = nodes = 0; quoted = escaped = False
    for byte in raw:
        if quoted:
            if escaped: escaped = False
            elif byte == 92: escaped = True
            elif byte == 34: quoted = False
        elif byte == 34: quoted = True; nodes += 1
        elif byte in (91,123):
            depth += 1; nodes += 1
            if depth > max_depth: raise ValueError('progress nesting capacity')
        elif byte in (93,125): depth -= 1
        elif byte == 44: nodes += 1
        if nodes > max_nodes: raise ValueError('progress token capacity')
    def pairs(items):
        result = {}
        for key, val in items:
            if key in result: raise ValueError('progress duplicate key')
            result[key] = val
        return result
    before()
    value = json.loads(raw, object_pairs_hook=pairs, parse_constant=lambda _: (_ for _ in ()).throw(ValueError('progress nonfinite')))
    before()
    primitives(value, max_depth=max_depth, max_nodes=max_nodes)
    before()
    return value


def canonical(path):
    value = str(path)
    if 'prompts' in Path(value).parts:raise ValueError('forbidden evidence path')
    if len(value.encode()) > 2048 or not value.startswith('/') or '\x00' in value:
        raise ValueError('progress canonical absolute path')
    if str(Path(value)) != value or any(p in ('.','..') for p in value.split('/')[1:]):
        raise ValueError('progress path alias')
    return Path(value)


def open_parent(path):
    path=canonical(path)
    before();fd=os.open('/',os.O_RDONLY|os.O_DIRECTORY)
    owned={fd}
    try:
        before()
        for part in path.parts[1:-1]:
            before();new=os.open(part,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW,dir_fd=fd)
            owned.add(new)
            # A failed close has uncertain kernel effect. Disown that descriptor
            # before the call, never blindly retry a possibly reused number.
            old=fd;fd=new;before();owned.remove(old)
            try:os.close(old)
            except BaseException as error:
                error.s1_uncertain_descriptors=tuple(sorted(set(getattr(error,'s1_uncertain_descriptors',()))|{old}))
                raise
            before()
        owned.remove(fd)
        return fd,path.name
    except BaseException:
        for descriptor in tuple(owned):
            owned.remove(descriptor)
            retire(os.close,descriptor)
        raise


def read_bytes(path, limit):
    before()
    parent, name = open_parent(path)
    try:
        before()
        fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent)
        try:
            before()
            opened = operation(os.fstat,fd)
            if not stat.S_ISREG(opened.st_mode) or opened.st_size > limit: raise ValueError('progress regular file capacity')
            before()
            with os.fdopen(fd, 'rb', buffering=0, closefd=False) as stream:
                raw = operation(stream.read,limit+1)
            before()
            after = operation(os.fstat,fd)
            named = operation(os.stat,name, dir_fd=parent, follow_symlinks=False)
            if (named.st_dev,named.st_ino)!=(opened.st_dev,opened.st_ino):raise ValueError('progress descriptor replacement')
            if (opened.st_dev,opened.st_ino,opened.st_size,opened.st_mtime_ns,opened.st_ctime_ns) != (after.st_dev,after.st_ino,after.st_size,after.st_mtime_ns,after.st_ctime_ns) or len(raw) != opened.st_size: raise ValueError('progress read mutation')
            before()
            return raw
        finally: retire(os.close,fd)
    finally: retire(os.close,parent)


def record(path, raw):
    before()
    result = dict(path=str(canonical(path)), bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())
    before()
    return result


def validate_record(value):
    keys(value, 'path bytes sha256')
    if type(value['path']) is not str:raise ValueError('progress path type')
    canonical(value['path']); integer(value['bytes']); digest(value['sha256'])
    return value


def read_record(value, limit=CHECKPOINT_BYTES):
    before()
    validate_record(value)
    raw = read_bytes(value['path'], limit)
    if record(value['path'], raw) != value: raise ValueError('progress accepted metadata changed')
    return decode(raw, limit)


def verified_bytes(value):
    """Fresh anchored bytes; a previous check or identical pathname grants nothing."""
    validate_record(value)
    raw = read_bytes(value['path'], value['bytes'])
    if record(value['path'], raw) != value:raise ValueError('progress source bytes changed')
    return raw


def checked_file_record(path,expected=None):
    path=Path(path).absolute()
    size = operation(path.stat).st_size
    result=record(path, read_bytes(path, size))
    if expected is not None and result['sha256']!=expected:raise ValueError('changed file: '+str(path))
    return result


def checked_verify_record(value):
    verified_bytes(value)
    return value


def checked_read_json(path):
    before()
    size = Path(path).stat().st_size
    before()
    raw = read_bytes(path, size)
    before()
    value = json.loads(raw)
    before()
    return value


def fsync_dir(path):
    parent, name = open_parent(path)
    try:
        before()
        fd = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent)
        try: operation(os.fsync,fd)
        finally: retire(os.close,fd)
    finally: retire(os.close,parent)


EVENTS = deque(maxlen=4096)
EVENT_DROPS = 0
EVENT_SEQUENCE = 0
_trace_binding=contextvars.ContextVar('s1_trace_binding',default=None)


def trace_event(phase, state):
    global EVENT_DROPS,EVENT_SEQUENCE
    if os.environ.get('VIPE_CPU_VALIDATION')!='1':return
    EVENT_SEQUENCE+=1
    if len(EVENTS)==EVENTS.maxlen:EVENT_DROPS+=1
    EVENTS.append(dict(index=EVENT_SEQUENCE,phase=phase,state=state,observed=time.monotonic(),correlation=_trace_binding.get()))


def trace_reset():
    global EVENT_DROPS,EVENT_SEQUENCE
    EVENTS.clear();EVENT_DROPS=EVENT_SEQUENCE=0


def trace_snapshot():
    return dict(events=list(EVENTS),overflow=EVENT_DROPS,valid=EVENT_DROPS==0)


def publication_boundary(stage):
    """Concrete I/O boundary; the following operation always remains real."""
    before()
    trace_event(stage,'boundary')
    before()


_deadline = contextvars.ContextVar('s1_original_work_deadline', default=None)


def before(deadline=None):
    deadline = _deadline.get() if deadline is None else deadline
    if deadline is None:return None
    now = time.monotonic()
    if now >= deadline:
        raise TimeoutError('progress original work deadline')
    return now


def operation(function, *args, deadline=None, **kwargs):
    """Gate both sides of one fallible operation; a late return grants no authority."""
    inherited = _deadline.get()
    active = inherited if deadline is None else deadline
    if inherited is not None and active is not None:active=min(inherited,active)
    token = _deadline.set(active)
    try:
        if active is not None:before(active)
        if active is not None:trace_event(getattr(function,'__name__','operation'),'start')
        if active is not None:before(active)
        value = function(*args, **kwargs)
        if active is not None:trace_event(getattr(function,'__name__','operation'),'completed')
        if active is not None:before(active)
        return value
    finally:
        _deadline.reset(token)


def with_deadline(function):
    """Carry an explicit original deadline into nested local evidence operations."""
    @functools.wraps(function)
    def run(*args, deadline=None, **kwargs):
        inherited = _deadline.get()
        effective = inherited if deadline is None else deadline
        if effective is None and kwargs.get('clock') is not None:effective=kwargs['clock'].work_deadline
        if effective is None and args and isinstance(args[0], Publisher):effective=getattr(args[0],'deadline',None)
        if inherited is not None and effective is not None:
            effective = min(inherited, effective)
        if effective is None:return function(*args, **kwargs)
        token = _deadline.set(effective)
        try:
            before(effective)
            result = function(*args, **kwargs)
            before(effective)
            return result
        finally:
            _deadline.reset(token)
    return run


class DeadlineSink:
    """Unbuffered sink: archive exception finalization cannot write after W."""
    def __init__(self, stream, deadline=None):
        self.stream, self.deadline = stream, deadline
    def write(self, data):
        count = operation(self.stream.write, data, deadline=self.deadline)
        if count != len(data):
            raise OSError('progress short write')
        return count
    def seek(self, *args):
        return operation(self.stream.seek, *args, deadline=self.deadline)
    def tell(self):
        return operation(self.stream.tell, deadline=self.deadline)
    def flush(self):
        return operation(self.stream.flush, deadline=self.deadline)
    def read(self, *args):
        return operation(self.stream.read, *args, deadline=self.deadline)
    def fileno(self):
        return self.stream.fileno()


@with_deadline
def write_exclusive(path, raw):
    parent, name = open_parent(path)
    stream = None
    fd = None
    try:
        publication_boundary('open')
        before()
        fd = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=parent)
        before()
        # No Python buffer can flush bytes during exception cleanup.
        stream = os.fdopen(fd, 'wb', buffering=0, closefd=False)
        publication_boundary('write')
        if operation(stream.write, raw) != len(raw):
            raise OSError('progress short write')
        publication_boundary('flush'); operation(stream.flush)
        publication_boundary('file_fsync'); operation(os.fsync, fd)
        publication_boundary('close'); operation(stream.close)
        publication_boundary('close_readback')
    finally:
        # Descriptor retirement is mandatory even if a syscall returned late.
        if stream is not None and not stream.closed:
            retire(publication_boundary,'descriptor_retirement')
            retire(stream.close)
        if fd is not None:
            retire(os.close,fd)
        retire(os.close,parent)
    if operation(read_bytes, path, len(raw)) != raw:
        raise ValueError('progress durable readback')
    return operation(record, path, raw)


def process_binding(value):
    return {key: value[key] for key in ('pid','start_ticks','pgid')}


def validate_process(value):
    keys(value, 'pid start_ticks pgid')
    for key in value: integer(value[key], 1, 2**31-1 if key in ('pid','pgid') else 2**64-1)
    if value['pid'] != value['pgid']: raise ValueError('progress process group')


def context_document(value):
    keys(value, 'schema root session boot_id owner_pid uid clock authorization work worker_generation sources frames')
    if value['schema'] != 's1-progress-context/v1': raise ValueError('progress context schema')
    if type(value['root']) is not str:raise ValueError('progress root type')
    canonical(value['root']); integer(value['owner_pid'],1,2**31-1); integer(value['uid'],0,2**32-1)
    if type(value['session']) is not str or len(value['session']) != 32 or any(c not in '0123456789abcdef' for c in value['session']): raise ValueError('progress session')
    from .s1_clock import ReservationClock
    clock = checked_clock_mapping(value['clock'])
    validate_record(value['clock']['request'])
    keys(value['clock']['reservation'],'sequence event_sha256')
    integer(value['clock']['reservation']['sequence']);digest(value['clock']['reservation']['event_sha256'])
    if type(value['boot_id']) is not str or len(value['boot_id']) != 36:raise ValueError('progress boot identity')
    if value['boot_id'] != clock.boot_id or value['worker_generation'] != 1 or type(value['worker_generation']) is not int: raise ValueError('progress boot/generation')
    validate_record(value['authorization']); validate_process(value['work'])
    keys(value['sources'], 'guard progress')
    for rec in value['sources'].values(): validate_record(rec)
    frames=value['frames']
    if type(frames) is not list or len(frames)!=15 or any(type(f) is not int for f in frames) or len(set(frames))!=15 or frames != sorted(frames) or sum(50<=f<150 for f in frames)!=10 or sum(150<=f<200 for f in frames)!=5: raise ValueError('progress admitted frames')
    return value


def prepare_context(local, clock, request, authorization, session, work, config, *, owner_pid=None):
    return _prepare_context(local,clock,request,authorization,session,work,config,owner_pid=owner_pid,deadline=clock.work_deadline)


@with_deadline
def _prepare_context(local, clock, request, authorization, session, work, config, *, owner_pid=None):
    """Called only by validated prelaunch work; no worker-owned path supplies it."""
    from .s1_helper_session import identity
    clock.observe()
    root = canonical(Path(local)/'jobs'/('S1-progress-'+session))
    operation(root.mkdir,mode=0o700)
    for producer in ('worker','reconcile'):
        operation((root/producer).mkdir,mode=0o700); operation(fsync_dir,root/producer)
    value = dict(schema='s1-progress-context/v1', root=str(root), session=session, boot_id=clock.boot_id,
        owner_pid=os.getppid() if owner_pid is None else owner_pid, uid=os.getuid(), clock=clock.mapping(), authorization=authorization,
        work=process_binding(work or identity(os.getpid())), worker_generation=1,
        sources={k:operation(record,p,operation(read_bytes,p,CHECKPOINT_BYTES)) for k,p in (
            ('guard',Path(__file__).with_name('s1_evidence.py')),('progress',Path(__file__)))},
        frames=config['fit_snapshots']+config['selection_snapshots'])
    context_document(value)
    if operation(read_record,clock.mapping()['request'],256*1024) != request: raise ValueError('progress request binding')
    reference=write_exclusive(root/'context.json',operation(encode,value,SMALL_BYTES))
    operation(fsync_dir,root); operation(fsync_dir,root.parent); operation(read_record,reference,SMALL_BYTES); clock.observe()
    return reference


def identities(context):
    return [dict(branch='calibration',camera=c,frame=f,pair_start=None) for c in range(34) for f in context['frames']]


def identity_index(value, context):
    keys(value,'branch camera frame pair_start')
    integer(value['camera'],0,33); integer(value['frame'],50,199)
    if value['branch']!='calibration' or value['pair_start'] is not None or value['frame'] not in context['frames']: raise ValueError('progress identity membership')
    return value['camera']*15+context['frames'].index(value['frame'])


def counts(rows, *, complete=False):
    produced=[r['identity'] for r in rows]; qualified=[r['identity'] for r in rows if r['qualified']]
    fit=lambda values:sum(i['frame']<150 for i in values)
    return dict(expected=510, complete=510 if complete else 0, produced=510 if complete else 'unknown',
        qualified_total=510 if complete else 'unknown', produced_lower_bound=len(produced), qualified=len(qualified),
        fit_expected=340,selection_expected=170,fit_produced_lower_bound=fit(produced),
        selection_produced_lower_bound=len(produced)-fit(produced),fit_qualified=fit(qualified),selection_qualified=len(qualified)-fit(qualified))


def coverage_transition(previous, current):
    allowed = {'sealed','closed','incomplete','conflict','overflow'}
    if previous not in allowed or current not in allowed:
        raise ValueError('progress coverage')
    if previous == 'sealed' and current != 'sealed':
        raise ValueError('progress sealed coverage regression')
    if previous == 'conflict' and current != 'conflict':
        raise ValueError('progress conflict regression')
    if previous == 'overflow' and current not in ('overflow','conflict'):
        raise ValueError('progress overflow regression')
    return current


def validate_diagnostics(value):
    keys(value,'dropped first last primary');integer(value['dropped'])
    for name in ('first','last','primary'):
        item=value[name]
        if item is None:continue
        keys(item,'error_class message phase observed')
        for field,limit in [('error_class',128),('message',1024),('phase',96)]:
            if type(item[field]) is not str or len(item[field].encode())>limit:
                raise ValueError('progress diagnostic string capacity')
        number(item['observed'])
    if (value['first'] is None)!=(value['last'] is None):raise ValueError('progress diagnostic observation pair')
    if value['first'] is None:
        if value['primary'] is not None or value['dropped'] != 0:raise ValueError('progress no-failure diagnostics')
    elif value['primary'] != value['first']:
        raise ValueError('progress original primary diagnostics')
    if value['first'] is not None and value['last']['observed']<value['first']['observed']:
        raise ValueError('progress diagnostic observation order')
    return value


def diagnostic_transition(old, new):
    validate_diagnostics(old);validate_diagnostics(new)
    if new['dropped']<old['dropped']:raise ValueError('progress diagnostic drop regression')
    for key in ('first','primary'):
        if old[key] is not None and new[key]!=old[key]:raise ValueError('progress diagnostic '+key+' regression')
    if old['last'] is not None and (new['last'] is None or new['last']['observed']<old['last']['observed']):
        raise ValueError('progress diagnostic last regression')


def acceptance_transition(old,new):
    if old['acceptance'] is not None and old['acceptance']!=new['acceptance']:
        raise ValueError('progress acceptance regression')


def publication_capacity(*, generations, committed_bytes, tree_entries, retained_bytes):
    """One production preallocation check, independent of disk enumeration."""
    integer(generations,0,2048);integer(committed_bytes,0,2*1024**3)
    integer(tree_entries,0,2057);integer(retained_bytes,0,4*1024**2)


def validate_checkpoint(value, context, reference):
    keys(value,'schema context producer binding request_id sequence previous work_deadline verified_at rows sources coverage errors diagnostics runtime first_result acceptance counts')
    validate_record(value['context'])
    number(value['work_deadline'])
    if value['schema']!=SCHEMA or value['context']!=reference or value['producer'] not in ('worker','reconcile'): raise ValueError('progress checkpoint binding')
    validate_process(value['binding']); integer(value['request_id'],1); integer(value['sequence'],1,MAX_GENERATIONS)
    if value['producer']=='worker' and value['request_id']!=1: raise ValueError('progress worker generation')
    if value['producer']=='reconcile' and value['binding']!=context['work']: raise ValueError('progress work identity')
    if value['previous'] is not None: validate_record(value['previous'])
    if (value['sequence']==1)!=(value['previous'] is None):raise ValueError('progress initial previous binding')
    if value['work_deadline']!=context['clock']['work_deadline'] or number(value['verified_at'])>=value['work_deadline'] or value['verified_at']<context['clock']['monotonic_start']: raise ValueError('progress verification time')
    if value['coverage'] not in ('sealed','closed','incomplete','conflict','overflow'): raise ValueError('progress coverage')
    if value['producer']=='worker' and value['coverage']!='sealed':raise ValueError('progress worker coverage')
    rows=value['rows']; sources=value['sources']
    if type(rows) is not list or len(rows)>510 or type(sources) is not list or len(sources)>4096: raise ValueError('progress entries capacity')
    seen=set()
    for rec in sources:
        validate_record(rec); key=tuple(rec[k] for k in ('path','bytes','sha256'))
        if key in seen: raise ValueError('progress duplicate source')
        seen.add(key)
    order=[]
    for row in rows:
        keys(row,'identity version row source_indices qualified authority')
        order.append(identity_index(row['identity'],context)); digest(row['version']); validate_record(row['row'])
        if type(row['qualified']) is not bool: raise ValueError('progress qualified bool')
        indices=row['source_indices']
        if type(indices) is not list or len(indices)>4096 or any(type(i) is not int for i in indices) or len(set(indices))!=len(indices): raise ValueError('progress source indices')
        for i in indices: integer(i,0,len(sources)-1)
        authority=row['authority'];keys(authority,'producer context guard version worker_reference')
        if authority['producer'] not in ('worker','reconcile') or authority['context']!=reference['sha256'] or authority['guard']!=context['sources']['guard']['sha256'] or authority['version']!=row['version']: raise ValueError('progress seal')
        if authority['producer']=='worker' and value['producer']=='reconcile':validate_record(authority['worker_reference'])
        elif authority['worker_reference'] is not None: raise ValueError('progress unexpected worker reference')
        if authority['producer']=='reconcile' and value['coverage'] not in ('closed','conflict','overflow'):raise ValueError('progress unclosed authority')
    if order!=sorted(set(order)):raise ValueError('progress identity order/duplicate')
    validate_diagnostics(value['diagnostics'])
    if type(value['errors']) is not list or len(value['errors'])>MAX_ERRORS:raise ValueError('progress errors capacity')
    if bool(value['errors']) != (value['diagnostics']['first'] is not None):raise ValueError('progress failure diagnostics alternative')
    for err in value['errors']:
        if type(err) is not str or len(err.encode())>1024:raise ValueError('progress error size')
    if type(value['runtime']) is not dict or set(value['runtime'])-{'initial-runtime.json','partial-runtime.json','final'}:raise ValueError('progress runtime capacity')
    for rec in value['runtime'].values():validate_record(rec)
    for name in ('first_result','acceptance'):
        if value[name] is not None:validate_record(value[name])
    complete=value['acceptance'] is not None
    if complete and (len(rows)!=510 or not all(r['qualified'] for r in rows) or value['coverage']!='closed' or value['errors'] or value['diagnostics']['primary'] is not None or value['diagnostics']['dropped']):raise ValueError('progress invalid complete acceptance')
    keys(value['counts'],' '.join(counts(rows,complete=complete)))
    if value['counts']!=counts(rows,complete=complete) or any(type(value['counts'][k]) is not type(v) for k,v in counts(rows,complete=complete).items()):raise ValueError('progress counts')
    return value



def validate_head(value):
    keys(value,'schema context producer sequence current previous')
    if value['schema']!='s1-progress-head/v1' or value['producer'] not in ('worker','reconcile'):raise ValueError('progress head schema')
    validate_record(value['context']);integer(value['sequence'],1,MAX_GENERATIONS);validate_record(value['current'])
    if value['previous'] is not None:validate_record(value['previous'])
    return value


def validate_notice(value):
    keys(value,'schema context producer binding request_id sequence current previous head completed')
    if value['schema']!='s1-progress-notice/v1' or value['producer'] not in ('worker','reconcile'):raise ValueError('progress notice schema')
    validate_record(value['context']);validate_process(value['binding']);integer(value['request_id'],1)
    integer(value['sequence'],1,MAX_GENERATIONS);number(value['completed'])
    for key in ('current','head'):validate_record(value[key])
    if value['previous'] is not None:validate_record(value['previous'])
    return value


def validate_ack(value):
    keys(value,'schema context producer sequence current')
    if value['schema']!='s1-progress-ack/v1' or value['producer'] not in ('worker','reconcile'):raise ValueError('progress ack schema')
    digest(value['context']);integer(value['sequence'],1,MAX_GENERATIONS);validate_record(value['current'])
    return value

def ack_correlation(value,expected):
    validate_ack(value)
    if value!=expected:raise ValueError('progress ack correlation')
    return value


def address(context, producer='owner'):
    value='\0s1-progress-'+context['session']+'-'+producer
    if len(value.encode())>96:raise ValueError('progress socket address capacity')
    return value


def mailbox(context, producer):
    channel=socket.socket(socket.AF_UNIX,socket.SOCK_DGRAM)
    try:
        channel.setblocking(False);channel.setsockopt(socket.SOL_SOCKET,socket.SO_PASSCRED,1)
        for option in (socket.SO_RCVBUF,socket.SO_SNDBUF):
            channel.setsockopt(socket.SOL_SOCKET,option,16384)
            if channel.getsockopt(socket.SOL_SOCKET,option)>32768:raise ValueError('progress kernel socket capacity')
        channel.bind(address(context,producer));return channel
    except BaseException:channel.close();raise


def receive(channel):
    raw, anc, flags, sender=channel.recvmsg(CONTROL_BYTES,socket.CMSG_SPACE(struct.calcsize('3i')))
    if flags & (socket.MSG_TRUNC|socket.MSG_CTRUNC):raise ValueError('progress truncated datagram')
    credentials=[struct.unpack('3i',data) for level,kind,data in anc if level==socket.SOL_SOCKET and kind==socket.SCM_CREDENTIALS and len(data)==12]
    if len(credentials)!=1:raise ValueError('progress sender credentials')
    return decode(raw,CONTROL_BYTES),credentials[0],sender


@dataclass(frozen=True)
class Snapshot:
    compact: bytes
    checkpoints: tuple


class RetainedProgress:
    """No fallible I/O under this short lock; monitor freezes one pointer."""
    def __init__(self):
        self.snapshot=None;self.frozen=False;self.integrity=None;self.lock=threading.RLock();self.pending={}
    def intended(self,producer,notice):
        with self.lock:
            if self.frozen:return False
            self.pending[producer]={k:notice[k] for k in ('binding','request_id','sequence','current','previous','head','completed')}
            return True
    def retain(self,snapshot):
        with self.lock:
            if self.frozen:return False
            self.snapshot=snapshot;return True
    def freeze(self,reason=None,*,integrity=False):
        with self.lock:
            self.frozen=True
            if integrity:self.integrity=str(reason)[:1024]
            return self.snapshot
    def acknowledge(self,snapshot,send):
        with self.lock:
            if self.frozen:return False
            previous=self.snapshot
            if not self.retain(snapshot):return False
            try:send()
            except BaseException:self.snapshot=previous;raise
            return True
    def reference(self):
        # Compact bounded metadata only. The bulk snapshot stays immutable.
        with self.lock:
            snap=self.snapshot;frozen=self.frozen;integrity=self.integrity;pending=dict(self.pending)
        if snap is None:return None
        value=decode(snap.compact,SMALL_BYTES)
        for producer,intent in pending.items():
            if producer in value['provenance'] and intent['current']!=value['checkpoints'][producer]:
                value['provenance'][producer]['intended_successor']=intent
        encode(value,SMALL_BYTES)
        value.update(frozen=frozen,integrity_status='failed' if integrity else 'verified',
            newest_status='unavailable' if frozen else 'acknowledged')
        return value


class Publisher:
    @property
    def coverage(self):return self._coverage
    @coverage.setter
    def coverage(self,value):
        old=getattr(self,'_coverage',None)
        if old is not None:
            if old=='conflict' and value=='overflow':
                self.failure(ValueError('overflow retained alongside conflict'));return
            coverage_transition(old,value)
        self._coverage=value
    @with_deadline
    def __init__(self,reference,producer,request_id,*,clock=None,request=None,trusted=None):
        if clock is None:raise ValueError('progress original clock required before context read')
        self.reference=reference;self.context=context_document(read_record(reference,SMALL_BYTES))
        if canonical(reference['path'])!=Path(self.context['root'])/'context.json':raise ValueError('progress context path')
        if clock is not None:clock_match(clock,self.context['clock'])
        if request is not None and read_record(self.context['clock']['request'],256*1024)!=request:raise ValueError('progress worker request')
        from .s1_helper_session import identity
        self.binding=process_binding(identity(os.getpid()));self.producer=producer;self.request_id=request_id
        self.deadline=self.context['clock']['work_deadline'];before(self.deadline)
        for rec in self.context['sources'].values():
            if record(rec['path'],read_bytes(rec['path'],CHECKPOINT_BYTES))!=rec:raise ValueError('progress source changed')
        self.channel=mailbox(self.context,producer);self.previous=None;self.sequence=0;self.rows={};self.sources=[]
        self.coverage='sealed' if producer=='worker' else 'incomplete';self.errors=[];self.runtime={};self.first_result=None;self.acceptance=None;self.stopped=False
        self.diagnostics=dict(dropped=0,first=None,last=None,primary=None);self.acknowledged_coverage=None;self.acknowledged_diagnostics=None
        self.inventory=None
        self.worker_authority=None
        if trusted is not None:
            recovered=recover(trusted)
            if trusted['context']!=reference or recovered['integrity_status']!='verified':raise ValueError('progress trusted context uncertainty')
            worker=trusted['checkpoints'].get('worker')
            if worker is not None:self.worker_authority=(worker,validate_checkpoint(read_record(worker),self.context,reference))
            prior=trusted['checkpoints'].get(producer)
            if prior is not None:
                doc=validate_checkpoint(read_record(prior),self.context,reference)
                self.previous=prior;self.sequence=doc['sequence'];self.rows={identity_index(r['identity'],self.context):r for r in doc['rows']}
                self.sources=doc['sources'];self.coverage=doc['coverage'];self.errors=doc['errors'];self.runtime=doc['runtime'];self.first_result=doc['first_result'];self.acceptance=doc['acceptance'];self.diagnostics=doc['diagnostics'];self.acknowledged_coverage=doc['coverage'];self.acknowledged_diagnostics=doc['diagnostics']
    def failure(self,error,phase='reconcile'):
        text=str(error).encode()[:1024].decode('utf-8','ignore')
        event=dict(error_class=type(error).__name__[:128],message=text,phase=phase[:96],observed=time.monotonic())
        if self.diagnostics['first'] is None:self.diagnostics['first']=event
        if self.diagnostics['primary'] is None:self.diagnostics['primary']=event
        self.diagnostics['last']=event
        if len(self.errors)<MAX_ERRORS:self.errors.append(text)
        else:self.diagnostics['dropped']=min(2**64-1,self.diagnostics['dropped']+1)
    def close(self):self.channel.close()
    def after_notice(self):
        pass
    @with_deadline
    def seal(self,row,row_record,*,qualified=False,worker_reference=None,publish=True):
        before(self.deadline)
        version=hashlib.sha256(operation(encode,row,256*1024)).hexdigest()
        index=identity_index(row['identity'],self.context)
        old=self.rows.get(index)
        if old and old['version']!=version:raise ValueError('progress conflicting authority')
        refs=[]
        def collect(value):
            if type(value) is dict:
                if set(value)=={'path','bytes','sha256'}:refs.append(validate_record(value));return
                for item in value.values():collect(item)
            elif type(value) is list:
                for item in value:collect(item)
        collect(row);indices=[]
        for ref in refs:
            if ref not in self.sources:
                if len(self.sources)>=4096:raise ValueError('progress sources overflow')
                self.sources.append(ref)
            indices.append(self.sources.index(ref))
        self.rows[index]=dict(identity=row['identity'],version=version,row=row_record,source_indices=sorted(set(indices)),
            qualified=qualified or bool(old and old['qualified']),authority=dict(producer='worker' if worker_reference else self.producer,
                context=self.reference['sha256'],guard=self.context['sources']['guard']['sha256'],version=version,worker_reference=worker_reference))
        return self.publish() if publish else None
    def publish(self):
        if self.stopped:raise ValueError('progress publisher stopped')
        try:return self._publish()
        except BaseException:self.stopped=True;raise
    @with_deadline
    def _publish(self):
        if self.inventory is not None:
            try:self.inventory.recheck(self.deadline)
            except TimeoutError:raise
            except Exception as exc:raise ProgressIntegrityError(str(exc)) from exc
        observed=before(self.deadline);sequence=self.sequence+1;integer(sequence,1,MAX_GENERATIONS)
        rows=[self.rows[k] for k in sorted(self.rows)]
        document=dict(schema=SCHEMA,context=self.reference,producer=self.producer,binding=self.binding,request_id=self.request_id,
            sequence=sequence,previous=self.previous,work_deadline=self.deadline,verified_at=observed,rows=rows,sources=self.sources,
            coverage=self.coverage,errors=self.errors,diagnostics=self.diagnostics,runtime=self.runtime,first_result=self.first_result,acceptance=self.acceptance,
            counts=counts(rows,complete=self.acceptance is not None))
        if self.acknowledged_coverage is not None:coverage_transition(self.acknowledged_coverage,self.coverage)
        if self.acknowledged_diagnostics is not None:diagnostic_transition(self.acknowledged_diagnostics,self.diagnostics)
        validate_checkpoint(document,self.context,self.reference);before(self.deadline);raw=operation(encode,document)
        publication_capacity(generations=sequence+MAX_GENERATIONS,committed_bytes=len(raw)+CHECKPOINT_BYTES*(sequence+MAX_GENERATIONS-1),tree_entries=sequence+MAX_GENERATIONS+9,retained_bytes=4*CHECKPOINT_BYTES)
        directory=Path(self.context['root'])/self.producer;target=directory/(str(sequence).zfill(4)+'.json');temp=directory/'checkpoint.tmp'
        before(self.deadline);write_exclusive(temp,raw,deadline=self.deadline);before(self.deadline)
        # link is an atomic no-replace install; all directory descriptors reject links.
        fd,name=open_parent(target)
        try:
            publication_boundary('generation_install');before(self.deadline)
            try:operation(os.link,'checkpoint.tmp',name,src_dir_fd=fd,dst_dir_fd=fd,follow_symlinks=False)
            except FileExistsError:
                if operation(read_bytes,target,CHECKPOINT_BYTES)!=raw:raise ValueError('progress generation collision')
            operation(os.unlink,'checkpoint.tmp',dir_fd=fd)
        finally:retire(os.close,fd)
        publication_boundary('generation_directory_fsync');before(self.deadline);operation(fsync_dir,directory)
        before(self.deadline);current=operation(record,target,raw);publication_boundary('generation_reopen_hash');operation(read_record,current);before(self.deadline)
        head=dict(schema='s1-progress-head/v1',context=self.reference,producer=self.producer,sequence=sequence,current=current,previous=self.previous)
        before(self.deadline);hraw=operation(encode,head,SMALL_BYTES);hpath=directory/'head.json';htemp=directory/'head.tmp'
        write_exclusive(htemp,hraw,deadline=self.deadline);before(self.deadline)
        fd,name=open_parent(hpath)
        try:
            publication_boundary('head_install');before(self.deadline)
            operation(os.replace,'head.tmp',name,src_dir_fd=fd,dst_dir_fd=fd)
        finally:retire(os.close,fd)
        publication_boundary('head_directory_fsync');before(self.deadline);operation(fsync_dir,directory)
        hrec=operation(record,hpath,hraw);publication_boundary('final_readback');before(self.deadline)
        publication_boundary('final_head_read');operation(read_record,hrec,SMALL_BYTES);before(self.deadline);publication_boundary('final_generation_read');operation(read_record,current)
        completed=before(self.deadline)
        notice=dict(schema='s1-progress-notice/v1',context=self.reference,producer=self.producer,binding=self.binding,request_id=self.request_id,
            sequence=sequence,current=current,previous=self.previous,head=hrec,completed=completed)
        encoded=operation(encode,notice,CONTROL_BYTES)
        publication_boundary('notice_send');before(self.deadline)
        if self.channel.sendto(encoded,address(self.context))!=len(encoded):raise OSError('progress notice short write')
        self.after_notice()
        end=min(self.deadline,completed+.5)
        while True:
            before(end)
            try:
                publication_boundary('ack_receipt:before');before(end);publication_boundary('ack_receipt');ack,credentials,sender=receive(self.channel);publication_boundary('ack_receipt:after');before(end)
            except BlockingIOError:time.sleep(min(.001,max(0,end-time.monotonic())));continue
            expected=dict(schema='s1-progress-ack/v1',context=self.reference['sha256'],producer=self.producer,sequence=sequence,current=current)
            ack_correlation(ack,expected)
            if ack!=expected or credentials[:2]!=(self.context['owner_pid'],self.context['uid']) or sender not in (address(self.context),address(self.context).encode()):raise ValueError('progress ack correlation')
            before(end);self.previous=current;self.sequence=sequence;self.acknowledged_coverage=self.coverage;self.acknowledged_diagnostics=decode(operation(encode,self.diagnostics));return current


class Consumer:
    def __init__(self,reference,cache,cancelled,bindings):
        self.reference=reference;self.context=context_document(read_record(reference,SMALL_BYTES));self.cache=cache
        self.cancelled=cancelled;self.bindings=bindings;self.current={};self.previous={};self.provenance={};self.channel=mailbox(self.context,'owner')
        self.buffers={name:self.channel.getsockopt(socket.SOL_SOCKET,option) for name,option in [('receive',socket.SO_RCVBUF),('send',socket.SO_SNDBUF)]}
    def close(self):self.channel.close()
    def check(self):
        if self.cancelled() or self.cache.frozen:raise InterruptedError('progress owner cancelled')
        before(self.context['clock']['work_deadline'])
    def stage(self,name):
        publication_boundary(name);self.check()
    def read(self,rec,limit=CHECKPOINT_BYTES):
        self.check();value=operation(read_record,rec,limit,deadline=self.context['clock']['work_deadline']);self.check();return value
    def tick(self):
        if self.cancelled() or self.cache.frozen:return
        token=_trace_binding.set(None)
        try:return operation(self._tick,deadline=self.context['clock']['work_deadline'])
        finally:_trace_binding.reset(token)
    def _tick(self):
        try:
            try:
                self.stage('dequeue:before');publication_boundary('notice_receive');notice,credentials,sender=receive(self.channel);self.stage('dequeue:after')
            except BlockingIOError:return
            self.stage('credentials:before');validate_notice(notice)
            producer=notice['producer']
            if producer not in ('worker','reconcile'):raise ValueError('progress producer')
            expected=self.bindings(producer)
            if (notice['schema']!='s1-progress-notice/v1' or notice['context']!=self.reference or expected is None or
                (notice['binding'],notice['request_id'])!=expected or credentials[:2]!=(expected[0]['pid'],self.context['uid']) or
                sender not in (address(self.context,producer),address(self.context,producer).encode())):raise ValueError('progress notice credential/correlation')
            _trace_binding.set(dict(session=self.context['session'],boot_id=self.context['boot_id'],reservation=self.context['clock']['reservation'],
                request=self.context['clock']['request'],producer=producer,binding=dict(expected[0]),request_id=notice['request_id'],
                sequence=notice['sequence'],current=notice['current'],work_deadline=self.context['clock']['work_deadline'],total_deadline=self.context['clock']['total_deadline']))
            self.stage('credentials:after')
            completed=number(notice['completed']);now=time.monotonic()
            if not self.context['clock']['monotonic_start']<=completed<self.context['clock']['work_deadline'] or now>=min(self.context['clock']['work_deadline'],completed+.5) or completed>now:raise TimeoutError('progress notice deadline')
            old=self.current.get(producer);sequence=integer(notice['sequence'],1,MAX_GENERATIONS)
            duplicate=old is not None and sequence==old[1]['sequence']
            if duplicate:
                if notice['current']!=old[0] or notice['previous']!=old[1]['previous']:raise ValueError('progress conflicting duplicate')
            elif sequence!=(1 if old is None else old[1]['sequence']+1) or notice['previous']!=(None if old is None else old[0]):raise ValueError('progress chain replay/regression')
            root=Path(self.context['root'])/producer
            if notice['current']['path']!=str(root/(str(sequence).zfill(4)+'.json')) or notice['head']['path']!=str(root/'head.json'):raise ValueError('progress foreign checkpoint path')
            if not duplicate:
                self.check();self.cache.intended(producer,notice);self.check()
            self.stage('context_read:before')
            if self.read(self.reference,SMALL_BYTES)!=self.context:raise ValueError('progress context mutation')
            self.stage('context_read:after')
            if old:
                self.stage('old_checkpoint_read:before');self.read(old[0]);self.stage('old_checkpoint_read:after')
            self.stage('head_read:before');head=validate_head(self.read(notice['head'],SMALL_BYTES));self.stage('head_read:after')
            if head!=dict(schema='s1-progress-head/v1',context=self.reference,producer=producer,sequence=sequence,current=notice['current'],previous=notice['previous']):raise ValueError('progress head correlation')
            self.stage('new_checkpoint_read:before');value=validate_checkpoint(self.read(notice['current']),self.context,self.reference);self.stage('new_checkpoint_read:after')
            if any(value[k]!=notice[k] for k in ('producer','binding','request_id','sequence','previous')) or value['verified_at']>completed:raise ValueError('progress notice/document correlation')
            if old:
                coverage_transition(old[1]['coverage'],value['coverage']);diagnostic_transition(old[1]['diagnostics'],value['diagnostics'])
                if any(error not in value['errors'] for error in old[1]['errors']) or old[1]['coverage']=='conflict' and value['coverage']!='conflict':raise ValueError('progress conflict/error regression')
                acceptance_transition(old[1],value)
                old_rows={identity_index(r['identity'],self.context):r for r in old[1]['rows']}
                new_rows={identity_index(r['identity'],self.context):r for r in value['rows']}
                if any(k not in new_rows or new_rows[k]['version']!=r['version'] or r['qualified'] and not new_rows[k]['qualified'] for k,r in old_rows.items()):raise ValueError('progress row regression')
                if old[1]['first_result'] is not None and value['first_result']!=old[1]['first_result'] or any(value['runtime'].get(k)!=v for k,v in old[1]['runtime'].items()):raise ValueError('progress state regression')
            if producer=='reconcile':
                self.stage('worker_authority_read:before');worker=self.current.get('worker')
                if worker is not None:self.read(worker[0])
                self.stage('worker_authority_read:after')
                for row in value['rows']:
                    if row['authority']['producer']!='worker':continue
                    if worker is None or row['authority']['worker_reference']!=worker[0]:raise ValueError('progress unacknowledged worker authority')
                    sealed=next((r for r in worker[1]['rows'] if r['identity']==row['identity']),None)
                    if sealed is None or any(row[k]!=sealed[k] for k in ('version','row','qualified')):
                        raise ValueError('progress worker authority mismatch')
                    if [value['sources'][i] for i in row['source_indices']] != [worker[1]['sources'][i] for i in sealed['source_indices']]:
                        raise ValueError('progress worker authority sources')
            proposed=dict(self.current);proposed[producer]=(notice['current'],value)
            merged={};runtime={};first=None
            for _,doc in proposed.values():
                for row in doc['rows']:
                    idx=identity_index(row['identity'],self.context);prior=merged.get(idx)
                    if prior and prior['version']!=row['version']:raise ValueError('progress conflicting producer authority')
                    if prior is None or row['qualified']:merged[idx]=row
                for key,ref in doc['runtime'].items():
                    if key in runtime and runtime[key]!=ref:raise ValueError('progress runtime conflict')
                    runtime[key]=ref
                if doc['first_result'] is not None:
                    if first is not None and first!=doc['first_result']:raise ValueError('progress first result conflict')
                    first=doc['first_result']
            provenance=dict(self.provenance)
            if not duplicate:
                provenance[producer]=dict(accepted_head=notice['head'],previous_checkpoint=None if old is None else old[0],previous_head=None if old is None else self.provenance[producer]['accepted_head'],intended_successor=None)
            compact=dict(schema='s1-progress-reference/v2',provenance=provenance,context=self.reference,session=self.context['session'],reservation=self.context['clock']['reservation'],
                checkpoints={p:r for p,(r,_) in proposed.items()},counts=counts([merged[k] for k in sorted(merged)],complete=any(d['acceptance'] is not None for _,d in proposed.values())),
                observed=time.monotonic(),frozen=False,integrity_status='verified',newest_status='acknowledged')
            retained={name:encode(doc) for name,(_,doc) in proposed.items()}
            for name,previous in self.previous.items():
                if previous is not None:retained[name+':previous']=encode(previous[1])
            if old is not None and not duplicate:retained[producer+':previous']=encode(old[1])
            publication_capacity(generations=sum(doc['sequence'] for _,doc in proposed.values()),committed_bytes=0,tree_entries=0,retained_bytes=sum(len(raw) for raw in retained.values()))
            snap=Snapshot(encode(compact,SMALL_BYTES),tuple(sorted(retained.items())))
            self.check();before(min(self.context['clock']['work_deadline'],completed+.5))
            ack=encode(dict(schema='s1-progress-ack/v1',context=self.reference['sha256'],producer=producer,sequence=sequence,current=notice['current']),CONTROL_BYTES)
            def send():
                if self.cancelled():raise InterruptedError('progress cancelled before ack')
                publication_boundary('ack_send:before')
                if self.cancelled():raise InterruptedError('progress cancelled before ack')
                publication_boundary('ack_send');before(min(self.context['clock']['work_deadline'],completed+.5))
                if self.channel.sendto(ack,sender)!=len(ack):raise OSError('progress ack short write')
                publication_boundary('ack_send:after')
                if self.cancelled():raise InterruptedError('progress cancelled after ack')
                before(min(self.context['clock']['work_deadline'],completed+.5))
            self.stage('retention:before');publication_boundary('owner_retention');self.check()
            self.stage('retention:after')
            if not self.cache.acknowledge(snap,send):return
            if not duplicate:self.previous[producer]=old
            self.current=proposed;self.provenance=provenance
        except InterruptedError:return
        except BaseException as exc:
            self.cache.freeze(exc,integrity=not isinstance(exc,(TimeoutError,BlockingIOError)))
            raise


def recover(reference):
    """Only an externally retained reference authorizes bounded cold readback."""
    keys(reference,'schema context session reservation checkpoints provenance counts observed frozen integrity_status newest_status')
    encode(reference,SMALL_BYTES)
    validate_record(reference['context']);number(reference['observed'])
    keys(reference['reservation'],'sequence event_sha256');integer(reference['reservation']['sequence']);digest(reference['reservation']['event_sha256'])
    if type(reference['frozen']) is not bool or reference['newest_status'] not in ('acknowledged','unavailable'):raise ValueError('progress reference state')
    if type(reference['session']) is not str or len(reference['session'])!=32:raise ValueError('progress reference session')
    if reference['schema']!='s1-progress-reference/v2' or reference['integrity_status']!='verified':raise ValueError('progress recovery unverified')
    context=context_document(read_record(reference['context'],SMALL_BYTES))
    if context['session']!=reference['session'] or context['clock']['reservation']!=reference['reservation']:raise ValueError('progress recovery correlation')
    refs=reference['checkpoints']
    if type(refs) is not dict or not refs or set(refs)-{'worker','reconcile'}:raise ValueError('progress recovery producers')
    provenance=reference['provenance']
    if type(provenance) is not dict or set(provenance)!=set(refs):raise ValueError('progress provenance producers')
    rows={};runtime={};first=None;errors=[];acceptance=None;uncertain=False;newest_unavailable=False
    coverages={};diagnostics={};sticky=False
    for producer,rec in refs.items():
        doc=validate_checkpoint(read_record(rec),context,reference['context'])
        if doc['producer']!=producer or rec['path']!=str(Path(context['root'])/producer/(str(doc['sequence']).zfill(4)+'.json')):raise ValueError('progress recovery path')
        proof=provenance[producer]
        keys(proof,'accepted_head previous_checkpoint previous_head intended_successor')
        validate_record(proof['accepted_head'])
        expected_head=dict(schema='s1-progress-head/v1',context=reference['context'],producer=producer,sequence=doc['sequence'],current=rec,previous=doc['previous'])
        head_path=Path(context['root'])/producer/'head.json'
        if proof['accepted_head']!=record(head_path,encode(expected_head,SMALL_BYTES)):
            raise ValueError('progress accepted head provenance changed')
        if (proof['previous_checkpoint'] is None)!=(proof['previous_head'] is None):raise ValueError('progress previous provenance pair')
        if proof['previous_checkpoint']!=doc['previous']:raise ValueError('progress previous provenance chain')
        if proof['previous_checkpoint'] is not None:
            validate_record(proof['previous_checkpoint']);validate_record(proof['previous_head'])
            previous=validate_checkpoint(read_record(proof['previous_checkpoint']),context,reference['context'])
            if previous['producer']!=producer or previous['sequence']+1!=doc['sequence'] or previous['binding']!=doc['binding']:
                raise ValueError('progress previous checkpoint provenance binding')
            previous_head=dict(expected_head,sequence=previous['sequence'],current=proof['previous_checkpoint'],previous=previous['previous'])
            if proof['previous_head']!=record(head_path,encode(previous_head,SMALL_BYTES)):
                raise ValueError('progress previous head provenance binding')
        intent=proof['intended_successor']
        if intent is not None:
            keys(intent,'binding request_id sequence current previous head completed')
            validate_notice(dict(schema='s1-progress-notice/v1',context=reference['context'],producer=producer,**intent))
            if intent['binding']!=doc['binding'] or intent['request_id']<doc['request_id'] or intent['sequence']!=doc['sequence']+1 or intent['current']['path']!=str(Path(context['root'])/producer/(str(intent['sequence']).zfill(4)+'.json')) or intent['previous']!=rec or not doc['verified_at']<=intent['completed']<doc['work_deadline']:
                raise ValueError('progress foreign successor provenance')
            expected_next=dict(expected_head,sequence=intent['sequence'],current=intent['current'],previous=rec)
            if intent['head']!=record(head_path,encode(expected_next,SMALL_BYTES)):
                raise ValueError('progress successor head provenance')
        try:
            head_raw=read_bytes(head_path,SMALL_BYTES)
            head=validate_head(decode(head_raw,SMALL_BYTES))
        except (FileNotFoundError,ValueError,json.JSONDecodeError):
            head=None;newest_unavailable=True
            if intent is None:uncertain=True
        if head is not None:
            current_head=record(head_path,head_raw)
            if current_head!=proof['accepted_head']:
                newest_unavailable=True
                if intent is None:raise ValueError('progress unproven head replacement')
                if current_head!=intent['head']:raise ValueError('progress cold head integrity/regression')
        for row in doc['rows']:
            idx=identity_index(row['identity'],context)
            if idx in rows and rows[idx]['version']!=row['version']:raise ValueError('progress recovery authority conflict')
            if idx not in rows or row['qualified']:rows[idx]=row
        for key,rec in doc['runtime'].items():
            if key in runtime and runtime[key]!=rec:raise ValueError('progress cold runtime conflict')
            runtime[key]=rec
        if first is not None and doc['first_result'] is not None and first!=doc['first_result']:raise ValueError('progress cold first conflict')
        first=first or doc['first_result'];errors.extend(doc['errors'])
        coverages[producer]=doc['coverage'];diagnostics[producer]=doc['diagnostics']
        sticky=sticky or doc['coverage'] in ('conflict','overflow') or bool(doc['diagnostics']['dropped'])
        if acceptance is not None and doc['acceptance'] is not None and acceptance!=doc['acceptance']:raise ValueError('progress cold acceptance conflict')
        acceptance=acceptance or doc['acceptance']
    ordered=[rows[k] for k in sorted(rows)]
    from .s1_clock import typed_equal
    if not typed_equal(reference['counts'],counts(ordered,complete=acceptance is not None)):raise ValueError('progress recovery counts')
    return dict(counts=counts(ordered,complete=acceptance is not None),acceptance=acceptance,integrity_status='uncertain' if uncertain else 'verified',stop_required=uncertain or sticky,produced_identities=[r['identity'] for r in ordered],qualified_identities=[r['identity'] for r in ordered if r['qualified']],
        runtime=runtime,first_result=first,verification_errors=errors[:32],coverage=coverages,diagnostics=diagnostics,scan_complete=acceptance is not None and not uncertain and not sticky and not newest_unavailable,verified_progress_reference=reference)



class ClosedInventory(list):
    def __init__(self,root=None):super().__init__();self.directories=[];self.root=None if root is None else canonical(root)
    def append(self,reference):
        if self.root is not None and not canonical(reference['path']).is_relative_to(self.root):raise ValueError('progress foreign candidate root')
        super().append(reference)
    def recheck(self,deadline=None):
        return operation(self._recheck,deadline,deadline=deadline)
    def _recheck(self,deadline=None):
        visited=0
        for path,dev,ino,names in self.directories:
            if deadline is not None:before(deadline)
            parent,name=open_parent(path)
            try:
                before();fd=os.open(name,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW,dir_fd=parent)
            finally:retire(os.close,parent)
            try:
                st=operation(os.fstat,fd);observed=[]
                before()
                with os.scandir(fd) as entries:
                    for entry in entries:
                        before();visited+=1
                        if visited>MAX_ENTRIES:raise ValueError('progress closure overflow')
                        observed.append(entry.name)
                if (st.st_dev,st.st_ino,tuple(sorted(observed)))!=(dev,ino,names):raise ValueError('progress inventory membership mutation')
            finally:retire(os.close,fd)
        for rec in self:
            if deadline is not None:before(deadline)
            raw=read_bytes(rec['path'],MAX_METADATA if rec['path'].endswith('/result.json') else 256*1024)
            if record(rec['path'],raw)!=rec:raise ValueError('progress inventory content mutation')
        if deadline is not None:before(deadline)


def inventory_capacity(name,value,maximum):
    """Production counter seam, including the exact value that was rejected."""
    if type(value) is not int or value<0 or value>maximum:
        error=ValueError('progress '+name+' overflow')
        error.counter=dict(name=name,value=value,maximum=maximum)
        raise error
    return value

def candidate_inventory(output, result, deadline):
    return operation(_candidate_inventory,output,result,deadline,deadline=deadline)


def _candidate_inventory(output, result, deadline):
    """Freeze a bounded no-follow inventory before crediting any unsealed row."""
    root=canonical(output);candidates=[];sources=ClosedInventory(root);errors=[];visited=total=0
    def append(source,row,rec):
        nonlocal total
        inventory_capacity('candidates',len(candidates)+1,MAX_CANDIDATES)
        raw=encode(row,256*1024);total+=len(raw)
        inventory_capacity('metadata_bytes',total,MAX_METADATA)
        candidates.append((source,row,rec,hashlib.sha256(raw).hexdigest()))
    try:
        raw=operation(read_bytes, root/'result.json', MAX_METADATA, deadline=deadline)
    except FileNotFoundError:
        if result is not None:raise
        raw=None
    if raw is not None:
        parsed=decode(raw, MAX_METADATA, max_depth=64, max_nodes=1048576)
        if result is None:result=parsed
        if type(result) is not dict or type(result.get('rows')) is not list:raise ValueError('progress result rows')
        inventory_capacity('candidates',len(result['rows']),MAX_CANDIDATES)
        from .s1_clock import typed_equal
        if not typed_equal(parsed,result):raise ValueError('progress result snapshot mismatch')
        inventory_capacity('inventory_sources',len(sources)+1,MAX_SOURCES)
        total+=len(raw)
        inventory_capacity('metadata_bytes',total,MAX_METADATA)
        rec=record(root/'result.json',raw);sources.append(rec)
        for row in result['rows']:
            if deadline is not None:before(deadline)
            append('result',row,rec)
    parent,name=open_parent(root)
    try:
        before();fd=os.open(name,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW,dir_fd=parent)
    finally:retire(os.close,parent)
    def walk(directory,path,depth):
        nonlocal visited
        observed=[];directory_identity=operation(os.fstat,directory)
        before()
        with os.scandir(directory) as entries:
            for entry in entries:
                if deadline is not None:before(deadline)
                observed.append(entry.name)
                visited+=1
                inventory_capacity('directory_entries',visited,MAX_ENTRIES)
                location=canonical(path/entry.name)
                if operation(entry.is_symlink):raise ValueError('progress inventory symlink')
                if operation(entry.is_dir,follow_symlinks=False):
                    if entry.name.endswith(('-produced-row.json','-qualified-row.json')):raise ValueError('progress directory candidate')
                    inventory_capacity('inventory_depth',depth+1,4)
                    before();child=os.open(entry.name,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW,dir_fd=directory)
                    try:walk(child,location,depth+1)
                    finally:retire(os.close,child)
                elif entry.name.endswith(('-produced-row.json','-qualified-row.json')):
                    inventory_capacity('inventory_sources',len(sources)+1,MAX_SOURCES)
                    st=operation(entry.stat,follow_symlinks=False)
                    if not stat.S_ISREG(st.st_mode) or st.st_nlink!=1:raise ValueError('progress candidate alias/nonregular')
                    raw=operation(read_bytes,location,256*1024,deadline=deadline);rec=record(location,raw);sources.append(rec)
                    append(str(location),decode(raw,256*1024),rec)
        sources.directories.append((str(path),directory_identity.st_dev,directory_identity.st_ino,tuple(sorted(observed))))
    try:walk(fd,root,0)
    finally:retire(os.close,fd)
    # Rehash the closed row inventory once, before any structural/semantic guard.
    sources.recheck(deadline)
    if deadline is not None:before(deadline)
    return candidates,sources


def publish_segment_row(row,request,loader,clock,publisher,produced_path,qualified_path,*,first=False):
    return operation(_publish_segment_row,row,request,loader,clock,publisher,produced_path,qualified_path,first=first,deadline=clock.work_deadline)


def _publish_segment_row(row,request,loader,clock,publisher,produced_path,qualified_path,*,first=False):
    """The actual segment boundary: structural commit/ack precedes semantics."""
    from .s1_evidence import produced_row, qualify_row
    clock.observe();row_record=write_exclusive(produced_path,encode(row,256*1024));clock.observe()
    if read_record(row_record,256*1024)!=row:raise ValueError('progress produced row readback')
    clock.observe();produced_row(row,request,loader=loader,deadline=clock.work_deadline);clock.observe()
    publisher.seal(row,row_record)
    clock.observe();checks=qualify_row(row,request,first=first,loader=loader,progress_context=publisher.reference,deadline=clock.work_deadline);clock.observe()
    write_exclusive(qualified_path,encode(row,256*1024));clock.observe()
    publisher.seal(row,row_record,qualified=True)
    return checks


def accepted_progress(publisher,result,result_record,acceptance):
    return _accepted_progress(publisher,result,result_record,acceptance,deadline=publisher.deadline)


@with_deadline
def _accepted_progress(publisher,result,result_record,acceptance):
    """Call only after actual acceptance guards; bind their immutable readback."""
    before(publisher.deadline)
    accepted=operation(read_record,acceptance)
    if accepted.get('result')!=result_record or accepted.get('status')!='passed' or accepted.get('count')!=510:
        raise ValueError('progress acceptance result binding')
    raw=operation(read_bytes,result_record['path'],MAX_METADATA)
    from .s1_clock import typed_equal
    if record(result_record['path'],raw)!=result_record or not typed_equal(decode(raw,MAX_METADATA,max_depth=64,max_nodes=1048576),result):raise ValueError('progress accepted result bytes')
    if len(result['rows'])!=510:raise ValueError('progress accepted row count')
    publisher.coverage='closed'
    for row in result['rows']:
        before(publisher.deadline)
        publisher.seal(row,result_record,qualified=True,publish=False)
    publisher.acceptance=acceptance
    publisher.first_result=accepted.get('first_result')
    # The exact result record is the bounded immutable runtime projection source.
    publisher.runtime['final']=result_record
    before(publisher.deadline);publisher.publish()


def summary_adapter(trusted, ordinary=None):
    """Independent acknowledged authority wins; verified conflicts fail closed."""
    if trusted is None:return ordinary
    if trusted.get('integrity_status') not in ('verified','uncertain'):raise ValueError('progress summary uncertainty')
    if trusted.get('integrity_status')=='uncertain' and trusted.get('stop_required') is not True:raise ValueError('progress summary uncertainty stop')
    result=dict(trusted)
    result['runtime']={k:dict(status='verified',value=validate_record(v)) for k,v in trusted['runtime'].items()}
    first=trusted['first_result']
    result['first_result']=dict(status='unverified' if first is None else 'verified',value=first)
    raw_errors=trusted.get('verification_errors',[])
    if type(raw_errors) is not list or len(raw_errors)>MAX_ERRORS:raise ValueError('progress summary error capacity')
    errors=list(raw_errors)
    if ordinary is not None:
        if type(ordinary) is not dict:raise ValueError('ordinary summary type')
        old_runtime=ordinary.get('runtime',{})
        if type(old_runtime) is not dict or len(old_runtime)>3:raise ValueError('ordinary runtime capacity')
        ordinary_errors=ordinary.get('verification_errors',[])
        if type(ordinary_errors) is not list or len(ordinary_errors)>MAX_ERRORS:raise ValueError('ordinary error capacity')
        for name,old in old_runtime.items():
            keys(old,'status value')
            if old['status'] not in ('verified','unverified'):raise ValueError('ordinary runtime status')
            if name not in ('initial-runtime.json','partial-runtime.json','final'):raise ValueError('ordinary runtime name')
            if old.get('status')=='verified':
                validate_record(old['value'])
                current=result['runtime'].get(name)
                if current is not None and current!=old:raise ValueError('progress summary runtime conflict')
            elif old['value'] is not None:raise ValueError('ordinary unverified runtime value')
                # Ordinary fields cannot establish independent durable authority.
        old=ordinary.get('first_result')
        if old is not None:
            keys(old,'status value')
            if old['status'] not in ('verified','unverified'):raise ValueError('ordinary first status')
            if old['status']=='verified':validate_record(old['value'])
            elif old['value'] is not None:raise ValueError('ordinary unverified first value')
        if old and old.get('status')=='verified' and first is not None and old['value']!=first:
            raise ValueError('progress summary first conflict')
        for error in ordinary.get('verification_errors',[]):
            if len(errors)>=MAX_ERRORS:break
            if error not in errors:errors.append(error)
    result['verification_errors']=errors
    return result

def checked_clock_mapping(value):
    from .s1_clock import ReservationClock, SCHEMA, number
    strict_record=checked_strict_record
    if not isinstance(value, dict) or set(value) != {'schema', 'job_id', 'request', 'reservation',
            'boot_id', 'monotonic_start', 'effective_seconds', 'cleanup_reserve_seconds',
            'total_deadline', 'work_deadline'} or value.get('schema') != SCHEMA:
        raise ValueError('invalid reservation clock mapping/schema')
    if value['job_id'] != 'S1-calibration-recovery-001' or type(value['job_id']) is not str:
        raise ValueError('invalid reservation clock job_id')
    record = strict_record(value['request'])
    ref = value['reservation']
    if (not isinstance(ref, dict) or set(ref) != {'sequence', 'event_sha256'}
            or type(ref['sequence']) is not int or ref['sequence'] < 0
            or type(ref['event_sha256']) is not str or len(ref['event_sha256']) != 64
            or any(c not in '0123456789abcdef' for c in ref['event_sha256'])):
        raise ValueError('invalid reservation clock reservation identity')
    if type(value['boot_id']) is not str or not value['boot_id'].strip():
        raise ValueError('invalid reservation clock boot_id')
    start = number(value['monotonic_start'], 'monotonic_start')
    total = number(value['effective_seconds'], 'effective_seconds', positive=True)
    cleanup = number(value['cleanup_reserve_seconds'], 'cleanup_reserve_seconds', positive=True)
    deadline = number(value['total_deadline'], 'total_deadline', positive=True)
    work = number(value['work_deadline'], 'work_deadline', positive=True)
    if (total > 3600 or cleanup != min(30., total / 4) or deadline != start + total
            or work != deadline - cleanup or not start < work < deadline):
        raise ValueError('invalid reservation clock derived window')
    return ReservationClock(value['job_id'], record['path'], record['sha256'], record['bytes'],
        ref['sequence'], ref['event_sha256'], value['boot_id'], start, total, cleanup, deadline, work)

def checked_clock_reservation(reservation):
    from .s1_clock import SCHEMA, number
    if not isinstance(reservation, dict) or reservation.get('event') != 'reserve':
        raise ValueError('reservation clock requires reserve event')
    value = dict(schema=SCHEMA, job_id=reservation.get('job_id'),
        request=reservation.get('evidence', {}).get('request'),
        reservation={k: reservation.get(k) for k in ('sequence', 'event_sha256')},
        boot_id=reservation.get('boot_id'), monotonic_start=reservation.get('monotonic_start'),
        effective_seconds=reservation.get('seconds'))
    start = number(value['monotonic_start'], 'monotonic_start')
    total = number(value['effective_seconds'], 'effective_seconds', positive=True)
    cleanup = min(30., total / 4)
    value.update(cleanup_reserve_seconds=cleanup, total_deadline=start + total,
                 work_deadline=start + total - cleanup)
    return checked_clock_mapping(value)
def checked_strict_record(value):
    validate_record(value)
    if 'prompts' in Path(value['path']).parts:raise ValueError('forbidden evidence path')
    verified_bytes(value)
    return value


def checked_require_clock(clock):
    from .s1_clock import ReservationClock
    if type(clock) is not ReservationClock:raise ValueError('trusted reservation clock required')
    clock_match(clock,clock.mapping())
    return clock


def clock_match(clock,value):
    from .s1_clock import typed_equal
    supplied=checked_clock_mapping(value)
    if not typed_equal(supplied.mapping(),clock.mapping()):raise ValueError('reservation clock differs from authoritative reservation')
    return True


def checked_mkdir(path,*,parents=False,exist_ok=False):
    path=Path(path)
    if parents and not operation(path.parent.exists):checked_mkdir(path.parent,parents=True,exist_ok=True)
    return operation(path.mkdir,exist_ok=exist_ok)


def checked_write_json(path,value):
    # Same JSON bytes and immutable link publication as files.write_json, with
    # an unbuffered sink and a gate between every fallible operation.
    import tempfile
    path=Path(path).absolute()
    if 'prompts' in path.parts:raise ValueError('forbidden evidence path')
    checked_mkdir(path.parent,parents=True,exist_ok=True)
    payload=operation(json.dumps,value,indent=2,allow_nan=False)+'\n'
    raw=operation(payload.encode)
    before();fd,temporary=tempfile.mkstemp(dir=path.parent,prefix='.'+path.name+'.',suffix='.tmp')
    stream=None
    try:
        before();stream=os.fdopen(fd,'wb',buffering=0,closefd=False)
        if operation(stream.write,raw)!=len(raw):raise OSError('short JSON write')
        operation(stream.flush);operation(os.fsync,fd);operation(stream.close)
        operation(os.link,temporary,path)
        operation(os.unlink,temporary)
    finally:
        # No deferred buffered write; leave partial bytes in place on failure.
        if stream is not None and not stream.closed:retire(stream.close)
        retire(os.close,fd)



def retire(function,*args):
    """Mandatory descriptor retirement cannot replace a pending primary."""
    import sys
    primary=sys.exception()
    try:return function(*args)
    except BaseException as error:
        if primary is None:raise
        primary.add_note('descriptor retirement: '+type(error).__name__+': '+str(error))



def acquire(function, release, *args, **kwargs):
    """Retain a returned resource before any fallible post-acquisition check."""
    before()
    trace_event(getattr(function,'__name__','acquire'),'start')
    before()
    value=function(*args,**kwargs)
    try:
        before()
        trace_event(getattr(function,'__name__','acquire'),'completed')
        before()
        return value
    except BaseException:
        retire(release,value)
        raise


def backend_operation(function, *args, cleanup_deadline=None, **kwargs):
    """Gate owned backend I/O internally; native calls remain indivisible.

    Asset snapshots may contain symlinks. Resolve and check the target before
    opening it, preserving the generic asset verifier's permitted membership.
    No cached bytes or verification result survives this invocation.
    """
    from . import files
    if function is files.safe_path:
        path=Path(args[0])
        if 'prompts' in path.parts:raise ValueError('prompts access is prohibited')
        resolved=operation(path.resolve)
        if 'prompts' in resolved.parts:raise ValueError('prompts access is prohibited')
        return path
    if function is files.verify_record:
        value=args[0]
        return backend_operation(files.file_record,value['path'],value['sha256'])
    if function is files.file_record:
        path=operation(backend_operation(files.safe_path,args[0]).resolve)
        expected=args[1] if len(args)>1 else kwargs.get('expected')
        checksum=operation(hashlib.sha256)
        stream=acquire(path.open,lambda stream:stream.close(),'rb',buffering=0)
        try:
            while True:
                block=operation(stream.read,2**20)
                if not block:break
                operation(checksum.update,block)
            operation(stream.close)
        finally:
            if not stream.closed:retire(stream.close)
        actual=operation(checksum.hexdigest)
        if expected is not None and actual!=expected:raise ValueError(f'changed file: {path}; expected {expected}, got {actual}')
        return dict(path=str(path),sha256=actual,bytes=operation(path.stat).st_size)
    if function is files.read_json:
        path=backend_operation(files.safe_path,args[0])
        stream=acquire(path.open,lambda stream:stream.close(),'r')
        try:
            raw=operation(stream.read)
            operation(stream.close)
        finally:
            if not stream.closed:retire(stream.close)
        return operation(json.loads,raw)
    if function is files.object_hash:
        raw=operation(json.dumps,args[0],sort_keys=True,separators=(',',':'),allow_nan=False)
        encoded=operation(raw.encode)
        checksum=operation(hashlib.sha256)
        operation(checksum.update,encoded)
        return operation(checksum.hexdigest)
    import tempfile
    if function is tempfile.TemporaryDirectory:
        return owned_temporary_directory(function,args,kwargs,cleanup_deadline)
    return operation(function,*args,**kwargs)


def loaded_runtime(output, *, modules=None, maps_path=Path('/proc/self/maps')):
    """S1 equivalent of runtime_capture, with every owned I/O return gated."""
    import sys
    from . import files
    modules=sys.modules if modules is None else modules
    names={}
    for name,module in list(modules.items()):
        filename=getattr(module,'__file__',None)
        if filename is None:continue
        path=operation(backend_operation(files.safe_path,filename).resolve)
        if not operation(path.is_file):continue
        names.setdefault(path,[]).append(name)
    path=backend_operation(files.safe_path,maps_path)
    stream=acquire(path.open,lambda stream:stream.close(),'r')
    try:
        raw=operation(stream.read)
        operation(stream.close)
    finally:
        if not stream.closed:retire(stream.close)
    libraries=set()
    for line in raw.splitlines():
        fields=line.split(maxsplit=5)
        if len(fields)!=6 or not fields[5].startswith('/'):continue
        filename=fields[5]
        if '.so' not in Path(filename).name:continue
        if filename.endswith(' (deleted)'):raise ValueError('loaded native library was deleted before provenance capture')
        libraries.add(operation(backend_operation(files.safe_path,filename).resolve))
    records=[]
    for path in sorted(set(names)|libraries):
        records.append(dict(backend_operation(files.file_record,path),modules=sorted(names.get(path,[])),mapped_native_library=path in libraries))
    checked_write_json(output,dict(schema='vipe-benchmark-loaded-runtime/v1',files=records,
        interpreter=dict(version=sys.version,executable=backend_operation(files.file_record,sys.executable),
            invoked_executable=sys.executable,prefix=sys.prefix,base_prefix=sys.base_prefix),
        moment='after the first allocated real result',new_imports=False,new_inference=False))
    return checked_file_record(output)


TEMPORARY_OWNERS=[]
PROCESS_STATE_OWNERS=[]
_temporary_scope=contextvars.ContextVar('s1_temporary_scope',default=None)


def mount_safe_opener():
    """Prepare the Linux no-mount-crossing syscall before entering native work.

    Linux openat2 RESOLVE_NO_XDEV also rejects same-device bind mounts. No
    weaker openat fallback is permitted. The closure does no procfs lookup.
    """
    import ctypes,sys
    if sys.platform!='linux' or os.uname().machine not in ('x86_64','aarch64'):
        raise OSError('S1 exact-root retirement requires supported Linux openat2 ABI')
    class OpenHow(ctypes.Structure):
        _fields_=[('flags',ctypes.c_uint64),('mode',ctypes.c_uint64),('resolve',ctypes.c_uint64)]
    library=ctypes.CDLL(None,use_errno=True);syscall=library.syscall;syscall.restype=ctypes.c_long
    def open_directory(parent_fd,name,mount_id):
        if type(mount_id) is not int or mount_id<=0:raise ValueError('retained mount identity unavailable')
        if type(name) is not str or not name or name in ('.','..') or '/' in name or '\0' in name:
            raise ValueError('exact owned directory basename required')
        how=OpenHow(os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW|os.O_CLOEXEC,0,0x01|0x04|0x08)
        result=syscall(ctypes.c_long(437),ctypes.c_int(parent_fd),ctypes.c_char_p(os.fsencode(name)),ctypes.byref(how),ctypes.c_size_t(ctypes.sizeof(how)))
        if result<0:
            code=ctypes.get_errno();raise OSError(code,os.strerror(code),name)
        # Successful resolution proves this FD belongs to the retained parent's
        # mount. Inherit that captured identity; never read /proc after C.
        return int(result)
    return open_directory


def captured_mount_identity(fd):
    """Fresh bounded fdinfo metadata, only under ordinary pre-constructor W."""
    import sys
    def release_stream(value):
        primary=sys.exception()
        try:value.close()
        except BaseException as error:
            (primary if primary is not None else error).s1_mount_readers=(value,)
            raise
    stream=acquire(Path('/proc/self/fdinfo',str(fd)).open,release_stream,'r')
    close_attempted=False
    def close_once():
        nonlocal close_attempted
        close_attempted=True
        return stream.close()
    try:
        raw=operation(stream.read,16385)
        operation(close_once)
    finally:
        pending=sys.exception()
        if not close_attempted:
            try:close_once()
            except BaseException as error:
                failure=pending if pending is not None else error
                failure.s1_mount_readers=(stream,)
                if pending is None:raise
                pending.add_note('mount metadata descriptor retirement: '+repr(error))
        elif not stream.closed and pending is not None:
            pending.s1_mount_readers=(stream,)
    if len(raw)>16384:raise ValueError('fdinfo metadata exceeded bound')
    fields=[line.split(':',1)[1].strip() for line in raw.splitlines() if line.startswith('mnt_id:')]
    if len(fields)!=1 or not fields[0].isascii() or not fields[0].isdigit() or int(fields[0])<=0:
        raise ValueError('retained mount identity unavailable')
    return int(fields[0])


class RetirementGate:
    """Transfer only already-owned retirement to safety at equality or later."""
    def __init__(self,deadline,event):
        self.deadline=deadline;self.event=event;self.safety=False;self.crossing=None
    def boundary(self,label,point):
        now=time.monotonic()
        if self.deadline is not None and now>=self.deadline and not self.safety:
            self.safety=True
            self.event.setdefault('transitions',[]).append(dict(operation=label,point=point,observed=now,deadline=self.deadline,state='safety_retirement'))
            self.crossing=TimeoutError('progress original work deadline')
        return now
    def call(self,label,function,*args,retain=None,**kwargs):
        entered=self.boundary(label,'before')
        item=dict(operation=label,start=entered,classification='safety_retirement' if self.safety else 'normal_cleanup',completed=False)
        if label in ('root_open','openat_directory_nofollow'):
            item.update(parent_fd=args[0],name=args[1],mount_id=args[2])
        elif label in ('root_fstat','fstat','scandir_owned_fd') or label.startswith('close_') or label=='fchdir_original':item['fd']=args[0]
        elif label in ('scandir_next','scandir_close'):
            item['iterator_id']=id(args[0]) if label=='scandir_next' else id(getattr(function,'__self__',None))
        self.event['operations'].append(item)
        try:
            result=function(*args,**kwargs)
            # Handle/effect ownership must be saved BEFORE the post-call clock.
            if retain is not None:retain(result)
            if label in ('root_open','openat_directory_nofollow'):item['acquired_fd']=result
            elif label=='scandir_owned_fd':item['iterator_id']=id(result)
            item['completed']=True
        except BaseException as error:
            item.update(error_class=type(error).__name__,message=str(error),effect='uncertain')
            raise
        item['end']=self.boundary(label,'after')
        return result


class OwnedTemporaryDirectory:
    """Exact generated root ownership; only mount-bound FD-relative retirement."""
    def __init__(self,directory,parent,name,parent_fd,root_fd,identity,cleanup_deadline):
        self.directory=directory;self.name=directory.name;self.parent=parent;self.basename=name
        self.parent_fd=parent_fd;self.root_fd=root_fd;self.identity=identity
        self.cleanup_deadline=cleanup_deadline;self.events=[];self.unresolved=True
        self.uncertain_descriptors=[];self.attempted=False;self.children=[];self.iterators=[]
        self.close_attempts=set();self.mount_id=None;self.open_directory=None;self.state='acquired'
    def close_fd(self,holder,key,gate,label):
        fd=holder[key] if isinstance(holder,dict) else getattr(holder,key)
        if fd is None:return
        token=(id(holder),key)
        if token in self.close_attempts:raise RuntimeError('uncertain descriptor close; blind retry prohibited')
        self.close_attempts.add(token)
        def closed(_):
            if isinstance(holder,dict):holder[key]=None;holder['closed']=True
            else:setattr(holder,key,None)
        try:gate.call(label,os.close,fd,retain=closed)
        except BaseException:
            self.uncertain_descriptors.append(fd);raise
    def cleanup(self):
        import sys
        primary=sys.exception()
        if not self.unresolved:return
        if self.attempted:
            error=RuntimeError('temporary retirement uncertainty; blind retry prohibited')
            if primary is not None:primary.add_note(str(error));return
            raise error
        self.attempted=True;self.state='retiring';started=time.monotonic()
        late=self.cleanup_deadline is not None and started>=self.cleanup_deadline
        event=dict(operation='temporary_safety_retirement' if late else 'temporary_cleanup',root=self.name,
            identity=None if self.identity is None else dict(self.identity),identity_available=self.identity is not None,
            cleanup_deadline=self.cleanup_deadline,start=started,operations=[],resolved=False,secondary=[])
        self.events.append(event);gate=RetirementGate(self.cleanup_deadline,event)
        if late:gate.safety=True  # Already late is an authorized retirement, not a new primary.
        failure=None
        def same(info,identity):return info.st_dev==identity['device'] and info.st_ino==identity['inode'] and stat.S_ISDIR(info.st_mode)
        def close_iterator(owned):
            if owned['closed'] or owned['close_attempted']:return
            owned['close_attempted']=True
            gate.call('scandir_close',owned['iterator'].close,retain=lambda _:owned.update(closed=True))
        def clear(fd,identity):
            if identity['mount_id']!=self.mount_id:raise ValueError('temporary mount identity changed')
            if not same(gate.call('fstat',os.fstat,fd),identity):raise ValueError('temporary directory identity changed')
            iterator=dict(iterator=None,closed=False,close_attempted=False)
            def retained(value):iterator['iterator']=value;self.iterators.append(iterator)
            gate.call('scandir_owned_fd',os.scandir,fd,retain=retained)
            sentinel=object();names=[]
            try:
                while True:
                    entry=gate.call('scandir_next',next,iterator['iterator'],sentinel)
                    if entry is sentinel:break
                    names.append(entry.name)
            except BaseException as pending:
                # Only a locally active traversal failure makes iterator
                # close secondary. sys.exception() may expose an outer
                # caller's primary, which must not mask this uncertainty.
                try:close_iterator(iterator)
                except BaseException as secondary:
                    event['secondary'].append(dict(operation='scandir_close',error_class=type(secondary).__name__,message=str(secondary)))
                    pending.add_note('temporary iterator close: '+repr(secondary))
                raise
            else:
                close_iterator(iterator)
            for name in names:
                if type(name) is not str or not name or name in ('.','..') or '/' in name:raise ValueError('temporary entry containment')
                item=gate.call('statat_nofollow',os.stat,name,dir_fd=fd,follow_symlinks=False)
                if item.st_dev!=self.identity['device']:raise ValueError('temporary mount/device escape')
                if stat.S_ISDIR(item.st_mode):
                    owned=dict(fd=None,device=item.st_dev,inode=item.st_ino,mount_id=self.mount_id,closed=False)
                    def retained_child(value):owned['fd']=value;self.children.append(owned)
                    gate.call('openat_directory_nofollow',self.open_directory,fd,name,self.mount_id,retain=retained_child)
                    traversal_error=None
                    try:
                        clear(owned['fd'],owned)
                        current=gate.call('statat_nofollow',os.stat,name,dir_fd=fd,follow_symlinks=False)
                        if not same(current,owned):raise ValueError('temporary child name reused')
                        gate.call('rmdirat',os.rmdir,name,dir_fd=fd)
                    except BaseException as error:
                        traversal_error=error
                        raise
                    finally:
                        # Ambient caller exceptions do not make a failed close
                        # secondary to this child traversal. Only a failure
                        # raised by this block may retain the child's primary.
                        pending=traversal_error
                        try:self.close_fd(owned,'fd',gate,'close_child_descriptor')
                        except BaseException as secondary:
                            if pending is None:raise
                            event['secondary'].append(dict(operation='close_child_descriptor',error_class=type(secondary).__name__,message=str(secondary)))
                            pending.add_note('temporary child close: '+repr(secondary))
                else:
                    current=gate.call('statat_nofollow',os.stat,name,dir_fd=fd,follow_symlinks=False)
                    if (current.st_dev,current.st_ino)!=(item.st_dev,item.st_ino):raise ValueError('temporary file name reused')
                    gate.call('unlinkat',os.unlink,name,dir_fd=fd)
        try:
            if self.root_fd is None or self.identity is None or self.mount_id is None or self.open_directory is None:
                raise RuntimeError('temporary root identity unavailable; no traversal')
            clear(self.root_fd,self.identity)
            current=gate.call('statat_root_nofollow',os.stat,self.basename,dir_fd=self.parent_fd,follow_symlinks=False)
            if not same(current,self.identity):raise ValueError('temporary root name reused')
            gate.call('rmdirat_root',os.rmdir,self.basename,dir_fd=self.parent_fd)
            event['root_removed']=True
        except BaseException as error:failure=error
        finally:
            # Close each acquired handle at most once even if traversal failed.
            for iterator in self.iterators:
                try:close_iterator(iterator)
                except BaseException as error:
                    event['secondary'].append(dict(operation='scandir_close',error_class=type(error).__name__,message=str(error)))
                    if failure is None:failure=error
            for holder,key,label in [(child,'fd','close_child_descriptor') for child in self.children]+[(self,'root_fd','close_root_descriptor'),(self,'parent_fd','close_parent_descriptor')]:
                fd=holder[key] if isinstance(holder,dict) else getattr(holder,key)
                if fd is None or (id(holder),key) in self.close_attempts:continue
                try:self.close_fd(holder,key,gate,label)
                except BaseException as error:
                    event['secondary'].append(dict(operation=label,error_class=type(error).__name__,message=str(error)))
                    if failure is None:failure=error
            if failure is None:
                self.unresolved=False;self.state='retired';event['resolved']=True;TEMPORARY_OWNERS.remove(self)
            else:
                self.state='uncertain';event.update(error_class=type(failure).__name__,message=str(failure))
            event['end']=time.monotonic()
        error=primary if primary is not None else gate.crossing or failure
        if error is not None:
            error.s1_temporary_retirement=tuple(self.events)
            if self.unresolved:error.s1_temporary_owners=tuple(value for value in TEMPORARY_OWNERS if value.unresolved)
            if failure is not None and error is not failure:error.add_note('temporary safety retirement: '+repr(failure))
            if primary is None:raise error


def owned_temporary_directory(constructor,args,kwargs,cleanup_deadline):
    inherited=_deadline.get()
    effective=cleanup_deadline if inherited is None else inherited if cleanup_deadline is None else min(inherited,cleanup_deadline)
    token=_deadline.set(effective)
    try:return _owned_temporary_directory(constructor,args,kwargs,cleanup_deadline)
    finally:_deadline.reset(token)


def _owned_temporary_directory(constructor,args,kwargs,cleanup_deadline):
    before()
    parent=operation(Path(kwargs['dir']).resolve)
    opener=operation(mount_safe_opener)
    def release_parent(fd):
        import sys
        primary=sys.exception()
        try:os.close(fd)
        except BaseException as error:
            pending=primary if primary is not None else error
            pending.s1_uncertain_descriptors=tuple(getattr(pending,'s1_uncertain_descriptors',()))+(fd,)
            raise
    parent_fd=acquire(os.open,release_parent,parent,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
    directory=None;owned=None;gate=None
    try:
        mount_id=operation(captured_mount_identity,parent_fd)
        if type(mount_id) is not int or mount_id<=0:raise ValueError('retained mount identity unavailable')
        before();directory=constructor(*args,**kwargs)
        name=Path(directory.name).name
        owned=OwnedTemporaryDirectory(directory,parent,name,parent_fd,None,None,cleanup_deadline)
        TEMPORARY_OWNERS.append(owned)
        if _temporary_scope.get() is not None:_temporary_scope.get().append(owned)
        owned.mount_id=mount_id;owned.open_directory=opener
        directory._finalizer.detach()
        if Path(directory.name).parent!=parent or name in ('.','..'):raise ValueError('temporary constructor root containment')
        event=dict(operation='temporary_root_acquisition',root=owned.name,parent_fd=parent_fd,operations=[],mount_id=mount_id,identity=None,work_deadline=_deadline.get(),cleanup_deadline=cleanup_deadline)
        owned.events.append(event);gate=RetirementGate(_deadline.get(),event)
        gate.call('root_open',opener,parent_fd,name,mount_id,retain=lambda fd:setattr(owned,'root_fd',fd))
        info=gate.call('root_fstat',os.fstat,owned.root_fd)
        named=gate.call('root_named_stat',os.stat,name,dir_fd=parent_fd,follow_symlinks=False)
        if not stat.S_ISDIR(info.st_mode) or (info.st_dev,info.st_ino)!=(named.st_dev,named.st_ino):raise ValueError('temporary acquisition identity changed')
        owned.identity=dict(device=info.st_dev,inode=info.st_ino,mount_id=mount_id)
        event['identity']=dict(owned.identity)
        if gate.crossing is not None:raise gate.crossing
        before()
        return owned
    except BaseException as primary:
        # A deadline observed earlier in the owned acquisition remains the
        # primary if a later safety-metadata operation also fails.
        first=gate.crossing if gate is not None and gate.crossing is not None else primary
        if first is not primary:first.add_note('temporary acquisition secondary: '+repr(primary))
        try:raise first
        except BaseException:
            if owned is not None:owned.cleanup()
            else:retire(release_parent,parent_fd)
            raise


class OwnedWorkingDirectory:
    def __init__(self):
        self.fd=None;self.identity=None;self.events=[];self.unresolved=True;self.attempted=False
        before();trace_event('cwd_open','start');before()
        self.fd=os.open('.',os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
        PROCESS_STATE_OWNERS.append(self)
        try:
            before();trace_event('cwd_open','completed');before()
            info=operation(os.fstat,self.fd)
            self.identity=dict(device=info.st_dev,inode=info.st_ino)
        except BaseException as primary:
            try:os.close(self.fd);self.unresolved=False;PROCESS_STATE_OWNERS.remove(self)
            except BaseException as cleanup:
                primary.s1_cwd_owners=(self,);primary.add_note('cwd acquisition retirement: '+repr(cleanup))
            raise
    def restore(self,cleanup_deadline):
        import sys
        primary=sys.exception()
        if self.attempted:raise RuntimeError('working directory restoration cannot retry')
        self.attempted=True;started=time.monotonic()
        late=cleanup_deadline is not None and started>=cleanup_deadline
        event=dict(operation='cwd_safety_restoration' if late else 'cwd_restoration',fd=self.fd,identity=self.identity,
            cleanup_deadline=cleanup_deadline,start=started,restored=False,closed=False,operations=[])
        self.events.append(event);gate=RetirementGate(cleanup_deadline,event)
        if late:gate.safety=True
        failure=None
        try:
            gate.call('fchdir_original',os.fchdir,self.fd,retain=lambda _:event.update(restored=True))
        except BaseException as error:failure=error;event.update(error_class=type(error).__name__,message=str(error))
        # A failed fchdir retains the only restoration handle. Never close it.
        if event['restored']:
            try:gate.call('close_original_cwd',os.close,self.fd,retain=lambda _:event.update(closed=True))
            except BaseException as error:
                event['close_error']=dict(error_class=type(error).__name__,message=str(error));failure=error
        event['end']=time.monotonic()
        if failure is None:
            self.unresolved=False;PROCESS_STATE_OWNERS.remove(self)
        error=primary if primary is not None else gate.crossing or failure
        if error is not None:
            error.s1_cwd_restoration=tuple(self.events)
            if self.unresolved:error.s1_cwd_owners=tuple(PROCESS_STATE_OWNERS)
            if failure is not None and error is not failure:error.add_note('cwd safety restoration: '+repr(failure))
            if primary is None:raise error

def backend_resource_scope():
    import contextlib,sys
    @contextlib.contextmanager
    def scope():
        resources=[];token=_temporary_scope.set(resources)
        try:yield resources
        finally:
            primary=sys.exception();first=None
            for resource in resources:
                if not resource.unresolved or resource.attempted:continue
                try:resource.cleanup()
                except BaseException as error:
                    if primary is not None:primary.add_note('backend resource cleanup: '+repr(error))
                    elif first is None:first=error
                    else:first.add_note('backend resource cleanup: '+repr(error))
            _temporary_scope.reset(token)
            if primary is None and first is not None:raise first
    return scope()


def numeric_archive(stream,arrays):
    """Same NumPy NPZ representation, with separate member/finalization gates."""
    import numpy as np
    import zipfile
    archive=operation(zipfile.ZipFile,stream,mode='w',compression=zipfile.ZIP_DEFLATED)
    try:
        for name,value in arrays.items():
            before()
            array=operation(np.asanyarray,value)
            member=acquire(archive.open,lambda value:value.close(),name+'.npy',mode='w',force_zip64=True)
            try:operation(np.lib.format.write_array,DeadlineSink(member),array,allow_pickle=False)
            finally:
                if __import__('sys').exception() is None:operation(member.close)
                else:retire(member.close)
        operation(archive.close)
    finally:
        if archive.fp is not None:
            # The externally owned sink is retired by numeric_file. An aborted
            # archive has no right to emit a central directory during cleanup.
            archive.fp=None

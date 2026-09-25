"""Fixed S1 CPU roles: bounded control transport and retained launch ownership.

The OS/native-thread boundary is measured, not asserted to be hard real time.
An unresolved launcher remains in OWNERS even after a timed-out caller returns.
"""
import _thread
from collections import deque
from dataclasses import dataclass
import datetime
import fcntl
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

JOB_LEDGER_SCHEMA = 'registered-process-tree-job/v1'
JOB_LEDGER_LIMIT = 8 * 1024 * 1024
JOB_LEDGER_POISONED = False

_JOB_EVENT_FIELDS = {
    'attempt-open': ({'kind','index','h','driver_pid'}, set()),
    'main-handle': ({'session_id','start_event_sha256'}, set()),
    'session-terminal': ({'session_id','terminal'}, set()),
    'root-reserved': ({'token','role','label','creator'}, {'candidate'}),
    'descendant-reserved': ({'token','root','role','label','creator'}, {'candidate'}),
    'root-bound': ({'token','identity','handle','owner'}, set()),
    'descendant-bound': ({'token','identity','handle','owner'}, set()),
    'root-wait': ({'token','terminal','handle_object_id','owner','operation_key'}, set()),
    'root-wait-claim': ({'token','owner','operation_key'}, set()),
    'wait-poll-intent': ({'token','owner','operation_key','sequence'}, set()),
    'wait-poll-result': ({'token','owner','operation_key','sequence','result'}, set()),
    'descendant-wait-result': ({'token','terminal','handle_object_id','owner','operation_key'}, set()),
    'root-retired': ({'token','terminal'}, {'method'}),
    'signal-intent': ({'token','owner','operation_key','target','signal'}, set()),
    'signal-result': ({'token','owner','operation_key','result'}, set()),
    'pidfd-pin': ({'token','owner','operation_key','target','descriptor'}, set()),
    'pidfd-close-claim': ({'token','owner','operation_key','descriptor'}, set()),
    'pidfd-closed': ({'token','owner','operation_key','descriptor','result'}, set()),
    'operation-uncertain': ({'token','owner','operation_key','phase','reason'}, set()),
    'descendant-creator-ack': ({'token','root','creator','identity','census'}, set()),
    'descendant-ack': ({'worker_pid','child_pid','census'}, set()),
    'descendant-retired': ({'token'}, {'method','identity','handle_object_id','terminal','owner','operation_key'}),
}


def _job_value(value, depth=0):
    """Reject non-JSON, non-finite, duplicate-shaped or unbounded event values."""
    if depth > 16: raise ValueError('job ledger nesting limit')
    if value is None or type(value) in (bool, int): return
    if type(value) is float:
        if not math.isfinite(value): raise ValueError('nonfinite job ledger number')
        return
    if type(value) is str:
        if '\x00' in value or len(value.encode('utf-8')) > 16384: raise ValueError('job ledger string limit')
        return
    if type(value) is list or type(value) is tuple:
        if len(value) > 4096: raise ValueError('job ledger array limit')
        for item in value: _job_value(item, depth+1)
        return
    if type(value) is dict:
        if len(value) > 128 or any(type(key) is not str or not key or '\x00' in key for key in value):
            raise ValueError('job ledger object limit')
        for key, item in value.items():
            _job_value(key, depth+1); _job_value(item, depth+1)
        return
    raise ValueError('job ledger value type')


def _job_proc_identity(value):
    fields={'boot_id','pid','ppid','pgid','start_ticks','threads','threads_before','threads_after','process_before','process_after'}
    if type(value) is not dict or set(value)!=fields:raise ValueError('job process identity schema')
    if type(value['boot_id']) is not str or not value['boot_id']:raise ValueError('job process boot identity')
    if any(type(value[key]) is not int or value[key]<=0 for key in ('pid','pgid','start_ticks')) or type(value['ppid']) is not int or value['ppid']<0:raise ValueError('job process identity numbers')
    process_fields={'boot_id','pid','ppid','pgid','start_ticks'}
    for key in ('process_before','process_after'):
        item=value[key]
        if type(item) is not dict or set(item)!=process_fields or any(item.get(field)!=value.get(field) for field in process_fields):raise ValueError('job process identity bracket')
    tasks=value['threads']
    if type(tasks) is not list or not tasks or len(tasks)>4096:raise ValueError('job process thread identity list')
    for task in tasks:
        required={'boot_id','pid','process_start_ticks','tid','start_ticks'}
        if type(task) is not dict or set(task)!=required or task['boot_id']!=value['boot_id'] or task['pid']!=value['pid'] or task['process_start_ticks']!=value['start_ticks'] or any(type(task[k]) is not int or task[k]<=0 for k in ('tid','start_ticks')):raise ValueError('job native task identity')
    if value['threads_before']!=tasks or value['threads_after']!=tasks:raise ValueError('job process task bracket')


def _job_creator_identity(value):
    fields={'boot_id','pid','start_ticks','pgid','tid','thread_start_ticks'}
    if type(value) is not dict or set(value)!=fields or type(value['boot_id']) is not str or not value['boot_id'] or any(type(value[key]) is not int or value[key]<=0 for key in fields-{'boot_id'}):
        raise ValueError('job creator incarnation schema')


def _job_terminal(value):
    if type(value) is not dict:raise ValueError('job terminal schema')
    if value.get('method')=='matching child wait':
        if set(value)=={'method','pid','returncode'} and type(value['pid']) is int and value['pid']>0 and type(value['returncode']) is int:return
        if set(value)=={'method','pid','wait_status'} and type(value['pid']) is int and value['pid']>0 and type(value['wait_status']) is int:return
    if value.get('method')=='same Thread.join' and set(value)=={'method','stopped'} and value['stopped'] is True:return
    raise ValueError('job terminal fields')


def _job_process_descriptor(value):
    fields={'schema','api','executable','argv','cwd','options','environment','host'}
    if type(value) is not dict or set(value)!=fields or value['schema']!='plan049-process-candidate/v1' or value['api'] not in ('subprocess.Popen','os.posix_spawn','os.execve'):
        raise ValueError('job process candidate descriptor schema')
    try:
        executable=bytes.fromhex(value['executable']);cwd=bytes.fromhex(value['cwd'])
        argv=[bytes.fromhex(item) for item in value['argv']]
    except (TypeError,ValueError):raise ValueError('job process candidate byte encoding') from None
    if (not executable or not cwd or not argv or len(argv)>4096
            or any(b'\0' in item for item in (executable,cwd,*argv))
            or type(value['options']) is not dict):
        raise ValueError('job process candidate command fields')
    env=value['environment'];host=value['host']
    if (type(env) is not dict or set(env)!={'sha256','entries','bytes'} or type(env['sha256']) is not str
            or len(env['sha256'])!=64 or any(c not in '0123456789abcdef' for c in env['sha256'])
            or type(env['entries']) is not int or not 0<=env['entries']<=4096 or type(env['bytes']) is not int or not 0<=env['bytes']<=1024*1024):
        raise ValueError('job process candidate environment summary')
    if (type(host) is not dict or set(host)!={'per_string','arg_max','pointer_bytes','platform_overhead','vector_bytes'}
            or any(type(host[key]) is not int or host[key]<0 for key in host)
            or host['per_string']<=0 or host['arg_max']<=0
            or host['pointer_bytes']+host['platform_overhead']+host['vector_bytes']>host['arg_max']
            or host['vector_bytes']!=sum(len(item)+1 for item in argv)+env['bytes']
            or any(len(item)+1>host['per_string'] for item in argv)):
        raise ValueError('job process candidate host limits')


def _job_event_data(event, data):
    if type(event) is not str or event not in _JOB_EVENT_FIELDS or type(data) is not dict:
        raise ValueError('unknown job ledger event/data')
    required, optional = _JOB_EVENT_FIELDS[event]
    if not required <= set(data) or set(data)-required-optional:
        raise ValueError('job ledger event fields')
    _job_value(data)
    if event == 'attempt-open' and (data['kind'] not in ('diagnostic','aggregate') or type(data['index']) is not int or data['index'] < 1 or type(data['h']) is not int or data['h'] != 1 or type(data['driver_pid']) is not int or data['driver_pid'] <= 0):
        raise ValueError('job ledger attempt-open fields')
    if event == 'main-handle' and (type(data['session_id']) is not int or data['session_id'] <= 0 or type(data['start_event_sha256']) is not str or len(data['start_event_sha256']) != 64 or any(c not in '0123456789abcdef' for c in data['start_event_sha256'])):
        raise ValueError('job ledger main-handle fields')
    if event == 'session-terminal':
        receipt=data['terminal']
        if (type(data['session_id']) is not int or data['session_id']<=0 or type(receipt) is not dict
                or set(receipt)!={'schema','session_id','returned_utc','exit_code','output_sha256'}
                or receipt.get('schema')!='plan049-main-session-terminal/v1' or receipt.get('session_id')!=data['session_id']
                or type(receipt.get('returned_utc')) is not str or type(receipt.get('exit_code')) is not int
                or type(receipt.get('output_sha256')) is not str or len(receipt['output_sha256'])!=64
                or any(char not in '0123456789abcdef' for char in receipt['output_sha256'])):
            raise ValueError('job ledger session terminal receipt')
        try:returned=datetime.datetime.fromisoformat(receipt['returned_utc'])
        except ValueError:raise ValueError('job ledger Main terminal UTC') from None
        if returned.tzinfo is None or returned.utcoffset()!=datetime.timedelta(0):raise ValueError('job ledger Main terminal UTC timezone')
    if event in ('root-reserved','descendant-reserved'):
        candidate=data.get('candidate')
        candidate_valid=False
        if type(candidate) is dict and set(candidate)=={'descriptor','sha256','environment'} and type(candidate.get('descriptor')) is str and type(candidate.get('sha256')) is str and type(candidate.get('environment')) is dict:
            try:
                descriptor_bytes=candidate['descriptor'].encode('ascii');descriptor=json.loads(descriptor_bytes)
                canonical=(json.dumps(descriptor,sort_keys=True,separators=(',',':'),allow_nan=False)+'\n').encode('ascii')
                environment=descriptor.get('environment') if type(descriptor) is dict else None
                _job_process_descriptor(descriptor)
                candidate_valid=(len(descriptor_bytes)<=16384 and descriptor_bytes==canonical
                    and hashlib.sha256(descriptor_bytes).hexdigest()==candidate['sha256']
                    and type(environment) is dict and set(environment)=={'sha256','entries','bytes'}
                    and environment==candidate['environment'] and type(environment.get('sha256')) is str
                    and len(environment['sha256'])==64 and all(char in '0123456789abcdef' for char in environment['sha256'])
                    and type(environment.get('entries')) is int and 0<=environment['entries']<=4096
                    and type(environment.get('bytes')) is int and 0<=environment['bytes']<=1024*1024)
            except (UnicodeEncodeError,ValueError,TypeError):candidate_valid=False
        if (type(data['token']) is not str or len(data['token']) != 32 or data['role'] not in ('B','H')
                or type(data['label']) is not str or not data['label'] or type(data['creator']) is not dict
                or ((data['role']=='B') != ('candidate' in data)) or ('candidate' in data and not candidate_valid)):
            raise ValueError('job ledger reservation fields')
        _job_creator_identity(data['creator'])
    if event in ('root-bound','descendant-bound') and (type(data['token']) is not str or type(data['identity']) is not dict or type(data['handle']) is not dict or set(data['handle']) != {'kind','object_id'} or data['handle']['kind'] not in ('process','Thread') or type(data['handle']['object_id']) is not int):
        raise ValueError('job ledger binding fields')
    if event in ('root-bound','descendant-bound'):
        if data['handle']['kind']=='process':_job_proc_identity(data['identity'])
        else:
            thread_fields={'boot_id','pid','pgid','start_ticks','tid','thread_start_ticks','ident'}
            if type(data['identity']) is not dict or set(data['identity'])!=thread_fields or type(data['identity']['boot_id']) is not str or not data['identity']['boot_id'] or any(type(data['identity'][key]) is not int or data['identity'][key]<=0 for key in ('pid','pgid','tid','ident','start_ticks','thread_start_ticks')):
                raise ValueError('job thread handle identity')
        owner=data['owner']
        if (type(owner) is not dict or set(owner)!={'boot_id','owner_pid','owner_start_ticks','main_session_id','root_token','nonce','handle_object_id'}
                or type(owner['boot_id']) is not str or type(owner['owner_pid']) is not int or owner['owner_pid']<=0
                or type(owner['owner_start_ticks']) is not int or owner['owner_start_ticks']<=0
                or type(owner['main_session_id']) is not int or owner['main_session_id']<=0 or owner['root_token']!=data['token']
                or type(owner['nonce']) is not str or len(owner['nonce'])!=32 or any(c not in '0123456789abcdef' for c in owner['nonce'])
                or owner['handle_object_id']!=data['handle']['object_id']):raise ValueError('job ledger owner incarnation')
    if event == 'root-wait' and (type(data['terminal']) is not dict or type(data['handle_object_id']) is not int):
        raise ValueError('job ledger root wait fields')
    if event in ('root-wait','descendant-wait-result'):_job_terminal(data['terminal'])
    if event == 'root-retired' and (type(data['terminal']) is not dict or ('method' in data and data['method'] != 'matching wait and pidfd terminal')):
        raise ValueError('job ledger root retirement fields')
    if event=='root-retired':_job_terminal(data['terminal'])
    if event in ('descendant-creator-ack','descendant-ack') and any(type(data[key]) is not dict for key in (('creator','identity','census') if event == 'descendant-creator-ack' else ('census',))):
        raise ValueError('job ledger descendant acknowledgement fields')
    if event in ('descendant-creator-ack','descendant-ack'):
        _job_proc_identity(data['identity'] if event=='descendant-creator-ack' else data['census'])
        if event=='descendant-creator-ack':_job_creator_identity(data['creator']);_job_proc_identity(data['census'])
    if event == 'descendant-retired':
        pidfd=data.get('method')=='identity-bound pidfd terminal' and set(data)=={'token','method','identity','owner','operation_key'} and type(data['identity']) is dict
        waited=data.get('method')=='matching child wait' and set(data)=={'token','method','terminal','handle_object_id','owner','operation_key'} and type(data['terminal']) is dict and type(data['handle_object_id']) is int
        legacy_wait='method' not in data and set(data)=={'token','terminal','handle_object_id','owner','operation_key'} and type(data['terminal']) is dict and type(data['handle_object_id']) is int
        if not (pidfd or waited or legacy_wait):raise ValueError('job ledger descendant retirement fields')
        if 'terminal' in data:_job_terminal(data['terminal'])
        if 'identity' in data:_job_proc_identity(data['identity'])
    if event in ('root-wait-claim','signal-intent','signal-result','pidfd-pin','pidfd-close-claim','pidfd-closed','operation-uncertain'):
        owner=data['owner']
        if (type(owner) is not dict or set(owner)!={'boot_id','owner_pid','owner_start_ticks','main_session_id','root_token','nonce','handle_object_id'}
                or type(data['operation_key']) is not str or len(data['operation_key'])!=64
                or any(char not in '0123456789abcdef' for char in data['operation_key'])):
            raise ValueError('job ledger operation owner/key')
    if event in ('wait-poll-intent','wait-poll-result'):
        owner=data['owner']
        if (type(owner) is not dict or set(owner)!={'boot_id','owner_pid','owner_start_ticks','main_session_id','root_token','nonce','handle_object_id'}
                or type(data['operation_key']) is not str or len(data['operation_key'])!=64
                or any(char not in '0123456789abcdef' for char in data['operation_key'])
                or type(data['sequence']) is not int or data['sequence']<1):raise ValueError('job ledger wait poll key/sequence')
        if event=='wait-poll-result':
            result=data['result']
            if (type(result) is not dict or set(result)!={'pid','wait_status','terminal'}
                    or type(result['pid']) is not int or result['pid']<0
                    or type(result['wait_status']) is not int or result['wait_status']<0
                    or type(result['terminal']) is not bool or result['terminal']!=(result['pid']>0)
                    or (result['pid']==0 and result['wait_status']!=0)):
                raise ValueError('job ledger wait poll result')
    if event in ('signal-intent','pidfd-pin'):_job_proc_identity(data['target'])
    if event=='signal-intent' and type(data['signal']) is not int:raise ValueError('job ledger signal intent')
    if event=='signal-result' and (type(data['result']) is not dict or set(data['result'])!={'sent','error'} or type(data['result']['sent']) is not bool or data['result']['error'] not in (None,'ProcessLookupError') or data['result']['sent']!=(data['result']['error'] is None)):raise ValueError('job ledger signal result')
    if event=='pidfd-closed' and (type(data['result']) is not dict or set(data['result'])!={'closed','error'} or data['result']!={'closed':True,'error':None}):raise ValueError('job ledger pidfd close result schema')
    if event=='pidfd-pin' and (type(data['target']) is not dict or type(data['descriptor']) is not int or data['descriptor']<0):raise ValueError('job ledger pidfd pin')
    if event=='pidfd-close-claim' and (type(data['descriptor']) is not int or data['descriptor']<0):raise ValueError('job ledger pidfd close claim')
    if event=='pidfd-closed' and (type(data['descriptor']) is not int or data['descriptor']<0):raise ValueError('job ledger pidfd close result')
    if event=='operation-uncertain' and (type(data['phase']) is not str or type(data['reason']) is not str):raise ValueError('job ledger uncertain operation')


def _candidate_bytes(create, args, kwargs):
    """Materialize one selected POSIX process candidate without losing env bytes."""
    import subprocess
    api_name=getattr(create,'_mock_name',None)
    if create is subprocess.Popen or api_name=='Popen':
        if not args:raise ValueError('process candidate argv missing')
        raw_argv=args[0]
        if type(raw_argv) not in (list,tuple) or not raw_argv:raise ValueError('process candidate requires an argv sequence')
        argv=tuple(os.fsencode(item) for item in raw_argv)
        executable=os.fsencode(kwargs.get('executable') or raw_argv[0])
        env_value=kwargs.get('env')
        env=dict(os.environ if env_value is None else env_value)
        cwd=kwargs.get('cwd')
        resolved_cwd=os.fsencode(os.path.abspath(os.fsdecode(cwd) if cwd is not None else os.getcwd()))
        allowed={'executable','stdin','stdout','stderr','preexec_fn','close_fds','shell','cwd','env','universal_newlines','startupinfo','creationflags','restore_signals','start_new_session','pass_fds','encoding','errors','text','user','group','extra_groups','umask','pipesize','process_group','bufsize'}
        if set(kwargs)-allowed:raise ValueError('unsupported Popen descriptor option')
        if kwargs.get('shell',False) is not False or kwargs.get('preexec_fn') is not None or kwargs.get('startupinfo') is not None:
            raise ValueError('unsupported process creation option')
        options={key:kwargs.get(key,default) for key,default in (
            ('shell',False),('close_fds',True),('restore_signals',True),('start_new_session',False),
            ('creationflags',0),('pass_fds',()),('stdin',None),('stdout',None),('stderr',None),
            ('bufsize',-1),('text',kwargs.get('text',kwargs.get('universal_newlines',False))),
            ('universal_newlines',kwargs.get('text',kwargs.get('universal_newlines',False))),('encoding',None),('errors',None),
            ('user',None),('group',None),('extra_groups',None),('umask',-1),('pipesize',-1),('process_group',None))}
        for key in ('stdin','stdout','stderr'):
            value=options[key]
            if value is None:
                options[key]=None
            elif type(value) is int:
                if value<0:raise ValueError('negative process stdio descriptor')
                st=os.fstat(value);options[key]=dict(fd=value,device=st.st_dev,inode=st.st_ino,mode=st.st_mode)
            elif hasattr(value,'fileno'):
                fd=value.fileno();st=os.fstat(fd);options[key]=dict(fd=fd,device=st.st_dev,inode=st.st_ino,mode=st.st_mode)
            else:raise ValueError('unsupported process stdio object')
        api='subprocess.Popen'
    elif create is os.posix_spawn or api_name=='posix_spawn' or create is os.execve or api_name=='execve':
        if len(args)<3:raise ValueError('posix_spawn candidate arguments')
        executable=os.fsencode(args[0]);argv=tuple(os.fsencode(item) for item in args[1]);env=dict(args[2])
        resolved_cwd=os.fsencode(os.path.abspath(os.getcwd()))
        if create is os.execve or api_name=='execve':
            if kwargs:raise ValueError('execve options unsupported')
            options={};api='os.execve'
        else:
            actions=kwargs.get('file_actions',())
            try:actions=tuple(tuple(item) for item in actions)
            except (TypeError,ValueError):raise ValueError('posix_spawn file actions') from None
            options={key:kwargs[key] for key in ('setsigdef','setsigmask','setpgroup','setsid','resetids') if key in kwargs}
            options['file_actions']=actions
            api='os.posix_spawn'
    else:
        raise ValueError('unreviewed selected process creation API')
    if any(b'\0' in item for item in (executable,*argv)):raise ValueError('NUL in process argument')
    encoded_env=[]
    for key,value in env.items():
        if type(key) is not str or type(value) is not str or not key or '=' in key:
            raise ValueError('invalid POSIX environment entry')
        kb=os.fsencode(key);vb=os.fsencode(value)
        if b'\0' in kb or b'\0' in vb:raise ValueError('NUL in POSIX environment')
        encoded_env.append((kb,vb))
    encoded_env.sort()
    env_vector=tuple(key+b'='+value+b'\0' for key,value in encoded_env)
    arg_vector=tuple(value+b'\0' for value in argv)
    env_size=sum(map(len,env_vector));arg_size=sum(map(len,arg_vector))
    if len(env_vector)>4096 or env_size>1024*1024:raise ValueError('process environment cap')
    try:
        page=os.sysconf('SC_PAGE_SIZE');arg_max=os.sysconf('SC_ARG_MAX')
    except (OSError,ValueError):raise ValueError('unsupported host process-vector limits') from None
    if type(page) is not int or type(arg_max) is not int or page<=0 or arg_max<=0:raise ValueError('unsupported host process-vector limits')
    per_string=page*32
    if any(len(value)>per_string for value in (*arg_vector,*env_vector)):
        raise ValueError('host per-string process limit')
    pointers=(len(arg_vector)+len(env_vector)+2)*struct.calcsize('P')
    platform_overhead=2*page  # Reserve stack alignment, auxv and exec metadata headroom.
    if arg_size+env_size+pointers+platform_overhead>arg_max:raise ValueError('host full process-vector limit')
    descriptor=dict(schema='plan049-process-candidate/v1',api=api,executable=executable.hex(),
        argv=[value.hex() for value in argv],cwd=resolved_cwd.hex(),options=options,
        environment=dict(sha256=hashlib.sha256(b''.join(env_vector)).hexdigest(),entries=len(env_vector),bytes=env_size),
        host=dict(per_string=per_string,arg_max=arg_max,pointer_bytes=pointers,platform_overhead=platform_overhead,vector_bytes=arg_size+env_size))
    descriptor_bytes=(json.dumps(descriptor,sort_keys=True,separators=(',',':'),allow_nan=False)+'\n').encode('ascii')
    if len(descriptor_bytes)>16384:raise ValueError('process command descriptor cap')
    final_env={os.fsdecode(key):os.fsdecode(value) for key,value in encoded_env}
    return descriptor_bytes,final_env


def _prepare_owned_candidate(create,args,kwargs):
    """Freeze argv/env then verify the exact reusable candidate against fresh host limits."""
    import subprocess
    api_name=getattr(create,'_mock_name',None)
    if create is subprocess.Popen or api_name=='Popen':
        if len(args)!=1:raise ValueError('Popen positional tail unsupported')
        descriptor,environment=_candidate_bytes(create,args,kwargs)
        frozen_args=(tuple(os.fsencode(item) for item in args[0]),)
        frozen_kwargs=dict(kwargs,env=environment,executable=os.fsencode(kwargs.get('executable') or args[0][0]),
            cwd=os.fsdecode(os.path.abspath(os.fsdecode(kwargs.get('cwd')) if kwargs.get('cwd') is not None else os.getcwd())))
        for key in ('stdin','stdout','stderr'):
            value=kwargs.get(key)
            if value is not None and type(value) is not int and hasattr(value,'fileno'):
                frozen_kwargs[key]=value.fileno()
        frozen_kwargs['pass_fds']=tuple(kwargs.get('pass_fds',()))
        for key in ('extra_groups',):
            if frozen_kwargs.get(key) is not None:frozen_kwargs[key]=tuple(frozen_kwargs[key])
    elif create is os.posix_spawn or api_name=='posix_spawn' or create is os.execve or api_name=='execve':
        if len(args)!=3:raise ValueError('spawn/exec positional tail unsupported')
        descriptor,environment=_candidate_bytes(create,args,kwargs)
        frozen_args=(os.fsencode(args[0]),tuple(os.fsencode(item) for item in args[1]),environment)
        if create is os.posix_spawn or api_name=='posix_spawn':
            allowed={'file_actions','setsigdef','setsigmask','setpgroup','setsid','resetids'}
            if set(kwargs)-allowed:raise ValueError('unsupported posix_spawn option')
            frozen_kwargs=dict(kwargs)
            if 'file_actions' in frozen_kwargs:frozen_kwargs['file_actions']=tuple(tuple(item) for item in frozen_kwargs['file_actions'])
            for key in ('setsigdef','setsigmask'):
                if key in frozen_kwargs:frozen_kwargs[key]=tuple(frozen_kwargs[key])
        else:frozen_kwargs=dict(kwargs)
    else:raise ValueError('unreviewed selected process creation API')
    return descriptor,environment,frozen_args,frozen_kwargs


def _candidate_receipt(candidate):
    descriptor,environment,_,_=candidate
    value=json.loads(descriptor)
    return dict(descriptor=descriptor.decode('ascii'),sha256=hashlib.sha256(descriptor).hexdigest(),environment=value['environment'])


def _job_bytes(value):
    digit_limit=sys.get_int_max_str_digits()
    try:
        if digit_limit and digit_limit<20000:sys.set_int_max_str_digits(20000)
        return (json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False)+'\n').encode()
    finally:
        if digit_limit and digit_limit<20000:sys.set_int_max_str_digits(digit_limit)


def _job_line(sequence,previous,event,data):
    row=dict(schema=JOB_LEDGER_SCHEMA,sequence=sequence,previous_sha256=previous,
        utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),event=event,data=data)
    row['sha256']=hashlib.sha256(_job_bytes(row)).hexdigest()
    return _job_bytes(row)


def job_ledger_paths(kind,index,repository=None):
    repository=Path(__file__).resolve().parents[2] if repository is None else Path(repository)
    if kind not in ('diagnostic','aggregate') or type(index) is not int or index<1:
        raise ValueError('job ledger kind/index')
    base=repository/'docs/resolve-blocker/plan031-progress-20260922'/('.job-ledger-'+kind+'-049-'+str(index).zfill(3))
    return Path(str(base)+'.jsonl'),Path(str(base)+'.lock')


def _job_read(raw):
    if not 0<len(raw)<=JOB_LEDGER_LIMIT or not raw.endswith(b'\n'):
        raise ValueError('job ledger length/incomplete line')
    previous='0'*64;rows=[]
    for sequence,line in enumerate(raw.splitlines()):
        def pairs(items):
            value={}
            for key,item in items:
                if key in value:raise ValueError('duplicate job ledger key')
                value[key]=item
            return value
        digit_limit=sys.get_int_max_str_digits()
        try:
            if digit_limit and digit_limit<20000:sys.set_int_max_str_digits(20000)
            row=json.loads(line,object_pairs_hook=pairs,parse_constant=lambda value:(_ for _ in ()).throw(ValueError('nonfinite job ledger number')))
        finally:
            if digit_limit and digit_limit<20000:sys.set_int_max_str_digits(digit_limit)
        def finite(value):
            if type(value) is float and not math.isfinite(value):raise ValueError('nonfinite job ledger number')
            if type(value) is dict:
                for item in value.values():finite(item)
            if type(value) is list:
                for item in value:finite(item)
        finite(row)
        if type(row) is not dict or set(row)!={'schema','sequence','previous_sha256','utc','event','data','sha256'} or row['schema']!=JOB_LEDGER_SCHEMA or type(row['sequence']) is not int or row['sequence']!=sequence or row['previous_sha256']!=previous or type(row['event']) is not str or type(row['data']) is not dict:
            raise ValueError('job ledger schema/chain')
        _job_event_data(row['event'],row['data'])
        try:observed=datetime.datetime.fromisoformat(row['utc'])
        except (TypeError,ValueError):raise ValueError('job ledger UTC') from None
        if observed.tzinfo is None or observed.utcoffset()!=datetime.timedelta(0):raise ValueError('job ledger UTC timezone')
        digest=row.pop('sha256')
        if type(digest) is not str or hashlib.sha256(_job_bytes(row)).hexdigest()!=digest:
            raise ValueError('job ledger checksum')
        row['sha256']=digest
        if _job_bytes(row)!=line+b'\n':raise ValueError('job ledger noncanonical line')
        previous=digest;rows.append(row)
    return rows


def _job_operation_key(owner,phase,target):
    payload=dict(root_token=owner['root_token'],nonce=owner['nonce'],handle_object_id=owner['handle_object_id'],phase=phase,target=target)
    return hashlib.sha256(_job_bytes(payload)).hexdigest()


def prepare_job_ledger(kind,index):
    """Derive the exact bootstrap bytes without mutating the filesystem."""
    path,lock=job_ledger_paths(kind,index)
    line=_job_line(0,'0'*64,'attempt-open',dict(kind=kind,index=index,h=1,driver_pid=os.getpid()))
    if len(line)>JOB_LEDGER_LIMIT:raise ValueError('job ledger bootstrap size cap')
    return dict(path=str(path),lock=str(lock),line=line,initial_sha256=hashlib.sha256(line).hexdigest(),schema=JOB_LEDGER_SCHEMA)


def initialize_job_ledger(kind,index,prepared=None):
    """First filesystem mutation; exclusively create and verify planned bytes."""
    value=prepare_job_ledger(kind,index) if prepared is None else prepared
    path=Path(value['path']);lock=Path(value['lock']);line=value['line']
    if value['schema']!=JOB_LEDGER_SCHEMA or path!=job_ledger_paths(kind,index)[0] or lock!=job_ledger_paths(kind,index)[1] or hashlib.sha256(line).hexdigest()!=value['initial_sha256']:
        raise ValueError('job ledger prepared bootstrap binding')
    flags=os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW
    descriptor=os.open(path,flags,0o600)
    try:
        with os.fdopen(descriptor,'wb',buffering=0) as stream:
            if stream.write(line)!=len(line):raise OSError('short job ledger bootstrap write')
            os.fsync(stream.fileno())
        lock_fd=os.open(lock,flags,0o600)
        try:
            fcntl.flock(lock_fd,fcntl.LOCK_EX)
            os.fsync(lock_fd)
            directory_fd=os.open(path.parent,os.O_RDONLY|os.O_DIRECTORY)
            try:os.fsync(directory_fd)
            finally:os.close(directory_fd)
            if path.read_bytes()!=line or len(_job_read(line))!=1:
                raise ValueError('job ledger bootstrap readback')
        finally:
            fcntl.flock(lock_fd,fcntl.LOCK_UN);os.close(lock_fd)
    except BaseException:
        # Occupied partial paths are preserved for Main's uncertainty audit.
        raise
    return {key:value[key] for key in ('path','lock','initial_sha256','schema')}


def job_ledger_events(path=None):
    global JOB_LEDGER_POISONED
    if JOB_LEDGER_POISONED:raise ValueError('job ledger process state poisoned; stop required')
    path=Path(path or os.environ['S1_JOB_LEDGER'])
    lock=Path(str(path)[:-6]+'.lock') if str(path).endswith('.jsonl') else None
    if lock is None:raise ValueError('job ledger suffix')
    descriptor=os.open(lock,os.O_RDONLY|os.O_NOFOLLOW)
    try:
        fcntl.flock(descriptor,fcntl.LOCK_SH)
        if os.fstat(descriptor).st_size:raise ValueError('job ledger append lock is poisoned; stop required')
        return _job_read(path.read_bytes())
    finally:
        active=sys.exc_info()[1];retirement_error=None
        try:fcntl.flock(descriptor,fcntl.LOCK_UN)
        except BaseException as exc:retirement_error=exc
        try:os.close(descriptor)
        except BaseException as exc:
            if retirement_error is None:retirement_error=exc
            else:
                try:retirement_error.add_note('job ledger read-lock close also failed: %r'%exc)
                except BaseException:pass
        if retirement_error is not None:
            JOB_LEDGER_POISONED=True
            if active is not None:
                try:active.add_note('job ledger read-lock retirement failed: %r'%retirement_error)
                except BaseException:pass
            else:raise retirement_error


def _job_state(rows):
    roots={};descendants={};operations={};handle=None;terminal=False
    for ordinal,row in enumerate(rows):
        event=row['event'];data=row['data'];token=data.get('token')
        if event=='attempt-open':
            if ordinal!=0 or data.get('h')!=1:raise ValueError('duplicate/invalid attempt open')
        elif event=='main-handle':
            if handle is not None or type(data.get('session_id')) is not int or data['session_id']<=0:
                raise ValueError('duplicate/invalid Main session handle')
            handle=data['session_id']
        elif event=='session-terminal':
            if terminal or handle is None or data.get('session_id')!=handle:raise ValueError('Main terminal handle mismatch')
            if any(row['state']!='retired' for row in roots.values()) or any(row['state']!='retired' for row in descendants.values()):
                raise ValueError('Main terminal before owned job retirement')
            terminal=True
        elif event=='root-reserved':
            if handle is None or token in roots or data.get('role') not in ('B','H'):raise ValueError('duplicate/invalid root reservation')
            roots[token]=dict(data,state='reserved')
        elif event=='root-bound':
            if token not in roots or roots[token]['state']!='reserved':raise ValueError('root binding order')
            owner=data.get('owner');creator=roots[token]['creator']
            if (owner is None or owner['main_session_id']!=handle or owner['root_token']!=token
                    or owner['boot_id']!=creator['boot_id'] or owner['owner_pid']!=creator['pid']
                    or owner['owner_start_ticks']!=creator['start_ticks']):raise ValueError('root bound owner differs from creator incarnation')
            roots[token].update(data,state='live')
        elif event=='root-wait-claim':
            target=roots.get(token) or descendants.get(token)
            if target is None or target['state']!='live' or data.get('owner')!=target.get('owner'):
                raise ValueError('root wait claim owner/state')
            operation_key=_job_operation_key(data['owner'],'wait',target['identity'])
            if data['operation_key']!=operation_key or operation_key in operations:raise ValueError('duplicate/conflicting root wait claim')
            operations[operation_key]=dict(kind='wait',token=token,owner=data['owner'],target=target['identity'],state='claimed')
        elif event=='wait-poll-intent':
            target=roots.get(token) or descendants.get(token)
            if target is None or target['state']!='live' or target.get('owner')!=data['owner']:raise ValueError('wait poll owner/state')
            key=_job_operation_key(data['owner'],'wait',target['identity'])
            if data['operation_key']!=key:raise ValueError('wait poll operation key')
            operation=operations.get(key)
            if operation is None:
                operation=dict(kind='wait',token=token,owner=data['owner'],target=target['identity'],state='polling',poll_sequence=0)
                operations[key]=operation
            if operation['kind']!='wait' or operation['token']!=token or operation['state']!='polling' or data['sequence']!=operation.get('poll_sequence',0)+1:
                raise ValueError('wait poll sequence/order')
            operation['state']='poll-intent';operation['poll_sequence']=data['sequence']
        elif event=='wait-poll-result':
            operation=operations.get(data['operation_key'])
            if operation is None or operation['kind']!='wait' or operation['token']!=token or operation['owner']!=data['owner'] or operation['state']!='poll-intent' or data['sequence']!=operation['poll_sequence']:
                raise ValueError('wait poll result without intent')
            result=data['result']
            if result['terminal'] and result['pid']!=operation['target']['pid']:
                raise ValueError('wait poll terminal differs from owned child')
            if result['terminal']:
                operation['state']='claimed';operation['terminal_poll']=dict(pid=result['pid'],wait_status=result['wait_status'],sequence=data['sequence'])
            else:operation['state']='polling'
        elif event=='root-wait':
            if token not in roots or roots[token]['state']!='live' or data.get('owner')!=roots[token].get('owner'):
                raise ValueError('root wait order')
            if data.get('handle_object_id')!=roots[token].get('handle',{}).get('object_id') or type(data.get('terminal')) is not dict:
                raise ValueError('root matching handle terminal')
            operation=operations.get(data.get('operation_key'))
            if operation is None or operation['kind']!='wait' or operation['token']!=token or operation['owner']!=data['owner'] or operation['state']!='claimed':
                raise ValueError('root wait result lacks unique claim')
            if operation.get('terminal_poll') is not None and (data['terminal'].get('pid')!=operation['terminal_poll']['pid'] or data['terminal'].get('wait_status')!=operation['terminal_poll']['wait_status']):raise ValueError('root wait differs from terminal poll')
            operations[data['operation_key']]['state']='complete'
            roots[token]['state']='waited';roots[token]['terminal']=data['terminal']
        elif event=='root-retired':
            if token not in roots or roots[token]['state']!='waited' or any(child['root']==token and child['state']!='retired' for child in descendants.values()):
                raise ValueError('root tree retirement order')
            if data.get('terminal')!=roots[token].get('terminal'):
                raise ValueError('root terminal reference')
            if any((value.get('token')==token or (value.get('kind')=='pin' and value.get('owner',{}).get('root_token')==token)) and value['state'] in ('claimed','intent','open','uncertain','poll-intent','polling') for value in operations.values()):
                raise ValueError('root retirement with unresolved operation')
            roots[token]['state']='retired'
        elif event=='descendant-reserved':
            parent=roots.get(data.get('root'))
            creator=data.get('creator')
            if token in descendants or parent is None or parent['state']!='live' or parent['role']!='B' or type(creator) is not dict or any(creator.get(key)!=parent.get('identity',{}).get(key) for key in ('boot_id','pid','start_ticks','pgid')):
                raise ValueError('descendant reservation/creator identity')
            descendants[token]=dict(data,state='reserved')
        elif event=='descendant-bound':
            if token not in descendants or descendants[token]['state']!='reserved':raise ValueError('descendant binding order')
            owner=data.get('owner');creator=descendants[token]['creator']
            if (owner is None or owner['main_session_id']!=handle or owner['root_token']!=token
                    or owner['boot_id']!=creator['boot_id'] or owner['owner_pid']!=creator['pid']
                    or owner['owner_start_ticks']!=creator['start_ticks']):raise ValueError('descendant bound owner differs from creator incarnation')
            descendants[token].update(data,state='live')
        elif event=='descendant-wait-result':
            child=descendants.get(token);operation=operations.get(data.get('operation_key'))
            if (child is None or child['state']!='live' or child.get('owner')!=data.get('owner')
                    or data.get('handle_object_id')!=child.get('handle',{}).get('object_id')
                    or operation is None or operation['kind']!='wait' or operation['token']!=token or operation['state']!='claimed'):
                raise ValueError('descendant wait receipt ownership/order')
            if operation.get('terminal_poll') is not None and (data['terminal'].get('pid')!=operation['terminal_poll']['pid'] or data['terminal'].get('wait_status')!=operation['terminal_poll']['wait_status']):raise ValueError('descendant wait differs from terminal poll')
            operations[data['operation_key']]['state']='complete';child.update(state='waited',terminal=data['terminal'])
        elif event=='signal-intent':
            root=roots.get(token) or descendants.get(token)
            if root is None or root['state']!='live' or data.get('owner')!=root.get('owner'):
                raise ValueError('signal intent root owner/state')
            key=_job_operation_key(data['owner'],'signal:'+str(data['signal']),data['target'])
            if data['operation_key']!=key or key in operations:raise ValueError('duplicate/conflicting signal intent')
            if not any(value['kind']=='pin' and value['owner']==data['owner'] and value['target']==data['target'] and value['state']=='open' for value in operations.values()):
                raise ValueError('signal target lacks open identity-bound pidfd')
            operations[key]=dict(kind='signal',token=token,owner=data['owner'],target=data['target'],signal=data['signal'],state='intent')
        elif event=='signal-result':
            operation=operations.get(data['operation_key'])
            if operation is None or operation['kind']!='signal' or operation['token']!=token or operation['owner']!=data['owner'] or operation['state']!='intent':
                raise ValueError('signal result without unique intent')
            operations[data['operation_key']]['state']='complete'
            operations[data['operation_key']]['result']=data['result']
        elif event=='pidfd-pin':
            root=roots.get(data['owner'].get('root_token')) or descendants.get(data['owner'].get('root_token'));target=roots.get(token) or descendants.get(token)
            if root is None or target is None or root['state']!='live' or data.get('owner')!=root.get('owner') or target.get('identity')!=data['target']:
                raise ValueError('pidfd pin owner/target')
            key=_job_operation_key(data['owner'],'pin',dict(identity=data['target'],descriptor=data['descriptor']))
            if key!=data['operation_key'] or key in operations:raise ValueError('duplicate pidfd pin')
            operations[key]=dict(kind='pin',token=token,owner=data['owner'],target=data['target'],descriptor=data['descriptor'],state='open')
        elif event=='pidfd-close-claim':
            pin=next((value for value in operations.values() if value['kind']=='pin' and value['token']==token and value['descriptor']==data['descriptor']),None)
            if pin is None or pin['owner']!=data['owner'] or pin['state']!='open':raise ValueError('pidfd close claim target/state')
            key=_job_operation_key(data['owner'],'close',dict(token=token,target=pin['target'],descriptor=data['descriptor']))
            if key!=data['operation_key'] or key in operations:raise ValueError('duplicate pidfd close claim')
            operations[key]=dict(kind='close',token=token,owner=data['owner'],target=pin['target'],descriptor=data['descriptor'],state='claimed')
        elif event=='pidfd-closed':
            operation=operations.get(data['operation_key'])
            if operation is None or operation['kind']!='close' or operation['token']!=token or operation['owner']!=data['owner'] or operation['descriptor']!=data['descriptor'] or operation['state']!='claimed':
                raise ValueError('pidfd close result without unique claim')
            operations[data['operation_key']]['state']='complete';operations[data['operation_key']]['result']=data['result']
            for pin in operations.values():
                if pin['kind']=='pin' and pin['token']==token and pin['descriptor']==data['descriptor']:pin['state']='closed'
        elif event=='operation-uncertain':
            operation=operations.get(data['operation_key'])
            if operation is None or operation['token']!=token or operation['owner']!=data['owner'] or operation['state'] not in ('claimed','intent','poll-intent'):
                raise ValueError('uncertain operation owner/key/state conflict')
            if data['phase']!=operation['kind']:raise ValueError('uncertain operation phase conflict')
            operation['state']='uncertain';operation['reason']=data['reason']
        elif event=='descendant-creator-ack':
            child=descendants.get(token)
            if child is None or child['state']!='live' or child.get('creator_acknowledged'):
                raise ValueError('descendant creator acknowledgement order')
            if data.get('root')!=child['root'] or data.get('creator')!=child['creator'] or data.get('identity')!=child['identity'] or type(data.get('census')) is not dict or any(data['census'].get(key)!=child['identity'].get(key) for key in ('boot_id','pid','ppid','pgid','start_ticks')):
                raise ValueError('descendant creator acknowledgement identity')
            child['creator_acknowledged']=True
        elif event=='descendant-ack':
            selected=[child for child in descendants.values() if child['state']=='live' and child.get('identity',{}).get('pid')==data.get('child_pid')]
            if len(selected)!=1 or not selected[0].get('creator_acknowledged') or selected[0].get('l35_acknowledged') or roots[selected[0]['root']].get('identity',{}).get('pid')!=data.get('worker_pid'):
                raise ValueError('descendant acknowledgement order')
            census=data.get('census')
            if type(census) is not dict or any(census.get(key)!=selected[0]['identity'].get(key) for key in ('boot_id','pid','ppid','pgid','start_ticks')):
                raise ValueError('descendant acknowledgement identity')
            selected[0]['l35_acknowledged']=True
        elif event=='descendant-retired':
            if token not in descendants or descendants[token]['state'] not in ('live','waited'):raise ValueError('descendant retirement order')
            if data.get('method')=='identity-bound pidfd terminal' and (not descendants[token].get('creator_acknowledged') or data.get('identity')!=descendants[token].get('identity')):
                raise ValueError('unacknowledged pidfd terminal')
            if data.get('method')!='identity-bound pidfd terminal' and data.get('handle_object_id')!=descendants[token].get('handle',{}).get('object_id'):
                raise ValueError('descendant matching handle terminal')
            if any(value.get('token')==token and value['state'] in ('claimed','intent','open','uncertain','poll-intent') and key!=data.get('operation_key') for key,value in operations.items()):
                raise ValueError('descendant retirement with unresolved operation')
            if data.get('method')!='identity-bound pidfd terminal':
                operation=operations.get(data.get('operation_key'))
                fresh_wait=operation is not None and operation['state']=='claimed' and descendants[token]['state']=='live'
                close_wait=operation is not None and operation['state']=='complete' and descendants[token]['state']=='waited' and data.get('terminal')==descendants[token].get('terminal')
                pins=[value for value in operations.values() if value['kind']=='pin' and value['token']==token]
                if (data.get('owner')!=descendants[token].get('owner') or operation is None or operation['kind']!='wait'
                        or operation['token']!=token or not (fresh_wait or close_wait) or any(pin['state']!='closed' for pin in pins)):
                    raise ValueError('descendant wait terminal lacks unique claim')
                terminal_poll=operation.get('terminal_poll')
                if terminal_poll is not None and (data['terminal'].get('pid')!=terminal_poll['pid']
                        or data['terminal'].get('wait_status')!=terminal_poll['wait_status']):
                    raise ValueError('descendant retirement differs from terminal poll')
                operations[data['operation_key']]['state']='complete'
            else:
                root=roots.get(data['owner'].get('root_token')) or descendants.get(data['owner'].get('root_token'))
                terminal_key=data.get('operation_key')
                pins=[value for value in operations.values() if value['kind']=='pin' and value['token']==token and value['target']==descendants[token]['identity']]
                expected_key=_job_operation_key(data['owner'],'pidfd-terminal',descendants[token]['identity']) if root is not None else None
                if (data.get('owner')!=root.get('owner') or terminal_key!=expected_key or terminal_key in operations
                        or not pins or any(pin['state']!='closed' for pin in pins)):
                    raise ValueError('pidfd descendant retirement owner/pin terminal')
                operations[terminal_key]=dict(kind='pidfd-terminal',token=token,owner=data['owner'],target=descendants[token]['identity'],state='complete')
            descendants[token]['state']='retired'
        else:raise ValueError('unknown job ledger transition')
    B=sum(row['role']=='B' and row['state']!='retired' for row in roots.values())
    H=(not terminal)+sum(row['role']=='H' and row['state']!='retired' for row in roots.values())
    if B+max(1,H)>8:raise ValueError('logical job capacity exceeded')
    return dict(roots=roots,descendants=descendants,operations=operations,B=B,H=H,session_id=handle,terminal=terminal)


def append_job_event(event,data,path=None,*,guard=None):
    global JOB_LEDGER_POISONED
    if JOB_LEDGER_POISONED:raise ValueError('job ledger poisoned after ambiguous append; stop required')
    path=Path(path or os.environ['S1_JOB_LEDGER'])
    lock=Path(str(path)[:-6]+'.lock') if str(path).endswith('.jsonl') else None
    if lock is None:raise ValueError('job ledger suffix')
    descriptor=os.open(lock,os.O_RDWR|os.O_NOFOLLOW)
    try:
        fcntl.flock(descriptor,fcntl.LOCK_EX)
        marker=os.pread(descriptor,64,0)
        if marker:raise ValueError('job ledger append lock is poisoned; stop required')
        def poison(reason):
            global JOB_LEDGER_POISONED
            JOB_LEDGER_POISONED=True
            expected=('POISON:'+reason[:48]).encode('ascii','replace')
            try:
                os.ftruncate(descriptor,0)
                if os.pwrite(descriptor,expected,0)!=len(expected):
                    raise OSError('short poison marker write')
                os.fsync(descriptor)
                if os.pread(descriptor,len(expected)+1,0)!=expected or os.fstat(descriptor).st_size!=len(expected):
                    raise OSError('poison marker readback mismatch')
            except BaseException as marker_error:
                return OSError('job ledger %s stop: poison marker persistence failed; durable stop unverified: %r'%(reason,marker_error))
            return None
        raw=path.read_bytes();rows=_job_read(raw)
        state=_job_state(rows)
        if guard is not None:
            replacement=guard(state)
            if replacement is not None:event,data=replacement
        _job_event_data(event,data)
        line=_job_line(len(rows),rows[-1]['sha256'],event,data)
        digit_limit=sys.get_int_max_str_digits()
        try:
            if digit_limit and digit_limit<20000:sys.set_int_max_str_digits(20000)
            proposed=json.loads(line)
        finally:
            if digit_limit and digit_limit<20000:sys.set_int_max_str_digits(digit_limit)
        _job_state(rows+[proposed])
        if len(raw)+len(line)>JOB_LEDGER_LIMIT:
            marker_error=poison('cap')
            if marker_error is not None:raise marker_error
            raise ValueError('job ledger size cap')
        file_fd=os.open(path,os.O_RDWR|os.O_APPEND|os.O_NOFOLLOW)
        try:
            os.lseek(file_fd,0,os.SEEK_END)
            try:
                written=os.write(file_fd,line)
                if written!=len(line):raise OSError('short job ledger append: %d of %d bytes'%(written,len(line)))
                os.fsync(file_fd)
                observed=path.read_bytes()
                if observed!=raw+line:raise OSError('job ledger append readback mismatch')
                return _job_read(observed)[-1]
            except BaseException as primary:
                # A failed write/fsync/readback never becomes committed evidence.
                # Restore only the previously verified prefix while holding the lock.
                try:
                    os.ftruncate(file_fd,len(raw));os.fsync(file_fd)
                    rollback=path.read_bytes()
                    if rollback!=raw or _job_read(rollback)!=rows:
                        raise OSError('job ledger rollback prefix mismatch')
                except BaseException as rollback_error:
                    marker_error=poison('uncertain')
                    try:primary.add_note('job ledger rollback failed; verified_prefix_bytes=%d attempted_line_bytes=%d observed_file_bytes=%s rollback_error=%r'%(len(raw),len(line),path.stat().st_size,rollback_error))
                    except BaseException:pass
                    if marker_error is not None:primary.add_note(str(marker_error))
                    raise primary
                marker_error=poison('rolled-back')
                try:primary.add_note('job ledger append rolled back and verified; verified_prefix_bytes=%d attempted_line_bytes=%d; attempt stopped'%(len(raw),len(line)))
                except BaseException:pass
                if marker_error is not None:primary.add_note(str(marker_error))
                raise primary
        finally:
            active=sys.exc_info()[1]
            try:os.close(file_fd)
            except BaseException as close_error:
                marker_error=poison('file-close')
                if active is not None:
                    try:active.add_note('job ledger file close failed after verified-prefix handling: %r'%close_error)
                    except BaseException:pass
                    if marker_error is not None:active.add_note(str(marker_error))
                else:
                    if marker_error is not None:close_error.add_note(str(marker_error))
                    raise
    finally:
        active=sys.exc_info()[1];retirement_error=None
        try:fcntl.flock(descriptor,fcntl.LOCK_UN)
        except BaseException as exc:retirement_error=exc
        try:os.close(descriptor)
        except BaseException as exc:
            if retirement_error is None:retirement_error=exc
            else:
                try:retirement_error.add_note('job ledger lock descriptor close also failed: %r'%exc)
                except BaseException:pass
        if retirement_error is not None:
            if 'poison' in locals():marker_error=poison('lock-retirement')
            else:
                JOB_LEDGER_POISONED=True;marker_error=None
            if marker_error is not None:retirement_error.add_note(str(marker_error))
            if active is not None:
                try:active.add_note('job ledger lock retirement failed: %r'%retirement_error)
                except BaseException:pass
                if marker_error is not None:active.add_note(str(marker_error))
            else:raise retirement_error


JOB_HANDLES={}
JOB_PROCESSES={}
JOB_OWNERS={}
JOB_MUTEXES={}
_JOB_REGISTRY_LOCK=_thread.allocate_lock()


def _job_owner(token,handle):
    with _JOB_REGISTRY_LOCK:
        registration=JOB_OWNERS.get(token);owner=None if registration is None else registration.get('owner')
        if JOB_HANDLES.get(token) is not handle or owner is None or owner['handle_object_id']!=id(handle):
            raise ValueError('exact retained owner handle unavailable')
        current=identity(os.getpid());boot=Path('/proc/sys/kernel/random/boot_id').read_text().strip()
        if owner['owner_pid']!=os.getpid() or owner['owner_start_ticks']!=current['start_ticks'] or owner['boot_id']!=boot:
            raise ValueError('owner incarnation changed or forked registry inherited')
        return dict(owner)


def _job_mutex(token):
    with _JOB_REGISTRY_LOCK:
        if token not in JOB_MUTEXES:JOB_MUTEXES[token]=_thread.allocate_lock()
        return JOB_MUTEXES[token]


def _wait_job_handle(token,handle,method,args,kwargs,*,thread=False):
    mutex=_job_mutex(token)
    with mutex:
        owner=_job_owner(token,handle)
        state=_job_state(job_ledger_events())
        row=state['roots'].get(token) or state['descendants'].get(token)
        if row is None or row.get('owner')!=owner:raise ValueError('wait owner differs from durable registration')
        cached=JOB_OWNERS[token].get('wait_receipt')
        if row['state'] in ('waited','retired'):
            if cached is None:raise ValueError('durable wait receipt unavailable; charged')
            if token in state['roots']:
                result=method(*args,**kwargs)  # Correction015 requires the same-handle repeat Popen.wait call.
                if not thread and result!=cached['returncode']:raise ValueError('same-handle repeated wait terminal changed')
                return result
            return cached['returncode']
        if row['state']!='live':raise ValueError('wait target not live')
        if cached is None:
            operation_key=_job_operation_key(owner,'wait',row['identity'])
            claims=[event for event in state['operations'].values() if event.get('kind')=='wait' and event.get('token')==token]
            if claims:raise ValueError('wait claim unresolved; second OS wait forbidden')
            append_job_event('root-wait-claim',dict(token=token,owner=owner,operation_key=operation_key))
            JOB_OWNERS[token]['wait_claim']=operation_key
            try:result=method(*args,**kwargs)
            except BaseException as exc:
                append_job_event('operation-uncertain',dict(token=token,owner=owner,operation_key=operation_key,phase='wait',reason=type(exc).__name__))
                raise
            if thread:
                alive=handle.is_alive() if hasattr(handle,'is_alive') else not handle.is_done()
                terminal=dict(method='same Thread.join',stopped=not alive)
                if not terminal['stopped']:raise ValueError('thread join returned while live')
                receipt=dict(operation_key=operation_key,terminal=terminal,returncode=None)
            else:
                receipt=dict(operation_key=operation_key,terminal=dict(method='matching child wait',pid=handle.pid,returncode=result),returncode=result)
            JOB_OWNERS[token]['wait_receipt']=receipt  # Cache before the durable result write.
            cached=receipt
        operation_key=cached['operation_key'];terminal=cached['terminal']
        if token in state['roots']:
            append_job_event('root-wait',dict(token=token,terminal=terminal,handle_object_id=id(handle),owner=owner,operation_key=operation_key))
        else:
            fresh=_job_state(job_ledger_events())
            open_pins=[value for value in fresh['operations'].values() if value['kind']=='pin' and value['token']==token and value['state']=='open']
            if open_pins:
                append_job_event('descendant-wait-result',dict(token=token,terminal=terminal,handle_object_id=id(handle),owner=owner,operation_key=operation_key))
            else:
                append_job_event('descendant-retired',dict(token=token,method='matching child wait',terminal=terminal,
                    handle_object_id=id(handle),owner=owner,operation_key=operation_key))
        return cached['returncode']


def wait_owned_pid(pid,flags=0):
    """Perform the single registered waitpid only after its durable claim."""
    owned=JOB_PROCESSES.get(pid)
    if owned is None:return os.waitpid(pid,flags)
    token,handle=owned
    if type(handle) is not int or handle!=pid:raise ValueError('waitpid does not match the retained exact spawn result')
    with _job_mutex(token):
        owner=_job_owner(token,handle);state=_job_state(job_ledger_events())
        row=state['roots'].get(token) or state['descendants'].get(token)
        if row is None or row.get('owner')!=owner or row['state']!='live':raise ValueError('waitpid target not live')
        operation_key=_job_operation_key(owner,'wait',row['identity'])
        if flags==os.WNOHANG:
            prior=state['operations'].get(operation_key)
            sequence=0 if prior is None else prior.get('poll_sequence',0)
            append_job_event('wait-poll-intent',dict(token=token,owner=owner,operation_key=operation_key,sequence=sequence+1))
            try:result=os.waitpid(pid,flags)
            except BaseException as exc:
                append_job_event('operation-uncertain',dict(token=token,owner=owner,operation_key=operation_key,phase='wait',reason=type(exc).__name__))
                raise
            if result[0] not in (0,pid) or (result[0]==0 and result[1]!=0):
                append_job_event('operation-uncertain',dict(token=token,owner=owner,operation_key=operation_key,phase='wait',reason='unexpected waitpid result'))
                raise ValueError('waitpid returned an unexpected child')
            append_job_event('wait-poll-result',dict(token=token,owner=owner,operation_key=operation_key,sequence=sequence+1,
                result=dict(pid=result[0],wait_status=result[1],terminal=result[0]==pid)))
            if result[0]==0:return result
            terminal=dict(method='matching child wait',pid=pid,wait_status=result[1])
            JOB_OWNERS[token]['wait_receipt']=dict(operation_key=operation_key,terminal=terminal,returncode=result[1],waitpid=True)
            fresh=_job_state(job_ledger_events())
            if token in fresh['roots']:
                append_job_event('root-wait',dict(token=token,terminal=terminal,handle_object_id=id(handle),owner=owner,operation_key=operation_key))
            else:
                open_pins=[value for value in fresh['operations'].values() if value['kind']=='pin' and value['token']==token and value['state']=='open']
                if open_pins:append_job_event('descendant-wait-result',dict(token=token,terminal=terminal,handle_object_id=id(handle),owner=owner,operation_key=operation_key))
                else:append_job_event('descendant-retired',dict(token=token,method='matching child wait',terminal=terminal,handle_object_id=id(handle),owner=owner,operation_key=operation_key))
            return result
        if any(value.get('kind')=='wait' and value.get('token')==token for value in state['operations'].values()):
            raise ValueError('waitpid claim unresolved; second OS wait forbidden')
        append_job_event('root-wait-claim',dict(token=token,owner=owner,operation_key=operation_key))
        try:result=os.waitpid(pid,flags)
        except BaseException as exc:
            append_job_event('operation-uncertain',dict(token=token,owner=owner,operation_key=operation_key,phase='wait',reason=type(exc).__name__))
            raise
        if result[0]!=pid:
            append_job_event('operation-uncertain',dict(token=token,owner=owner,operation_key=operation_key,phase='wait',reason='nonterminal waitpid result'))
            raise ValueError('waitpid did not return the exact claimed child')
        terminal=dict(method='matching child wait',pid=pid,wait_status=result[1])
        JOB_OWNERS[token]['wait_receipt']=dict(operation_key=operation_key,terminal=terminal,returncode=result[1],waitpid=True)
        if token in state['roots']:
            append_job_event('root-wait',dict(token=token,terminal=terminal,handle_object_id=id(handle),owner=owner,operation_key=operation_key))
        else:
            fresh=_job_state(job_ledger_events())
            open_pins=[value for value in fresh['operations'].values() if value['kind']=='pin' and value['token']==token and value['state']=='open']
            if open_pins:
                append_job_event('descendant-wait-result',dict(token=token,terminal=terminal,handle_object_id=id(handle),owner=owner,operation_key=operation_key))
            else:
                append_job_event('descendant-retired',dict(token=token,method='matching child wait',terminal=terminal,
                    handle_object_id=id(handle),owner=owner,operation_key=operation_key))
        return result


def register_job_pidfd_pin(root_token,target_token,target_identity,descriptor):
    if os.environ.get('S1_JOB_LEDGER'):
        root_handle=JOB_HANDLES.get(root_token);owner=_job_owner(root_token,root_handle)
        key=_job_operation_key(owner,'pin',dict(identity=target_identity,descriptor=descriptor))
        append_job_event('pidfd-pin',dict(token=target_token,owner=owner,operation_key=key,target=target_identity,descriptor=descriptor))
        JOB_OWNERS[root_token].setdefault('pidfds',{})[(target_token,descriptor)]=dict(identity=target_identity)
        return key
    return None


def signal_job_pidfd(root_token,target_token,target_identity,descriptor,sig,deadline):
    if not os.environ.get('S1_JOB_LEDGER'):
        return os.pidfd_send_signal(descriptor,sig,None,0)
    with _job_mutex(root_token):
        owner=_job_owner(root_token,JOB_HANDLES.get(root_token));state=_job_state(job_ledger_events())
        root=state['roots'].get(root_token) or state['descendants'].get(root_token)
        if root is None or root['state']!='live' or root.get('owner')!=owner:raise ValueError('pidfd signal root owner/state')
        key=_job_operation_key(owner,'signal:'+str(int(sig)),target_identity)
        old=state['operations'].get(key)
        if old is not None:
            if old.get('kind')!='signal' or old.get('token')!=root_token or old.get('target')!=target_identity:raise ValueError('pidfd signal operation conflict')
            if old['state']=='complete':return dict(old['result'])
            raise ValueError('pidfd signal intent unresolved; no resend')
        append_job_event('signal-intent',dict(token=root_token,owner=owner,operation_key=key,target=target_identity,signal=int(sig)))
        from .s1_progress import before
        try:
            before(deadline)
            os.pidfd_send_signal(descriptor,sig,None,0)
            result=dict(sent=True,error=None)
        except ProcessLookupError:
            result=dict(sent=False,error='ProcessLookupError')
        except BaseException as exc:
            append_job_event('operation-uncertain',dict(token=root_token,owner=owner,operation_key=key,phase='signal',reason=type(exc).__name__))
            raise
        receipts=JOB_OWNERS[root_token].setdefault('signal_receipts',{});receipts[key]=dict(result=result)
        append_job_event('signal-result',dict(token=root_token,owner=owner,operation_key=key,result=result))
        return result


def close_job_pidfd(root_token,target_token,target_identity,descriptor):
    if not os.environ.get('S1_JOB_LEDGER'):
        os.close(descriptor);return None
    with _job_mutex(root_token):
        owner=_job_owner(root_token,JOB_HANDLES.get(root_token));state=_job_state(job_ledger_events())
        pin=next((value for value in state['operations'].values() if value['kind']=='pin' and value['token']==target_token and value['target']==target_identity and value['descriptor']==descriptor),None)
        if pin is None or pin['owner']!=owner:raise ValueError('pidfd close lacks exact durable pin')
        key=_job_operation_key(owner,'close',dict(token=target_token,target=target_identity,descriptor=descriptor))
        old=state['operations'].get(key)
        if old is not None:
            if old.get('kind')!='close' or old.get('descriptor')!=descriptor:raise ValueError('pidfd close operation conflict')
            if old['state']=='complete':return dict(old['result'])
            receipt=JOB_OWNERS[root_token].setdefault('close_receipts',{}).get(key)
            if receipt!={'closed':True,'error':None}:raise ValueError('pidfd close claim unresolved; no repeated close')
            append_job_event('pidfd-closed',dict(token=target_token,owner=owner,operation_key=key,descriptor=descriptor,result=receipt))
            return dict(receipt)
        append_job_event('pidfd-close-claim',dict(token=target_token,owner=owner,operation_key=key,descriptor=descriptor))
        try:
            os.close(descriptor);result=dict(closed=True,error=None)
        except BaseException as exc:
            uncertainty=dict(closed=None,error=type(exc).__name__)
            JOB_OWNERS[root_token].setdefault('close_receipts',{})[key]=uncertainty
            append_job_event('operation-uncertain',dict(token=target_token,owner=owner,operation_key=key,phase='close',reason=type(exc).__name__))
            raise
        JOB_OWNERS[root_token].setdefault('close_receipts',{})[key]=result
        append_job_event('pidfd-closed',dict(token=target_token,owner=owner,operation_key=key,descriptor=descriptor,result=result))
        return result


def signal_owned_pid(pid,sig,deadline):
    """Signal one retained process incarnation through one durable pidfd operation."""
    owned=JOB_PROCESSES.get(pid)
    if not os.environ.get('S1_JOB_LEDGER') or owned is None:
        return os.kill(pid,sig)
    token,handle=owned
    state=_job_state(job_ledger_events());target=state['roots'].get(token) or state['descendants'].get(token)
    if target is None or target['state']!='live' or target['identity']['pid']!=pid:raise ValueError('signal exact live owned pid')
    owner_token=token
    root_handle=JOB_HANDLES.get(owner_token)
    if root_handle is None:raise ValueError('signal owning process handle unavailable')
    identity_value=target['identity'];registration=JOB_OWNERS[owner_token]
    selected=next(((key[1],key) for key,value in registration.get('pidfds',{}).items()
        if key[0]==token and value['identity']==identity_value),None)
    if selected is None:
        before=stable_process_identity(pid)
        if any(before[key]!=identity_value[key] for key in ('boot_id','pid','start_ticks','pgid')):raise ValueError('signal target incarnation changed')
        descriptor=os.pidfd_open(pid,0)
        after=stable_process_identity(pid)
        if any(after[key]!=identity_value[key] for key in ('boot_id','pid','start_ticks','pgid')):raise ValueError('signal pidfd incarnation changed')
        register_job_pidfd_pin(owner_token,token,identity_value,descriptor)
    else:descriptor=selected[0]
    return signal_job_pidfd(owner_token,token,identity_value,descriptor,sig,deadline)


def _job_creator():
    pid=os.getpid();tid=_thread.get_native_id()
    boot=Path('/proc/sys/kernel/random/boot_id').read_text().strip()
    process=identity(pid);task=thread_identity(pid,tid)
    return dict(boot_id=boot,pid=pid,start_ticks=process['start_ticks'],pgid=process['pgid'],
        tid=tid,thread_start_ticks=task['start_ticks'])


def reserve_job_root(role,label,*,allow_descendant=True,candidate=None):
    if not os.environ.get('S1_JOB_LEDGER'):return None
    if role not in ('B','H'):raise ValueError('job role')
    creator=_job_creator();token=uuid.uuid4().hex
    candidate_receipt=None if candidate is None else _candidate_receipt(candidate)
    if (role=='B') != (candidate_receipt is not None):raise ValueError('process reservation requires actual candidate descriptor')
    def guard(state):
        if state['terminal'] or state['session_id'] is None:raise ValueError('unbound Main H session')
        parent=next((key for key,row in state['roots'].items() if row.get('role')=='B' and row.get('label')!='capture runner' and row['state']=='live' and all(row.get('identity',{}).get(field)==creator[field] for field in ('boot_id','pid','start_ticks','pgid'))),None) if allow_descendant else None
        if parent is None and state['B']+(role=='B')+max(1,state['H']+(role=='H'))>8:
            raise ValueError('job root capacity')
        if parent:return 'descendant-reserved',dict(token=token,root=parent,role=role,label=label,creator=creator,**({} if candidate_receipt is None else {'candidate':candidate_receipt}))
        return 'root-reserved',dict(token=token,role=role,label=label,creator=creator,**({} if candidate_receipt is None else {'candidate':candidate_receipt}))
    # Parent selection and capacity are atomic under the interprocess lock.
    append_job_event('root-reserved',dict(token=token,role=role,label=label,creator=creator),guard=guard)
    return token


def bind_job_root(token,identity_value,handle,*,thread=False):
    if token is None:return
    if type(identity_value) is not dict:raise ValueError('job identity')
    with _JOB_REGISTRY_LOCK:
        if token in JOB_HANDLES:raise ValueError('duplicate job handle')
        state=_job_state(job_ledger_events());session_id=state['session_id']
        if type(session_id) is not int:raise ValueError('Main session binding unavailable')
        current=identity(os.getpid());boot=Path('/proc/sys/kernel/random/boot_id').read_text().strip()
        owner=dict(boot_id=boot,owner_pid=os.getpid(),owner_start_ticks=current['start_ticks'],main_session_id=session_id,
            root_token=token,nonce=uuid.uuid4().hex,handle_object_id=id(handle))
        JOB_HANDLES[token]=handle;JOB_OWNERS[token]=dict(owner=owner,wait_receipt=None);JOB_MUTEXES[token]=_thread.allocate_lock()
    def guard(state):
        event='descendant-bound' if token in state['descendants'] else 'root-bound'
        return event,dict(token=token,identity=identity_value,
            handle=dict(kind='Thread' if thread else 'process',object_id=id(handle)),owner=owner)
    append_job_event('root-bound',{},guard=guard)
    method_name='join' if thread else 'wait'
    try:original_wait=getattr(handle,method_name)
    except AttributeError:original_wait=None
    if original_wait is not None and not thread:
        def retained_wait(*args,**kwargs):return _wait_job_handle(token,handle,original_wait,args,kwargs,thread=thread)
        try:setattr(handle,method_name,retained_wait)
        except (AttributeError,TypeError):raise ValueError('exact process wait hook unavailable') from None


def wait_job_root(token,handle,*,terminal,retire=True,perform_wait=False,wait_args=(),wait_kwargs=None):
    if token is None:return
    if JOB_HANDLES.get(token) is not handle:raise ValueError('different job handle')
    if perform_wait:
        thread=type(handle).__name__=='_ThreadHandle' or isinstance(handle, __import__('threading').Thread)
        method=handle.join if thread else handle.wait
        _wait_job_handle(token,handle,method,tuple(wait_args),dict(wait_kwargs or {}),thread=thread)
    state=_job_state(job_ledger_events());row=state['roots'].get(token) or state['descendants'].get(token)
    receipt=JOB_OWNERS.get(token,{}).get('wait_receipt')
    if row is None or receipt is None or row['state'] not in ('waited','retired'):
        raise ValueError('durable same-handle wait result required')
    recorded=receipt['terminal']
    if 'stopped' in terminal:
        alive=handle.is_alive() if hasattr(handle,'is_alive') else not handle.is_done()
        if terminal['stopped'] is not True or alive:raise ValueError('thread root still live')
    if 'pid' in terminal and (terminal['pid']!=recorded.get('pid') or terminal.get('returncode',recorded.get('returncode'))!=recorded.get('returncode')):
        raise ValueError('same-handle wait terminal differs')
    if token in state['descendants']:
        if not retire:raise ValueError('descendant terminal required')
        return
    if retire:
        current=_job_state(job_ledger_events());root=current['roots'][token]
        if root['state']=='waited' and not any(child['root']==token and child['state']!='retired' for child in current['descendants'].values()):
            append_job_event('root-retired',dict(token=token,terminal=root['terminal']))


def finalize_waited_job_root(token,handle,pid):
    """Finish only the exact already-waited process tree; never repeat its wait."""
    if JOB_HANDLES.get(token) is not handle:
        raise ValueError('waited root exact returned handle')
    state=_job_state(job_ledger_events());root=state['roots'].get(token)
    if root is None or root.get('handle')!=dict(kind='process',object_id=id(handle)) or root.get('identity',{}).get('pid')!=pid:
        raise ValueError('waited root handle/identity')
    terminal=root.get('terminal')
    observed=terminal.get('returncode') if type(handle) is not int else terminal.get('wait_status')
    expected=handle.returncode if type(handle) is not int else JOB_OWNERS[token].get('wait_receipt',{}).get('returncode')
    if type(terminal) is not dict or terminal.get('method')!='matching child wait' or terminal.get('pid')!=pid or observed!=expected or root['state'] not in ('waited','retired'):
        raise ValueError('waited root terminal mismatch')
    if any(child['root']==token and child['state']!='retired' for child in state['descendants'].values()):
        raise ValueError('waited root descendants unresolved')
    if root['state']=='waited':
        append_job_event('root-retired',dict(token=token,terminal=root['terminal']))
    if _job_state(job_ledger_events())['roots'][token]['state']!='retired':
        raise ValueError('waited root retirement not durable')
    if JOB_PROCESSES.get(pid)==(token,handle):del JOB_PROCESSES[pid]


def acknowledge_job_descendant(worker_pid,child_pid,census_row):
    """Main test runner's live ancestry acknowledgment before L35 release."""
    if not os.environ.get('S1_JOB_LEDGER'):return None
    if type(census_row) is not dict or census_row.get('pid')!=child_pid or census_row.get('ppid')!=worker_pid:
        raise ValueError('L35 census ancestry')
    selected={}
    def guard(state):
        for token,row in state['descendants'].items():
            if row['state']=='live' and row.get('identity',{}).get('pid')==child_pid:
                root=state['roots'][row['root']]
                if root.get('identity',{}).get('pid')==worker_pid:
                    selected.update(token=token,root=row['root'],identity=row['identity'])
                    break
        if not selected:raise ValueError('L35 live descendant not in shared ledger')
        identity_value=selected['identity']
        if any(identity_value.get(key)!=census_row.get(key) for key in ('boot_id','pid','ppid','pgid','start_ticks')):
            raise ValueError('L35 ledger/census identity differs')
    event=append_job_event('descendant-ack',dict(worker_pid=worker_pid,child_pid=child_pid,census=census_row),guard=guard)
    rows=job_ledger_events()
    if rows[-1]!=event:raise ValueError('L35 durable descendant acknowledgment')
    return selected


def retire_job_descendant_pidfd(selected,pidfd,deadline):
    """A live-opened pidfd witnesses terminal state for a reparented child."""
    if selected is None:return
    import select
    state=_job_state(job_ledger_events())
    token=selected['token'];row=state['descendants'].get(token)
    if row is None or row['state'] not in ('live','waited','retired') or row.get('identity')!=selected['identity']:
        raise ValueError('L35 descendant identity changed')
    pin=next((value for value in state['operations'].values() if value['kind']=='pin' and value['token']==token and value['descriptor']==pidfd and value['target']==selected['identity']),None)
    if pin is None:raise ValueError('L35 pidfd lacks exact durable pin record')
    receipts=JOB_OWNERS.get(selected['root'],{}).setdefault('pidfd_terminal_receipts',{})
    receipt_key=(token,pidfd)
    if pin['state']!='closed':
        poll=select.poll();poll.register(pidfd,select.POLLIN)
        while not poll.poll(0) and time.monotonic()<deadline:
            poll.poll(max(0,min(5,math.ceil((deadline-time.monotonic())*1000))))
        if not poll.poll(0):raise ValueError('L35 pidfd not terminal by original safety deadline')
        receipts[receipt_key]=dict(identity=selected['identity'],terminal=True)
    close_job_pidfd(selected['root'],token,selected['identity'],pidfd)
    after=_job_state(job_ledger_events());row=after['descendants'][token]
    # Another retained pidfd for the same identity may be owned by stop_group.
    # Retirement waits until each exact descriptor has one durable close receipt.
    pins=[value for value in after['operations'].values() if value['kind']=='pin' and value['token']==token and value['target']==selected['identity']]
    if any(pin['state']!='closed' for pin in pins):return
    if row['state']=='retired':return
    if row['state']!='waited' and receipts.get(receipt_key)!=dict(identity=selected['identity'],terminal=True):
        raise ValueError('pidfd terminal owner receipt unavailable; descendant remains charged')
    owner=_job_owner(selected['root'],JOB_HANDLES[selected['root']])
    operation_key=_job_operation_key(owner,'pidfd-terminal',selected['identity'])
    append_job_event('descendant-retired',dict(token=token,method='identity-bound pidfd terminal',identity=selected['identity'],owner=owner,operation_key=operation_key))
    after=_job_state(job_ledger_events())
    root=after['roots'][selected['root']]
    if root['state']=='waited' and not any(item['root']==selected['root'] and item['state']!='retired' for item in after['descendants'].values()):
        append_job_event('root-retired',dict(token=selected['root'],terminal=root['terminal'],method='matching wait and pidfd terminal'))


def thread_job_identity(thread):
    pid=os.getpid();tid=thread.native_id
    if type(tid) is not int or tid<=0 or type(thread.ident) is not int or thread.ident<=0:
        raise ValueError('unbound native thread')
    process=identity(pid);task=thread_identity(pid,tid)
    return dict(boot_id=Path('/proc/sys/kernel/random/boot_id').read_text().strip(),pid=pid,
        pgid=process['pgid'],start_ticks=process['start_ticks'],tid=tid,
        thread_start_ticks=task['start_ticks'],ident=thread.ident)

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


def create_owned_process(event,create,*args,deadline=None,admission_observer=None,**kwargs):
    """Common real creation gate; callers retain the returned handle immediately."""
    candidate=None
    if os.environ.get('S1_JOB_LEDGER'):
        candidate=_prepare_owned_candidate(create,args,kwargs)
    if os.environ.get('S1_OWNED_ROOT_NOTE'):
        observed=predispatch_owned(event)
        if admission_observer is not None:admission_observer(observed)
    from .s1_progress import before
    before(deadline)
    token=reserve_job_root('B',event,candidate=candidate) if candidate is not None else None
    if candidate is not None:
        descriptor,environment,frozen_args,frozen_kwargs=candidate
        checked=_prepare_owned_candidate(create,frozen_args,frozen_kwargs)
        if checked[0]!=descriptor or checked[1]!=environment:
            raise ValueError('process candidate changed after durable reservation')
        handle=create(*checked[2],**checked[3])
    else:handle=create(*args,**kwargs)
    if token is not None:
        pid=handle if type(handle) is int else handle.pid
        # Creation uncertainty stays reserved if this complete identity read fails.
        bind_job_root(token,stable_process_identity(pid),handle)
        JOB_PROCESSES[pid]=(token,handle)
        state=_job_state(job_ledger_events())
        if token in state['descendants']:
            child=state['descendants'][token]
            census_row=stable_process_identity(pid)
            if any(census_row.get(key)!=child['identity'].get(key) for key in ('boot_id','pid','ppid','pgid','start_ticks')) or child['creator']['pid']!=os.getpid() or census_row['ppid']!=os.getpid():
                raise ValueError('descendant live creation census changed')
            append_job_event('descendant-creator-ack',dict(token=token,root=child['root'],creator=child['creator'],identity=child['identity'],census=census_row))
    return handle


def register_owned(pid,event='spawn'):
    if os.environ.get('S1_OWNED_ROOT_NOTE'):
        return INVOCATION.register(pid,event)


def retire_owned(pid,handle=None):
    """Called only after a matching child wait, including registration failure."""
    owned=JOB_PROCESSES.get(pid)
    if owned is not None and handle is not None and owned[1] is not handle:
        raise ValueError('different returned process handle')
    if owned is None and handle is not None and os.environ.get('S1_JOB_LEDGER'):
        state=_job_state(job_ledger_events())
        matches=[(token,row) for token,row in state['roots'].items() if row.get('identity',{}).get('pid')==pid and JOB_HANDLES.get(token) is handle]
        if len(matches)!=1 or matches[0][1]['state']!='retired' or any(child['root']==matches[0][0] and child['state']!='retired' for child in state['descendants'].values()):
            raise ValueError('same-handle retired tree required for repeat cleanup')
        return
    with INVOCATION.lock:
        for key,record in list(INVOCATION.records.items()):
            if record['pid']==pid:
                record.update(state='retired',retirement='matching child wait')
                if key[2] is None:del INVOCATION.records[key]
    if owned is not None:
        token,handle=owned
        state=_job_state(job_ledger_events())
        if token in state['roots']:
            current=state['roots'][token]
            for (target_token,descriptor),pin in list(JOB_OWNERS[token].get('pidfds',{}).items()):
                if target_token==token:
                    operation=next((value for value in state['operations'].values() if value['kind']=='pin' and value['token']==token and value['descriptor']==descriptor),None)
                    if operation is not None and operation['state']=='open':close_job_pidfd(token,token,pin['identity'],descriptor)
                    state=_job_state(job_ledger_events())
            if current['state']=='waited':
                if not any(child['root']==token and child['state']!='retired' for child in state['descendants'].values()):
                    finalize_waited_job_root(token,handle,pid)
            elif current['state']!='retired':raise ValueError('retire_owned unresolved root')
            retired=_job_state(job_ledger_events())['roots'][token]['state']=='retired'
        else:
            child=state['descendants'].get(token)
            if child is None or child['state'] not in ('waited','retired'):raise ValueError('retire_owned unresolved descendant')
            parent=state['roots'][child['root']]
            registration=JOB_OWNERS[token]
            for (target_token,descriptor),pin in list(registration.get('pidfds',{}).items()):
                if target_token==token:
                    close_job_pidfd(child['root'],token,pin['identity'],descriptor)
            state=_job_state(job_ledger_events());child=state['descendants'][token];parent=state['roots'][child['root']]
            if child['state']=='waited':
                if any(value['kind']=='pin' and value['token']==token and value['state']!='closed' for value in state['operations'].values()):return
                receipt=JOB_OWNERS[token].get('wait_receipt')
                if receipt is None:raise ValueError('descendant wait receipt unavailable')
                append_job_event('descendant-retired',dict(token=token,method='matching child wait',terminal=child['terminal'],
                    handle_object_id=id(handle),owner=child['owner'],operation_key=receipt['operation_key']))
                state=_job_state(job_ledger_events());child=state['descendants'][token];parent=state['roots'][child['root']]
            if parent['state']=='waited' and not any(row['root']==child['root'] and row['state']!='retired' for row in state['descendants'].values()):
                append_job_event('root-retired',dict(token=child['root'],terminal=parent['terminal']))
            retired=child['state']=='retired'
        if retired:
            if JOB_PROCESSES.get(pid)==(token,handle):del JOB_PROCESSES[pid]


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
    if os.environ.get('S1_JOB_LEDGER'):
        state=_job_state(job_ledger_events());B=state['B'];H=state['H']
    else:
        B=sum(len(record['threads']) for record in records);H=0
    return dict(root_pid=root_pid,processes=records,B=B,H=H,charge=owned_charge(B,H),complete=True)


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
        if os.environ.get('S1_JOB_LEDGER'):
            logical=_job_state(job_ledger_events());B=logical['B'];H=logical['H']
            if unresolved:raise ValueError('owned unresolved process identity blocks dispatch')
        else:
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
        if note['run_directory']!=anchor['directory'] or note['command']!=anchor['command']:raise ValueError('owned output/command binding')
        if os.environ.get('S1_OWNED_ROOT_NOTE')!=anchor['note_path'] or os.environ.get('S1_VALIDATION_RUN_DIRECTORY',anchor['directory'])!=anchor['directory']:raise ValueError('owned environment locator')
        run=repository/'docs/resolve-blocker/plan031-progress-20260922'
        dispatch_path=run/'implementation-dispatch-049.json';dispatch_raw=dispatch_path.read_bytes();dispatch=json.loads(dispatch_raw)
        dispatch_record=dict(path=str(dispatch_path),bytes=len(dispatch_raw),sha256=hashlib.sha256(dispatch_raw).hexdigest())
        status=dispatch['implementation_status_snapshot'];plan=dispatch['plan']
        if dispatch.get('schema')!='plan049-implementation-dispatch/v1' or plan['path']!=str(repository/'plans/plan_049.md') or status['path']!=str(run/'implementation-status-049.md'):raise ValueError('owned fixed Plan049 authority')
        original_plan=dict(path=str(repository/'plans/plan_049.md'),sha256='a27329ee5c9d9439515093e6797ad72f61bd6faf1e43c5f45f2b2cf4c013cc1f')
        if plan!=original_plan:raise ValueError('owned original Plan049 dispatch authority')
        current_plan_raw=(repository/'plans/plan_049.md').read_bytes()
        current_plan=dict(path=str(repository/'plans/plan_049.md'),bytes=len(current_plan_raw),sha256=hashlib.sha256(current_plan_raw).hexdigest())
        if dispatch_record not in note['bindings'] or current_plan not in note['bindings'] or note['status']!={k:status[k] for k in ('bytes','sha256')}:raise ValueError('owned dispatch/plan/status binding')
        if note['cwd']!=str(repository) or str(run/'launch-049-exec.py')!=note['driver']['path']:raise ValueError('owned launch authority')
        ancestors=[];cursor=root['ppid'];seen=set()
        for recorded in note['preexisting_ancestors']:
            if cursor in seen or cursor!=recorded['pid'] or cursor not in rows:raise ValueError('owned truncated/cyclic ancestry')
            seen.add(cursor)
            expected=dict(boot_id=boot,**{k:rows[cursor][k] for k in ('pid','ppid','pgid','start_ticks')})
            if any(recorded[k]!=v for k,v in expected.items()) or recorded['start_ticks']>root['start_ticks']:raise ValueError('owned ancestry changed')
            ancestors.append(dict(recorded,exclusion_reason='pre-existing kernel ancestry'));cursor=rows[cursor]['ppid']
        if cursor!=0 or not ancestors or note['ancestry_terminal']!={'pid':ancestors[-1]['pid'],'ppid':0}:raise ValueError('owned incomplete ancestry termination')
        if note['retained_wrappers']:raise ValueError('unvalidated retained wrapper ownership')
        # Named local authority predicates fail before cross-record validation.
        # Every successful path still verifies the complete current proof graph.
        no_timeout_launch(dict(path=str(note_path),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest()),anchor['directory'],diagnostic=note['kind']=='diagnostic')
        source_membership(note['sources'],repository)
        for rec in note['bindings']+note['sources']+[note['driver'],status]:
            current=Path(rec['path']).read_bytes()
            if len(current)!=rec['bytes'] or hashlib.sha256(current).hexdigest()!=rec['sha256']:raise ValueError('owned source/dispatch bytes changed')
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
            env,deadline=self.session.ready_deadline,admission_observer=lambda observed:self.session.events.append(dict(event='owned_dispatch',role=role,**observed)),file_actions=actions,setsid=True)

    def observe_identity(self, pid):
        return identity(pid)

    def observe(self):
        return census()

    def signal_group(self, pid, sig):
        if os.environ.get('S1_JOB_LEDGER'):
            signal_owned_pid(pid,sig,self.session.cleanup_deadline)
        else:os.killpg(pid, sig)

    def reap_child(self, pid):
        result=wait_owned_pid(pid,os.WNOHANG)
        if result[0]==pid:retire_owned(pid)
        return result

    def run(self):
        if os.environ.get('S1_JOB_LEDGER'):
            self.native_job_identity=dict(_job_creator(),ident=_thread.get_ident())
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
                    # spawn's common creation gate performs the one fresh audit;
                    # its observation and original deadline check precede syscall.
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
            self.job_thread=reserve_job_root('H','Session owner thread',allow_descendant=False) if os.environ.get('S1_JOB_LEDGER') else None
            self.handle=_thread.start_joinable_thread(self.owner.run,daemon=False)
            self.owner.handle=self.handle; self.state='running'
            if self.job_thread is not None:
                while not hasattr(self.owner,'native_job_identity') and time.monotonic()<self.ready_deadline:
                    time.sleep(.001)
                if not hasattr(self.owner,'native_job_identity'):raise ValueError('native owner thread identity unresolved')
                bind_job_root(self.job_thread,self.owner.native_job_identity,self.handle,thread=True)
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
            if getattr(self,'job_thread',None) is not None:
                wait_job_root(self.job_thread,self.handle,terminal=dict(method='same joinable handle join',stopped=True,native_identity=self.owner.native_job_identity),perform_wait=True,wait_args=(0,))
            else:self.handle.join(0)
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

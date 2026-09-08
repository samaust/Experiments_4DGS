"""Immutable finite artifacts and fsynced, checksummed attempt journals."""
import gzip
import hashlib
import json
import os
from pathlib import Path
import tempfile
import time
import numpy as np

class PersistenceError(RuntimeError):
    pass

def canonical(value):
    if isinstance(value,np.ndarray):return value.tolist()
    if isinstance(value,np.generic):return value.item()
    raise TypeError('unsupported JSON type '+type(value).__name__)

def encode(value):
    return json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False,default=canonical).encode()

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def sync_dir(path):
    fd=os.open(path,os.O_RDONLY|os.O_DIRECTORY)
    try:os.fsync(fd)
    finally:os.close(fd)

def publish(path,value,fault=None):
    path=Path(path)
    payload=encode(value)
    if path.suffix=='.gz':payload=gzip.compress(payload,mtime=0)
    path.parent.mkdir(parents=True,exist_ok=True)
    fd,tmp=tempfile.mkstemp(prefix='.v10-',dir=path.parent)
    try:
        with os.fdopen(fd,'wb') as f:f.write(payload);f.flush();os.fsync(f.fileno())
        if fault=='before_publish':raise PersistenceError(fault)
        os.link(tmp,path)
        sync_dir(path.parent)
    finally:
        Path(tmp).unlink(missing_ok=True);sync_dir(path.parent)
    if fault=='after_publish':raise PersistenceError(fault)
    return sha(path)

def read(path):
    path=Path(path);data=path.read_bytes()
    if path.suffix=='.gz':data=gzip.decompress(data)
    result=json.loads(data,parse_constant=lambda v: (_ for _ in ()).throw(ValueError('nonfinite '+v)))
    encode(result)
    return result

def journal_prefix(path):
    path=Path(path);events=[];previous='0'*64;valid_bytes=0
    if not path.exists():return dict(events=[],valid_bytes=0,complete=False,reason='missing journal')
    data=path.read_bytes()
    for line in data.splitlines(keepends=True):
        try:
            if not line.endswith(b'\n'):raise ValueError('truncated line')
            row=json.loads(line);checksum=row.pop('checksum')
            assert row['seq']==len(events) and row['previous']==previous
            assert hashlib.sha256(encode(row)).hexdigest()==checksum
        except (ValueError,KeyError,AssertionError):break
        row['checksum']=checksum;events.append(row);previous=checksum;valid_bytes+=len(line)
    return dict(events=events,valid_bytes=valid_bytes,complete=valid_bytes==len(data),reason=None if valid_bytes==len(data) else 'invalid suffix; execution beyond valid prefix unknown')

class Journal:
    def __init__(self,path,recover=False):
        self.path=Path(path);self.path.parent.mkdir(parents=True,exist_ok=True)
        if self.path.exists() and not recover:raise FileExistsError(self.path)
        prefix=journal_prefix(self.path)
        if self.path.exists() and not prefix['complete']:raise PersistenceError('cannot append after invalid journal suffix')
        self.seq=len(prefix['events']);self.previous=prefix['events'][-1]['checksum'] if self.seq else '0'*64
        self.state=None
    def append(self,event,**data):
        try:
            row=dict(seq=self.seq,previous=self.previous,event=event,unix=time.time(),**data)
            checksum=hashlib.sha256(encode(row)).hexdigest();row['checksum']=checksum
            with self.path.open('ab') as f:f.write(encode(row)+b'\n');f.flush();os.fsync(f.fileno())
            if self.seq==0:sync_dir(self.path.parent)
            self.seq+=1;self.previous=checksum
        except Exception as e:raise PersistenceError(str(e)) from e

class Observed(dict):
    """Status writes by numerical routines synchronize their actual return boundary."""
    def __init__(self,data,journal,index):
        super().__init__(data);self.journal=journal;self.index=index
    def __setitem__(self,key,value):
        if key=='status' and self.journal:
            self.journal.append('numerical_return',index=self.index,status=value)
        super().__setitem__(key,value)

def commit_attempt(directory,item,verify,fault=None):
    directory=Path(directory);artifact=directory/'attempt.json.gz'
    try:
        digest=publish(artifact,item,fault=fault)
        return recover_attempt(directory,verify,expected=digest)
    except Exception as e:raise PersistenceError(type(e).__name__+': '+str(e)) from e

def recover_attempt(directory,verify,expected=None):
    """Reconstruct receipt/completion only; this function never executes a solver."""
    directory=Path(directory);artifact=directory/'attempt.json.gz';digest=sha(artifact)
    if expected is not None and digest!=expected:raise PersistenceError('artifact hash mismatch')
    item=read(artifact);proof=verify(item,directory)
    if not proof['passed']:raise PersistenceError('independent verification failed')
    receipt=directory/'receipt.json'
    if receipt.exists():
        saved=read(receipt)
        if saved['artifact_sha256']!=digest or saved['id']!=item['id']:raise PersistenceError('receipt identity/hash mismatch')
    else:publish(receipt,dict(id=item['id'],artifact_sha256=digest,verification=proof,verified_unix=time.time()))
    j=Journal(directory/'journal.jsonl',recover=True)
    completed=[e for e in journal_prefix(j.path)['events'] if e['event']=='completed']
    if completed:
        if len(completed)!=1 or completed[0]['artifact_sha256']!=digest or completed[0]['receipt_sha256']!=sha(receipt):raise PersistenceError('completion mismatch')
    else:j.append('completed',id=item['id'],artifact_sha256=digest,receipt_sha256=sha(receipt))
    return dict(id=item['id'],artifact=str(artifact),sha256=digest,receipt=str(receipt),receipt_sha256=sha(receipt))

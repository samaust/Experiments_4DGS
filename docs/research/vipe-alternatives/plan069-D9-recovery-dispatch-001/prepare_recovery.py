"""Prepare a private D9 recovery REVIEW; dispatch requires separate fresh approval.

All locations are explicit. REVIEW never writes the shared run. The dispatcher
uses existing checked admission and supervision; it creates no DO or source review.
"""
import argparse
import copy
import json
from pathlib import Path
import subprocess
import sys

JOB='plan069-D9-setup-recovery-001'
OLD='plan069-D9-setup-001'


def require(condition,message):
    if not condition:raise ValueError(message)


def checked_checkout(checkout):
    checkout=Path(checkout).resolve()
    require((checkout/'scripts/vipe_benchmark').is_dir(),'explicit code checkout required')
    changed=subprocess.check_output(['git','status','--porcelain','--untracked-files=no'],cwd=checkout,text=True)
    require(not changed.strip(),'tracked checkout must be clean')
    sys.path.insert(0,str(checkout/'scripts'))
    from vipe_benchmark.config import ROOT
    require(ROOT.resolve()==checkout,'imported code checkout differs')
    return checkout


def validate_qualification(receipt,sources,checkout):
    """Require the root's actual CPU capture over every exact executable source."""
    require(receipt.get('schema')=='plan069-delta-cpu-test-capture/v1' and
        receipt.get('record_kind')=='actual' and receipt.get('passed') is True and
        receipt.get('within_wall_limit') is True and receipt.get('source_bytes_unchanged') is True and
        receipt.get('sources_before')==receipt.get('sources_after') and receipt.get('checkout')==str(checkout),
        'current passing combined CPU qualification required')
    qualified=receipt['sources_before']
    require(all(record in qualified for record in sources),'execution source not covered by CPU qualification')
    commands=receipt.get('commands',[])
    require(bool(commands) and all(row.get('returncode')==0 and row.get('timed_out') is False and
        row.get('cleanup',{}).get('confirmed_no_surviving_observed_processes') is True and
        row.get('cleanup',{}).get('surviving_observed_owned_processes')==[] for row in commands),
        'CPU qualification command failed or cleanup is uncertain')


def retained_original(root,events):
    from vipe_benchmark.files import file_record,read_json,verify_record
    def one(event,job):
        rows=[row for row in events if row.get('event')==event and row.get('job_id')==job]
        require(len(rows)==1,'unique retained '+event+' required');return rows[0]
    grants=[row for row in events if row.get('event')=='depth_setup_authorized' and row.get('candidate')=='D9']
    require(len(grants)==1,'unique original D9 setup grant required')
    grant=grants[0];reserve=one('reserve',OLD);finish=one('finish',OLD)
    require(grant['sequence']==761 and finish['sequence']==765 and finish.get('status')=='failed' and
        finish.get('cleanup_confirmed') is True and finish.get('cleanup_uncertain') is False and
        finish.get('surviving_pids')==[] and finish.get('deadline_exceeded') is False,
        'exact preserved failed D9 attempt required')
    request=reserve['evidence']['request'];verify_record(request)
    original_request=read_json(request['path']);old_review=read_json(verify_record(grant['review'])['path'])
    proposals=[row for row in old_review['proposals'] if row['candidate']=='D9']
    require(len(proposals)==1,'original D9 proposal required');maps=proposals[0]
    from vipe_benchmark.files import object_hash
    require(object_hash(maps)==grant['proposal_sha256'],'original approved proposal changed')
    asset=read_json(verify_record(maps['required_assets'])['path'])['candidates']['D9']['files'][0]
    checkpoint=root/'jobs'/OLD/asset['path'];info=checkpoint.stat()
    identity=dict(device=info.st_dev,inode=info.st_ino,size=info.st_size,mtime_ns=info.st_mtime_ns)
    receipts=[]
    for path in (root/'transfers').glob('transfer-*.json'):
        value=read_json(path)
        if value.get('output')==str(checkpoint):receipts.append((file_record(path),value))
    require(len(receipts)==1 and receipts[0][1].get('output_identity')==identity and
        receipts[0][1].get('error') is None and receipts[0][1].get('bytes_received')==asset['bytes'] and
        info.st_size==asset['bytes'] and not checkpoint.is_symlink(),'unchanged retained model metadata required')
    # Existing approved LFS bytes and acquisition inode, not a new payload read.
    checkpoint_record=dict(path=str(checkpoint),sha256=asset['lfs_sha256'],bytes=asset['bytes'])
    source=root/'jobs'/OLD/'source'
    from vipe_benchmark.video_native import native_source_records
    source_files=native_source_records(source)
    original=dict(grant_event_sha256=grant['event_sha256'],failed_finish_event_sha256=finish['event_sha256'],
        byte_checkpoint=grant['byte_checkpoint'],request=request,source_archive=file_record(root/'jobs'/OLD/'source.tar.gz'),
        source_files=source_files,checkpoint=checkpoint_record,runtime_failure=file_record(root/'jobs'/OLD/'runtime/failure.json'),
        dependency_lock=file_record(root/'jobs'/OLD/'runtime/requirements.lock'))
    return original,original_request,maps,receipts[0][0]


def prepare_review(checkout,root,output):
    from vipe_benchmark.config import load
    from vipe_benchmark.ledger import Ledger
    from vipe_benchmark.files import file_record,read_json,object_hash,write_json
    from vipe_benchmark.video_environment import FRAME_RECIPE,environment_request,bind_source_environment
    from vipe_benchmark.depth_admission import VIDEO_FRAME_PROFILES
    require(not output.exists() and not output.is_relative_to(root),'fresh private REVIEW output required')
    events=Ledger(root/'ledger.jsonl',dict(load(),new_download_gib_limit=110,new_artifact_disk_gib_limit=210)).events()
    original,old_request,oldmap,transfer=retained_original(root,events)
    maps=copy.deepcopy(oldmap);maps.update(runtime_recipe=file_record(FRAME_RECIPE),profile_inventory=file_record(VIDEO_FRAME_PROFILES),
        profile=read_json(VIDEO_FRAME_PROFILES)['profiles']['D9'])
    require(maps['allocation']==oldmap['allocation'] and maps['max_attempts']==1,'original combined caps required')
    recovery=dict(schema='plan069-video-setup-recovery-proposal/v1',status='REVIEW',candidate='D9',job_id=JOB,
        max_attempts=1,recovery_seconds=1200,original_setup=original,map_proposal_sha256=object_hash(maps),
        runtime_recipe=maps['runtime_recipe'],profile_inventory=maps['profile_inventory'])
    review=dict(schema='plan069-depth-execution-review/v1',status='REVIEW',scope='D9 frame-input setup recovery only',
        proposals=[maps],setup_recovery_proposal=recovery,asset_inventory=maps['required_assets'])
    prior=old_request['runtime_environment']
    environment=environment_request('D9',root,seed_executable=prior['python_seed_executable'],uv_executable=prior['uv']['path'],
        media_tools={key:record['path'] for key,record in prior['media_tools'].items()},recipe_path=FRAME_RECIPE)
    environment=bind_source_environment(environment,root/'jobs'/OLD/'source',maps['candidate_config']['code']['revision'],
        candidate='D9',record_kind='actual')
    output.mkdir(parents=True,exist_ok=False);write_json(output/'review.json',review)
    request=dict(schema='plan069-video-setup-recovery-request/v1',record_kind='actual',candidate='D9',job_id=JOB,
        ledger_path=str(root/'ledger.jsonl'),review=file_record(output/'review.json'),authorization=None,source_review=None,
        original_setup=original,runtime_environment=environment)
    write_json(output/'request-template.json',request)
    worker=checkout/'scripts/basketball_vipe_video_setup_recovery.py'
    command=[sys.executable,str(worker),'--request',str(root/'requests'/f'{JOB}.json'),'--output',str(root/'jobs'/JOB)]
    write_json(output/'proposal.json',dict(status='REVIEW',automatic_dispatch=False,review=file_record(output/'review.json'),
        request_template=file_record(output/'request-template.json'),worker_command=command,seconds_limit=1200,
        original_checkpoint_transfer=transfer,model_payload_rehashed=False,
        pending=['independent REVIEW approval','explicit matching user DO','fresh source review','combined CPU capture012']))
    return output


def validate_approval(approval,review_record,proposal,maps):
    from vipe_benchmark.files import object_hash
    require(approval.get('schema')=='plan069-depth-user-authorization/v1' and approval.get('status')=='DO' and
        approval.get('review')==review_record and approval.get('setup_recovery_approval')==dict(candidate='D9',
        job_id=JOB,status='approved',max_attempts=1,proposal_sha256=object_hash(proposal)) and
        any(all(row.get(key)==value for key,value in dict(candidate='D9',status='approved',
            max_attempts=1,proposal_sha256=object_hash(maps)).items()) and
            row.get('schema','plan069-depth-execution-approval/v1')=='plan069-depth-execution-approval/v1'
            for row in approval.get('candidate_approvals',[])),'explicit matching one-attempt DO required')


def reservation_evidence(request,review,authorization,source_review,worker,executable):
    return dict(request=request,review=review,authorization=authorization,source_review=source_review,
        worker=worker,executable=executable)


def publish_request(request,path,output,events):
    from vipe_benchmark.files import read_json,write_json,file_record
    require(not output.exists() and not output.is_symlink() and not any(
        row.get('job_id')==JOB and row.get('event') in ('depth_setup_recovery_authorized','reserve','finish')
        for row in events),'one-use recovery already authorized or attempted')
    if path.exists() or path.is_symlink():
        require(not path.is_symlink() and read_json(path)==request,'retained recovery request differs')
    else:write_json(path,request)
    return file_record(path)


def dispatch(checkout,root,review,authorization,source_review,qualification):
    from vipe_benchmark.files import file_record,read_json,verify_record,object_hash
    from vipe_benchmark.config import load
    from vipe_benchmark.ledger import Ledger
    from vipe_benchmark.depth_admission import local_source_records
    from vipe_benchmark.depth_setup_recovery import validate_recovery_request
    from vipe_benchmark.video_environment import environment_request,bind_source_environment
    from vipe_benchmark.video_setup_recovery import validate_recovery_result
    from vipe_benchmark.depth_recovery_lineage import accepted_setup_lineage
    from vipe_benchmark.execution import resources
    from vipe_benchmark.supervisor import supervise
    require(Path('/proc/1/comm').read_text().strip()=='systemd','host PID visibility required')
    records=[file_record(path) for path in (review,authorization,source_review,qualification)]
    review_record,authorization_record,source_record,qualification_record=records
    approved=read_json(review);proposal=approved['setup_recovery_proposal'];source=read_json(source_review)
    require(source['local_sources']==local_source_records('D9'),'fresh reviewed source closure required')
    supplemental=source.get('supplemental_sources',[])
    producer=file_record(Path(__file__))
    require(producer in supplemental,'tracked dispatcher must be independently reviewed')
    for record in supplemental:verify_record(record)
    closure=[*source['local_sources'],*supplemental,proposal['runtime_recipe'],proposal['profile_inventory']]
    validate_qualification(read_json(qualification),closure,checkout)
    require(source.get('cpu_qualification',{}).get('validation')==qualification_record,
        'source review must bind current CPU qualification')
    old=read_json(proposal['original_setup']['request']['path'])['runtime_environment']
    maps=next(row for row in approved['proposals'] if row['candidate']=='D9')
    environment=environment_request('D9',root,seed_executable=old['python_seed_executable'],uv_executable=old['uv']['path'],
        media_tools={key:record['path'] for key,record in old['media_tools'].items()},recipe_path=proposal['runtime_recipe']['path'])
    environment=bind_source_environment(environment,root/'jobs'/OLD/'source',maps['candidate_config']['code']['revision'],
        candidate='D9',record_kind='actual')
    request=dict(schema='plan069-video-setup-recovery-request/v1',record_kind='actual',candidate='D9',job_id=JOB,
        ledger_path=str(root/'ledger.jsonl'),review=review_record,authorization=authorization_record,source_review=source_record,
        original_setup=proposal['original_setup'],runtime_environment=environment)
    request_path=root/'requests'/f'{JOB}.json';output=root/'jobs'/JOB
    # Verify all approval inputs before publishing the immutable live request.
    approval=read_json(authorization)
    validate_approval(approval,review_record,proposal,maps)
    require(source.get('schema')=='plan069-depth-source-review/v1' and source.get('status')=='passed' and
        source.get('candidate')=='D9' and source.get('proposal_sha256')==object_hash(maps) and
        source.get('setup_recovery_proposal_sha256')==object_hash(proposal),'fresh matching source review required')
    config=dict(load(),new_download_gib_limit=110,new_artifact_disk_gib_limit=210);ledger=Ledger(root/'ledger.jsonl',config)
    request_record=publish_request(request,request_path,output,ledger.events())
    normalized=validate_recovery_request(request_record,ledger.events(),root)
    worker=checkout/'scripts/basketball_vipe_video_setup_recovery.py'
    command=[sys.executable,str(worker),'--request',str(request_path),'--output',str(output)]
    worker_record=file_record(worker);executable=file_record(sys.executable)
    ledger.authorize_depth_setup_recovery(request_record,command=command,worker=worker_record,executable=executable)
    limits=normalized['byte_limits']
    def sample():
        reading=resources(root,gpu=True)
        require(reading['download_bytes']<=limits['download_bytes'] and reading['artifact_bytes']<=limits['artifact_bytes'],
            'original recovery absolute byte caps exceeded')
        return reading
    def validate(out):
        validate_recovery_result(file_record(out/'result.json'),request_record,ledger.events(),root)
    outcome=supervise(ledger,JOB,command,output,evidence=reservation_evidence(request_record,review_record,
        authorization_record,source_record,worker_record,executable),
        sample_resources=sample,validate_result=validate,poll_seconds=2.,seconds_limit=normalized['allocation']['setup_seconds'])
    accepted_setup_lineage(file_record(output/'result.json'),ledger.events(),root)
    return outcome


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--checkout',required=True,type=Path);parser.add_argument('--run-root',required=True,type=Path)
    parser.add_argument('--mode',required=True,choices=('review','dispatch'));parser.add_argument('--output',type=Path)
    for field in ('review','authorization','source-review','qualification'):parser.add_argument('--'+field,type=Path)
    args=parser.parse_args();checkout=checked_checkout(args.checkout);root=args.run_root.resolve()
    if args.mode=='review':
        require(args.output is not None,'private output required');print(prepare_review(checkout,root,args.output.resolve()))
    else:
        require(all(getattr(args,key) is not None for key in ('review','authorization','source_review','qualification')),
            'REVIEW, explicit DO, fresh source review and combined qualification required')
        print(json.dumps(dispatch(checkout,root,args.review,args.authorization,args.source_review,args.qualification)))


if __name__=='__main__':main()

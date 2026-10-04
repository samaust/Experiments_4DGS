"""Publish a conditional D10 DO only from explicit approval and actual D9 evidence."""
import argparse
import copy
import fcntl
import json
from pathlib import Path
import sys


def require(value,message):
    if not value:raise ValueError(message)


def prepare(checkout,run,review_path,qualification_path,prefix_path,user_approval_path,output):
    checkout=Path(checkout).resolve();run=Path(run).resolve()
    sys.path.insert(0,str(checkout/'scripts'))
    from vipe_benchmark.config import ROOT
    from vipe_benchmark.files import file_record,read_json,verify_record,object_hash,write_json
    from vipe_benchmark.depth_video_frame_authorization import validate_frame_amendment,unstarted_prefix
    require(ROOT.resolve()==checkout,'exact canonical checkout import required')
    review_record=file_record(review_path);review=read_json(review_path)
    require(review.get('schema')=='plan069-depth-execution-review/v1' and review.get('status')=='REVIEW' and
        len(review.get('proposals',[]))==1 and review['proposals'][0].get('candidate')=='D10',
        'exact separate D10 REVIEW required')
    proposal=review['proposals'][0]
    approval_record=file_record(user_approval_path);approval=read_json(user_approval_path)
    require(approval.get('schema')=='plan069-D10-frame-user-approval/v1' and approval.get('status')=='approved' and
        approval.get('candidate')=='D10' and approval.get('review')==review_record and
        approval.get('proposal_sha256')==object_hash(proposal) and
        type(approval.get('max_attempts')) is int and approval['max_attempts']==1 and
        approval.get('optional_decoder_omission_approved') is True and
        isinstance(approval.get('authorization_basis'),str) and approval['authorization_basis'].strip(),'explicit exact D10 user approval required')
    prior_path=checkout/'docs/research/vipe-alternatives/plan031-execution/depth-approval-003.json'
    prior_record=file_record(prior_path);prior=read_json(prior_path)
    prefix_record=file_record(prefix_path);unstarted_prefix(prefix_record)
    qualification_record=file_record(qualification_path)
    qualified=read_json(qualification_path)
    require(qualified.get('record_kind')=='actual' and qualified.get('candidate')=='D9' and
        qualified.get('status')=='passed','actual passed D9 qualification required')
    setup_record=verify_record(qualified['setup']);setup=read_json(setup_record['path'])
    require(Path(qualified['setup']['path']).resolve().parents[2]==run and
        setup.get('schema')=='plan069-video-setup-recovery-result/v2' and
        setup.get('job_id')=='plan069-D9-setup-recovery-002','accepted recovery002 owned run required')
    result=dict(schema='plan069-depth-user-authorization/v1',status='DO',review=review_record,
        previous_authorization=prior_record,reset_previous_consumption=False,
        authorization_basis=approval['authorization_basis'],user_approval=approval_record,
        candidate_approvals=[dict(schema='plan069-depth-execution-approval/v1',status='approved',candidate='D10',
            max_attempts=1,proposal_sha256=object_hash(proposal))],
        **{key:copy.deepcopy(prior[key]) for key in ('cap_amendment','cap_approval','video_amendment')})
    result['video_frame_amendment']=dict(schema='plan069-video-frame-amendment-approval/v1',status='approved',candidate='D10',
        optional_decoder_omission_approved=True,runtime_recipe=proposal['runtime_recipe'],profile_inventory=proposal['profile_inventory'],
        unstarted_ledger_prefix=review['unstarted_ledger_prefix'],D9_runtime_qualification=qualification_record,
        D9_qualification_ledger_prefix=prefix_record)
    # Hold the read lock through both public gates and publication. No ledger event is written.
    prefix_bytes=Path(prefix_record['path']).read_bytes()
    with (run/'ledger.jsonl').open('rb') as stream:
        fcntl.flock(stream,fcntl.LOCK_SH)
        require(stream.read()==prefix_bytes,'fresh exact current protected qualification prefix required')
        validate_frame_amendment('D10',result,review,root=checkout)
        require(file_record(prefix_path)==prefix_record and file_record(qualification_path)==qualification_record and
            file_record(review_path)==review_record and file_record(user_approval_path)==approval_record and
            file_record(prior_path)==prior_record and verify_record(qualified['setup'])==setup_record,
            'approval or qualification changed during publication')
        path=Path(output).absolute();require(not path.exists() and not path.is_symlink(),'fresh immutable D10 authorization required')
        path.parent.mkdir(parents=True,exist_ok=True);write_json(path,result)
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('checkout','run','review','qualification','qualification-ledger-prefix','user-approval','output'):
        p.add_argument('--'+name,required=True)
    a=p.parse_args();result=prepare(a.checkout,a.run,a.review,a.qualification,a.qualification_ledger_prefix,a.user_approval,a.output)
    print(json.dumps(dict(status=result['status'],candidate='D10')))


if __name__=='__main__':main()

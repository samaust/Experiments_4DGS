"""Select one separately approved D9 recovery without reopening failed setup."""
import copy
import math
from pathlib import Path

from .files import file_record, object_hash


def _require(condition,message):
    if not condition:raise ValueError(message)


def validate_recovery_authorization(candidate,approved,reviewed,*,root):
    """Check REVIEW and both new approvals against protected failed ancestry."""
    from .config import load
    from .ledger import Ledger
    from .depth_setup_recovery import original_setup_lineage
    from .depth_admission import VIDEO_FRAME_PROFILES,selected_profile_inventory
    from .video_environment import FRAME_RECIPE
    _require(candidate=='D9','setup recovery authorization is D9-only')
    expected_review=Path(root)/'docs/specs/plan031-execution/depth-D9-frame-recovery-review-001.json'
    _require(approved.get('schema')=='plan069-depth-user-authorization/v1' and approved.get('status')=='DO' and
        reviewed.get('schema')=='plan069-depth-execution-review/v1' and reviewed.get('status')=='REVIEW' and
        approved.get('review')==file_record(expected_review),'exact new canonical D9 recovery REVIEW and DO required')
    rows=reviewed.get('proposals',[]);recovery=reviewed.get('setup_recovery_proposal')
    _require(len(rows)==1 and rows[0].get('candidate')=='D9' and isinstance(recovery,dict),
        'exact single D9 proposal and separate recovery required')
    maps=rows[0]
    _require(maps.get('schema')=='plan069-depth-execution-proposal/v1' and maps.get('status')=='REVIEW' and
        type(maps.get('max_attempts')) is int and maps['max_attempts']==1 and
        recovery.get('schema')=='plan069-video-setup-recovery-proposal/v1' and recovery.get('status')=='REVIEW' and
        recovery.get('candidate')=='D9' and recovery.get('job_id')=='plan069-D9-setup-recovery-001' and
        type(recovery.get('max_attempts')) is int and recovery['max_attempts']==1 and
        type(recovery.get('recovery_seconds')) is int and recovery['recovery_seconds']==1200 and
        recovery.get('map_proposal_sha256')==object_hash(maps) and
        recovery.get('runtime_recipe')==maps.get('runtime_recipe')==file_record(FRAME_RECIPE) and
        recovery.get('profile_inventory')==maps.get('profile_inventory')==file_record(VIDEO_FRAME_PROFILES),
        'exact one-attempt 1200-second frame-input recovery proposal required')
    grants=approved.get('candidate_approvals',[])
    _require(len(grants)==1 and grants[0].get('schema')=='plan069-depth-execution-approval/v1' and
        grants[0].get('candidate')=='D9' and grants[0].get('status')=='approved' and
        type(grants[0].get('max_attempts')) is int and grants[0]['max_attempts']==1 and
        grants[0].get('proposal_sha256')==object_hash(maps) and
        approved.get('setup_recovery_approval')==dict(candidate='D9',job_id='plan069-D9-setup-recovery-001',
            status='approved',max_attempts=1,proposal_sha256=object_hash(recovery)),
        'both exact fresh D9 map and setup-recovery approvals required')
    _require(selected_profile_inventory(maps)==VIDEO_FRAME_PROFILES,'exact frame-input runtime profile required')
    original=recovery['original_setup'];run_root=Path(original['request']['path']).parent.parent
    config=dict(load(),new_download_gib_limit=110,new_artifact_disk_gib_limit=210)
    lineage=original_setup_lineage(original,Ledger(run_root/'ledger.jsonl',config).events(),run_root)
    _require(lineage['grant']['sequence']==761 and lineage['finish']['sequence']==765,
        'exact preserved original D9 grant and failed finish required')
    restored=copy.deepcopy(maps)
    for key in ('profile','profile_inventory','runtime_recipe'):restored[key]=lineage['proposal'][key]
    _require(restored==lineage['proposal'],'recovery changes original science, assets, caps or workload')
    elapsed=lineage['finish'].get('elapsed_seconds')
    _require(type(elapsed) in (int,float) and math.isfinite(elapsed) and elapsed>=0 and
        elapsed+recovery['recovery_seconds']<=lineage['proposal']['allocation']['setup_seconds'],
        'recovery exceeds original remaining setup allowance')
    return lineage

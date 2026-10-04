"""Select the exact approved depth budget without reopening consumed attempts."""
from .config import ROOT
from .files import file_record, object_hash, read_json, verify_record


AMENDED = ('D5', 'D6', 'D8')
CANDIDATES = ('D2', 'D5', 'D6', 'D7', 'D8', 'D9', 'D10', 'D11')


def execution_authorization(candidate, *, root=ROOT, authorization_path=None):
    """Return verified review, authorization, proposal and one applicable grant."""
    if candidate not in CANDIDATES:
        raise ValueError('unknown approved depth candidate')
    version = '002' if candidate in AMENDED else '001'
    auth_path = root / ('docs/research/vipe-alternatives/plan031-execution/' +
                        f'depth-approval-{version}.json')
    if authorization_path is not None:
        if candidate not in ('D9', 'D10'):
            raise ValueError('explicit runtime authorization is video-only')
        from pathlib import Path
        auth_path = Path(authorization_path)
    authorization = file_record(auth_path)
    approved = read_json(auth_path)
    review = verify_record(approved['review'])
    reviewed = read_json(review['path'])
    if (approved.get('schema') != 'plan069-depth-user-authorization/v1' or
            approved.get('status') != 'DO' or
            reviewed.get('schema') != 'plan069-depth-execution-review/v1' or
            reviewed.get('status') != 'REVIEW'):
        raise ValueError('exact approved depth authorization required')
    if reviewed.get('setup_recovery_proposal') is not None or approved.get('setup_recovery_approval') is not None:
        from .depth_recovery_authorization import validate_recovery_authorization
        validate_recovery_authorization(candidate, approved, reviewed, root=root)
    elif authorization_path is not None and approved.get("video_frame_amendment") is not None:
        from .depth_video_frame_authorization import validate_frame_amendment
        validate_frame_amendment(candidate, approved, reviewed, root=root)
    elif authorization_path is not None:
        import copy
        from .depth_admission import VIDEO_PROFILES, VIDEO_PYPI_PROFILES, selected_profile_inventory
        from .video_environment import PYPI_RECIPE
        prior_record = verify_record(approved['previous_authorization'])
        local_prior = file_record(root / 'docs/research/vipe-alternatives/plan031-execution/depth-approval-001.json')
        if any(prior_record[key] != local_prior[key] for key in ('sha256', 'bytes')):
            raise ValueError('video runtime amendment requires immutable prior authorization')
        prior = read_json(prior_record['path'])
        baseline = read_json(verify_record(prior['review'])['path'])
        restored = copy.deepcopy(reviewed)
        original = {row['candidate']: row for row in baseline['proposals']}
        video_rows = [row for row in reviewed.get('proposals', []) if row.get('candidate') in ('D9', 'D10')]
        inventories = {selected_profile_inventory(row) for row in video_rows}
        if len(video_rows) != 2 or len(inventories) != 1:
            raise ValueError('explicit video runtime amendment requires its new profile for both candidates')
        pypi = inventories == {VIDEO_PYPI_PROFILES}
        if pypi:
            budget_path = ROOT / 'docs/research/vipe-alternatives/plan031-execution/video-pypi-budget-proposal-001/proposal.json'
            expected_amendment = dict(schema='plan069-video-distribution-budget-approval/v1', status='approved',
                distribution_approved=True, budget_approved=True, recipe=file_record(PYPI_RECIPE),
                budget_review=file_record(budget_path))
            if approved.get('video_amendment') != expected_amendment:
                raise ValueError('explicit PyPI distribution and exact budget approval required')
            changes = {row['candidate']: row for row in read_json(budget_path)['changes']}
            if any(row['allocation'] != changes[row['candidate']]['proposed'] for row in video_rows):
                raise ValueError('PyPI allocation differs from reviewed exact bounds')
        elif approved.get('video_amendment') is not None:
            raise ValueError('indexed runtime amendment cannot select PyPI budgets')
        for proposal in restored.get('proposals', []):
            if proposal.get('candidate') in ('D9', 'D10'):
                if selected_profile_inventory(proposal) not in (VIDEO_PROFILES, VIDEO_PYPI_PROFILES):
                    raise ValueError('explicit video runtime amendment requires its new profile')
                for key in ('profile', 'profile_inventory'):
                    proposal[key] = original[proposal['candidate']][key]
                proposal.pop('runtime_recipe', None)
                if pypi:
                    for key in ('download_bytes', 'artifact_bytes'):
                        proposal['allocation'][key] -= 4 * 2**30
        if (restored != baseline or approved.get('reset_previous_consumption') is not False or
                approved.get('cap_amendment') != prior.get('cap_amendment') or
                approved.get('cap_approval') != prior.get('cap_approval') or
                sorted(g.get('candidate') for g in approved.get('candidate_approvals', [])) != ['D10', 'D9']):
            raise ValueError('video runtime amendment differs from approved scope or lineage')
    if candidate in AMENDED:
        import copy
        prior_record = verify_record(approved['previous_authorization'])
        local_prior = file_record(root / 'docs/research/vipe-alternatives/plan031-execution/depth-approval-001.json')
        if any(prior_record[k] != local_prior[k] for k in ('sha256', 'bytes')):
            raise ValueError('budget-only amendment requires immutable prior authorization')
        prior = read_json(prior_record['path'])
        baseline = read_json(verify_record(prior['review'])['path'])
        restored = copy.deepcopy(reviewed)
        for proposal in restored.get('proposals', []):
            if proposal.get('candidate') in AMENDED:
                for key in ('download_bytes', 'artifact_bytes'):
                    proposal['allocation'][key] -= 4 * 2**30
        if (restored != baseline or approved.get('reset_previous_consumption') is not False or
                approved.get('cap_amendment') != prior.get('cap_amendment') or
                approved.get('cap_approval') != prior.get('cap_approval') or
                sorted(g.get('candidate') for g in approved.get('candidate_approvals', [])) != sorted(AMENDED)):
            raise ValueError('budget-only amendment differs from approved scope or lineage')
    proposals = [p for p in reviewed.get('proposals', []) if p.get('candidate') == candidate]
    grants = [g for g in approved.get('candidate_approvals', []) if g.get('candidate') == candidate]
    if (len(proposals) != 1 or len(grants) != 1 or
            proposals[0].get('max_attempts') != 1 or
            grants[0].get('schema') != 'plan069-depth-execution-approval/v1' or
            grants[0].get('status') != 'approved' or grants[0].get('max_attempts') != 1 or
            grants[0].get('proposal_sha256') != object_hash(proposals[0])):
        raise ValueError('exact one-attempt candidate grant required')
    return review, authorization, proposals[0], grants[0]

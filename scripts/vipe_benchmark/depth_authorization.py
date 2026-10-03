"""Select the exact approved depth budget without reopening consumed attempts."""
from .config import ROOT
from .files import file_record, object_hash, read_json, verify_record


AMENDED = ('D5', 'D6', 'D8')
CANDIDATES = ('D2', 'D5', 'D6', 'D7', 'D8', 'D9', 'D10', 'D11')


def execution_authorization(candidate, *, root=ROOT):
    """Return verified review, authorization, proposal and one applicable grant."""
    if candidate not in CANDIDATES:
        raise ValueError('unknown approved depth candidate')
    version = '002' if candidate in AMENDED else '001'
    auth_path = root / ('docs/research/vipe-alternatives/plan031-execution/' +
                        f'depth-approval-{version}.json')
    authorization = file_record(auth_path)
    approved = read_json(auth_path)
    review = verify_record(approved['review'])
    reviewed = read_json(review['path'])
    if (approved.get('schema') != 'plan069-depth-user-authorization/v1' or
            approved.get('status') != 'DO' or
            reviewed.get('schema') != 'plan069-depth-execution-review/v1' or
            reviewed.get('status') != 'REVIEW'):
        raise ValueError('exact approved depth authorization required')
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

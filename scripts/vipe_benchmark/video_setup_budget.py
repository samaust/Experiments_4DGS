"""Use the protected setup grant for independent video byte ceilings."""
from .files import object_hash


def setup_byte_limits(request, proposal, run_root, reading, config):
    """An actual request cannot supply or enlarge its setup-start baseline."""
    baseline = reading
    if request.get('record_kind') == 'actual':
        from .ledger import Ledger
        events = Ledger(run_root / 'ledger.jsonl', config).events()
        grants = [row for row in events if row.get('event') == 'depth_setup_authorized'
                  and row.get('candidate') == proposal['candidate']]
        if (len(grants) != 1 or grants[0].get('review') != request['review'] or
                grants[0].get('authorization') != request['authorization'] or
                grants[0].get('proposal_sha256') != object_hash(proposal)):
            raise ValueError('exact protected video setup byte baseline required')
        baseline = grants[0]['resource_snapshot']
    elif request.get('record_kind') != 'fixture':
        raise ValueError('exact video setup budget record kind required')
    limits = {}
    for key, setting in (('download_bytes', 'new_download_gib_limit'),
                         ('artifact_bytes', 'new_artifact_disk_gib_limit')):
        allowance = proposal['allocation'].get(key)
        if (type(allowance) is not int or allowance <= 0 or
                type(baseline.get(key)) is not int or baseline[key] < 0 or
                type(reading.get(key)) is not int or reading[key] < baseline[key]):
            raise ValueError('exact positive video setup byte allocation required')
        limits[key] = min(config[setting] * 2**30, baseline[key] + allowance)
        if reading[key] > limits[key]:
            raise ValueError('video setup byte allocation exhausted: ' + key)
    return limits

"""Per-candidate setup-recovery identities used by setup_recovery_core.

Each entry names the original setup job, ordered recovery jobs with their result
schemas, the maps job tolerated as active during lineage checks, and the DO field
that carries the explicit recovery approval.
"""
from typing import TypedDict


class RecoveryCandidate(TypedDict):
    original_job: str
    jobs: tuple[str, ...]
    result_schemas: dict[str, str]
    maps_job: str
    approval_field: str


RECOVERY_CANDIDATES: dict[str, RecoveryCandidate] = {
    'D9': RecoveryCandidate(
        original_job='plan069-D9-setup-001',
        jobs=('plan069-D9-setup-recovery-001', 'plan069-D9-setup-recovery-002'),
        result_schemas={'plan069-D9-setup-recovery-001': 'plan069-video-setup-recovery-result/v1',
                        'plan069-D9-setup-recovery-002': 'plan069-video-setup-recovery-result/v2'},
        maps_job='plan069-D9-maps-001',
        approval_field='setup_recovery_approval'),
}

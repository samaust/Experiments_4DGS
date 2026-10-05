"""Per-candidate setup-recovery identities used by setup_recovery_core.

Each entry names the original setup job, ordered recovery jobs with their result
schemas, the DO field that carries the explicit recovery approval, the candidate's
profile module (setup-specific validation) and recovery worker script, and
`legacy_lineage`: its accepted lineage and byte markers use the original
depth_recovery_lineage contract rather than the core.
The maps job tolerated as active during lineage checks comes from depth_map_retry.
"""
from typing import TypedDict


class RecoveryCandidate(TypedDict):
    original_job: str
    jobs: tuple[str, ...]
    result_schemas: dict[str, str]
    approval_field: str
    profile_module: str
    worker: str
    legacy_lineage: bool


# Recovery requests whose job no table entry owns are routed to this profile, whose
# validators refuse them.
UNKNOWN_JOB_PROFILE = 'D9'


RECOVERY_CANDIDATES: dict[str, RecoveryCandidate] = {
    'D9': RecoveryCandidate(
        original_job='plan069-D9-setup-001',
        jobs=('plan069-D9-setup-recovery-001', 'plan069-D9-setup-recovery-002'),
        result_schemas={'plan069-D9-setup-recovery-001': 'plan069-video-setup-recovery-result/v1',
                        'plan069-D9-setup-recovery-002': 'plan069-video-setup-recovery-result/v2'},
        approval_field='setup_recovery_approval',
        profile_module='depth_setup_recovery',
        worker='basketball_vipe_video_setup_recovery.py',
        legacy_lineage=True),
    'D8': RecoveryCandidate(
        original_job='plan069-D8-setup-001',
        jobs=('plan069-D8-setup-recovery-001',),
        result_schemas={'plan069-D8-setup-recovery-001': 'plan069-depth-setup-recovery-result/v1'},
        approval_field='setup_recovery_approval',
        profile_module='depth_native_setup_recovery',
        worker='basketball_vipe_depth_setup_recovery.py',
        legacy_lineage=False),
    # D6's original setup completed; this approved recovery only replaces its unusable runtime.
    'D6': RecoveryCandidate(
        original_job='plan069-D6-setup-001',
        jobs=('plan069-D6-setup-recovery-001',),
        result_schemas={'plan069-D6-setup-recovery-001': 'plan069-depth-setup-recovery-result/v1'},
        approval_field='setup_recovery_approval',
        profile_module='depth_moge_runtime_replacement',
        worker='basketball_vipe_moge_runtime_replacement.py',
        legacy_lineage=False),
}

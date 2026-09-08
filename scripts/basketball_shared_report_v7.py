"""Package a failed or interrupted v7 stage without fabricating success evidence."""
from basketball_scale import write

def empty_ledger(scheduled):
    return dict(scheduled=scheduled,executed=0,missing=scheduled,qualified=0)


def package(output,prior,predecessor,p):
    if prior['status']!='blocked':raise ValueError('terminal blocked predecessor required for blocker package')
    if prior['stage'] not in ['prepare','diagnose']:
        raise ValueError('this admission-blocker reporter cannot invent later-stage ledgers')
    decision=dict(status='unassessed',passed=None,reason='required diagnostic evidence unavailable',timing_qualification=False)
    write(output/'development-decisions.json',dict(conditioning={**decision,'local_attempts':empty_ledger(144)},
          scalar_basins={**decision,'conditional_initial':empty_ledger(7344),'refinement':dict(scheduled=None,executed=0,missing=None,qualified=0)},
          combined={**decision,'outer_searches':empty_ledger(144),'joint_solves':dict(scheduled=None,executed=0,missing=None,qualified=0)}))
    write(output/'search-ledgers.json',dict(conditioning=empty_ledger(144),scalar_initial=empty_ledger(7344),
          combined_outer=empty_ledger(144),refinement_scheduled=None,joint_scheduled=None,executed_conditional_fits=0,executed_joint_solves=0,executed_outer_searches=0,reason='stopped before any scientific fitting'))
    write(output/'resources.json',dict(runtime_projection=None,projection_status='unassessed',reason='admission evidence blocks benchmarks',gpu_seconds=0,scientific_solves=0,production_fits=0))
    return dict(status='blocked',terminal_kind=prior['terminal_kind'],blockers=prior['blockers'],blocked_stage=prior['stage'],scientific_solves=0,conditioning_decision='unassessed',basin_decision='unassessed',combined_decision='unassessed')

# Video setup slot byte guard

The D9/D10 worker and independent supervisor sampler now enforce both approved
byte allowances from the protected `depth_setup_authorized.resource_snapshot`.
Actual requests cannot provide their own baseline. Exact review, authorization
and proposal hash must match the grant. Each ceiling is the smaller of the
shared global cap and protected setup baseline plus the approved allowance.
No budget, attempt, global cap or previous consumption changes.

Both ceilings are passed into archive/checkpoint acquisition and environment
provisioning. Supervisor sampling separately rejects growth beyond the same
limits. Original v1/v2 and selected v3 continue using their exact allocation
values. Rejected worker budgets preserve an immutable failure receipt before
any acquisition. The new helper is included in D9/D10 source inventories.

Fifty CPU video fixtures passed; scoped mypy passed four changed modules.
Independent Spec and Standards reviews have no remaining actionable findings.
An initial supervisor fixture omitted its fake worker file; correcting that
fixture resolved the error. No production behavior was changed for that error.
A review finding about failure-receipt preservation was fixed and covered by a
separate rejection fixture.

Root must integrate this fix together with the independent causal whole-slot
accounting change, refresh canonical source receipts004 and run the affected
CPU qualification before actual setup. Existing source003 receipts bind the
previous executable sources. No setup, installation, network, model load, GPU
or shared ledger writes occurred during this implementation.

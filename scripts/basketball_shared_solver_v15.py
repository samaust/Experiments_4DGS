"""Coherent owned callback/ordinary/interrupted return path; optimizer is injected."""


def owned_report(adapter):
    return adapter.request('R',vg_hex=adapter.input['vg_hex'],vby_hex=adapter.input['vby_hex'])


def solve(adapter,optimizer,y):
    """Wire objective and exact derivatives without constructing or fitting inputs.

    Scientific Plan021 never invokes this function; readiness uses a mock only.
    The admitted returned state and multiplier bytes remain authoritative.
    """
    callbacks=[];error=None
    def check_multipliers(state):
        from basketball_shared_accounting_v15 import bytes_of
        if bytes_of(state.v[0]).hex()!=adapter.input['vg_hex'] or bytes_of(state.v[1]).hex()!=adapter.input['vby_hex']:raise ValueError('solver multiplier ownership')
    def callback(public_y,state):
        check_multipliers(state)
        adapter.ledger.iteration(int(state.nit))
        adapter.request('O',public=True,y=public_y)
        callbacks.append(owned_report(adapter))
    result=None
    try:
        result=optimizer(adapter.fun,y,jac=adapter.jac,hess=adapter.hess,callback=callback,constraint=adapter.constraint,constraint_hessian=adapter.constraint_hessian)
        check_multipliers(result)
        adapter.request('O',public=True,y=result.x)
    except (RuntimeError,ValueError,KeyboardInterrupt) as exc:error=type(exc).__name__+': '+str(exc)
    final=owned_report(adapter)
    return dict(report=final,callbacks=callbacks,error=error,interrupted=result is None,success=error is None,report_role='validated returned state' if error is None else 'last valid cached report')

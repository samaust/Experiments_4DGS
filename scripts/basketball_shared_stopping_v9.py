"""Explicit original-coordinate qualification; xtol never implies stationarity."""
import numpy as np
from basketball_shared_solver_v6 import POLICY


def options(adapter,disable_xtol=False):
    return {**POLICY,'gtol':adapter.gtol,'xtol':0. if disable_xtol else POLICY['xtol'],'maxiter':200}


def qualified(success,kkt,depth,boundary,finite=True):
    return bool(success and finite and kkt is not None and np.isfinite(kkt).all() and np.max(np.abs(kkt))<=1e-6 and np.min(depth)>1e-7 and not boundary)

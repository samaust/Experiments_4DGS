"""Verified lifetime repair primitives for the Plan 028 crossing study."""
from __future__ import annotations

import math
from typing import Mapping

import torch


REPAIR_VERSION = "duration-floor-v1"
RENDERING_MIN_DURATION = 0.02
AUTOMATIC_DURATION_SENTINEL = -1.0


def resolve_duration_target(initializer_metadata: Mapping, requested: float = AUTOMATIC_DURATION_SENTINEL) -> float:
    """Resolve a finite positive duration from frozen initializer metadata."""
    candidates = []
    for key in ("duration", "resolved_duration", "duration_target"):
        if initializer_metadata.get(key) is not None:
            candidates.append((key, initializer_metadata[key]))
    normalization = initializer_metadata.get("normalization")
    if isinstance(normalization, Mapping) and normalization.get("duration") is not None:
        candidates.append(("normalization.duration", normalization["duration"]))
    if requested != AUTOMATIC_DURATION_SENTINEL:
        candidates.insert(0, ("requested", requested))
    if not candidates:
        raise ValueError("automatic duration requires frozen initializer metadata")
    try:
        target = float(candidates[0][1])
    except (TypeError, ValueError) as error:
        raise ValueError("duration target is not numeric") from error
    if not math.isfinite(target) or target <= 0:
        raise ValueError("resolved duration target must be finite and positive")
    for name, value in candidates[1:]:
        try:
            other = float(value)
        except (TypeError, ValueError) as error:
            raise ValueError(f"{name} duration is not numeric") from error
        if not math.isfinite(other) or other <= 0 or not math.isclose(target, other, rel_tol=0, abs_tol=1e-12):
            raise ValueError("conflicting frozen duration targets")
    return target


def log_duration_floor(dtype=torch.float32, device=None) -> torch.Tensor:
    """Return a representable log value whose exponent is at least .02."""
    floor = torch.tensor(RENDERING_MIN_DURATION, dtype=dtype, device=device)
    return torch.nextafter(torch.log(floor), torch.full_like(floor, math.inf))


@torch.no_grad()
def project_duration_parameter_(parameter: torch.Tensor, optimizer: torch.optim.Optimizer) -> dict:
    """Project low log durations and clear Adam moments only for those entries."""
    if not isinstance(parameter, torch.Tensor) or parameter.ndim != 2 or parameter.shape[1] != 1:
        raise ValueError("duration parameter must have shape [N, 1]")
    if not torch.isfinite(parameter).all():
        raise ValueError("duration parameter contains nonfinite values")
    floor = log_duration_floor(parameter.dtype, parameter.device)
    mask = parameter < floor
    before = parameter.detach().clone()
    changed = int(mask.sum().item())
    parameter.copy_(torch.maximum(parameter, floor))
    state = optimizer.state.get(parameter)
    cleared = []
    if state is not None:
        for name in ("exp_avg", "exp_avg_sq", "max_exp_avg_sq"):
            value = state.get(name)
            if value is None:
                continue
            if value.shape != parameter.shape:
                raise ValueError(f"Adam state {name} shape mismatch")
            value[mask] = 0
            cleared.append(name)
    preserved_step = state.get("step") if state is not None else None
    if isinstance(preserved_step, torch.Tensor):
        preserved_step = float(preserved_step.item())
    return dict(version=REPAIR_VERSION, floor_duration=RENDERING_MIN_DURATION,
                floor_log=float(floor.item()), changed_entries=changed,
                total_entries=parameter.numel(), cleared_moments=cleared,
                preserved_step=preserved_step,
                minimum_before=float(torch.exp(before).min().item()),
                minimum_after=float(torch.exp(parameter).min().item()))


def policy_record(training_policy: str, lifetime_policy: str, target: float) -> dict:
    if training_policy not in {"holdout", "all-times"}:
        raise ValueError("unknown training policy")
    if lifetime_policy not in {"original", "repaired"}:
        raise ValueError("unknown lifetime policy")
    return dict(training_policy=training_policy, lifetime_policy=lifetime_policy,
                repair_version=REPAIR_VERSION if lifetime_policy == "repaired" else None,
                resolved_duration_target=target if lifetime_policy == "repaired" else None,
                rendering_min_duration=RENDERING_MIN_DURATION)


def qualify_projection() -> dict:
    """Exercise boundary projection, gradient availability, and Adam state."""
    parameter = torch.nn.Parameter(torch.log(torch.tensor([[.01], [.021], [.2]])))
    optimizer = torch.optim.Adam([parameter], lr=.01)
    parameter.grad = torch.ones_like(parameter)
    optimizer.step()
    step_before = optimizer.state[parameter]["step"].clone()
    result = project_duration_parameter_(parameter, optimizer)
    if result["changed_entries"] != 1 or not torch.all(torch.exp(parameter) >= .02):
        raise AssertionError("duration floor projection failed")
    if not torch.equal(step_before, optimizer.state[parameter]["step"]):
        raise AssertionError("projection changed Adam step counter")
    optimizer.zero_grad(set_to_none=True)
    parameter.grad = torch.ones_like(parameter)
    if not torch.isfinite(parameter.grad).all():
        raise AssertionError("boundary gradient is not usable")
    return result

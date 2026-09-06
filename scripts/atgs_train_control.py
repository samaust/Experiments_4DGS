"""Synchronous ATGS loop control, independent of scene loss/densification.

The caller owns the budget reservation and external process watchdog. Callbacks
execute synchronously; a failed callback propagates without saving partial work.
"""
import math

from atgs_loop_state import validate_loop


def run_training_segment(*, model, sampler, loop, max_iterations,
                         remaining_seconds, microstep, update, checkpoint,
                         checkpoint_interval=1000, checkpoint_reserve=60.,
                         step_reserve=5., force_update_due=None, after_microstep=None):
    """Run complete microsteps, preserving pending gradients at a deadline.

    microstep(model, key, iteration) performs forward/loss/backward and any
    per-view bookkeeping, returning (encoder_id, finite_loss). update(model,
    micro_steps, encoder_visits, counter) is the upstream accumulation step
    bound to resolved options. checkpoint(model, sampler, loop, reason) writes
    a new bundle synchronously. No DataLoader prefetch or implicit CUDA fallback.
    force_update_due(iteration) identifies upstream save/test/densification
    boundaries (not extra deadline snapshots). after_microstep(model, iteration,
    updated) runs after any update and sampler restart, for densification and
    buffer cleanup. The full schedule end always flushes pending accumulation.

    Reserves are caller-selected conservative estimates, not timing guarantees.
    A supervisor must enforce the actual hard limit, including checkpoint I/O.
    """
    encoders = len(sampler.buckets)
    validate_loop(loop, encoders)
    if type(max_iterations) is not int or max_iterations < loop['iteration']:
        raise ValueError('invalid full-schedule iteration limit')
    if type(checkpoint_interval) is not int or checkpoint_interval <= 0:
        raise ValueError('checkpoint interval must be positive')
    if any(not math.isfinite(value) or value <= 0 for value in (checkpoint_reserve, step_reserve)):
        raise ValueError('checkpoint and step reserves must be finite and positive')

    def remaining():
        value = remaining_seconds()
        if not math.isfinite(value) or value < 0:
            raise ValueError('invalid remaining budget')
        return value

    def save(reason):
        if remaining() <= 0:
            raise RuntimeError('deadline exhausted before checkpoint; retain previous committed bundle')
        validate_loop(loop, encoders)
        checkpoint(model, sampler, loop, reason)
        if remaining() <= 0:
            raise RuntimeError('deadline exhausted during checkpoint')

    while loop['iteration'] < max_iterations:
        # Reserve one complete microstep plus any resulting optimizer update.
        if remaining() <= checkpoint_reserve + step_reserve:
            save('deadline')
            return 'deadline'
        iteration = loop['iteration'] + 1
        key = next(sampler)
        encoder, loss = microstep(model, key, iteration)
        if type(encoder) is not int or not 0 <= encoder < encoders or not math.isfinite(loss):
            raise ValueError('invalid completed microstep result')
        loop['iteration'] = iteration
        loop['micro_steps'] += 1
        loop['encoder_visits'][encoder] = loop['encoder_visits'].get(encoder, 0) + 1
        loop['ema_loss'] = .4 * loss + .6 * loop['ema_loss']
        balanced = len(loop['encoder_visits']) == encoders
        special = iteration == max_iterations or (force_update_due is not None and force_update_due(iteration))
        updated = balanced or special
        if updated:
            counter = dict(count=loop['update_count'], iteration=iteration)
            update(model, loop['micro_steps'], dict(loop['encoder_visits']), counter)
            if counter['count'] != loop['update_count'] + 1:
                raise ValueError('optimizer update counter did not advance once')
            loop.update(micro_steps=0, encoder_visits={}, update_count=counter['count'],
                        last_update_iteration=iteration)
            if special and not balanced and iteration < max_iterations:
                sampler.restart_epoch()
        if after_microstep is not None:
            after_microstep(model, iteration, updated)
        # A final/deadline snapshot supersedes a coincident periodic snapshot.
        if iteration == max_iterations:
            break
        if remaining() <= checkpoint_reserve + step_reserve:
            save('deadline')
            return 'deadline'
        if iteration % checkpoint_interval == 0:
            save('periodic')
    save('completed')
    return 'completed'

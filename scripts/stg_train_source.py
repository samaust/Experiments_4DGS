"""Auditable hooks around the pinned upstream STG training loop.

Keep loss, batch-gradient accumulation, densification and EMS upstream-owned.
Fail closed if upstream train.py changes; save the adapted source with each run.
"""
import hashlib

TRAIN_SHA256 = '2e38ed71ff2e292983adde7d26a3dd0f62dbcf8c8db560b092c227032d1f9523'
LOOP_KEYS = ('flag', 'flagtwo', 'ema_loss_for_log', 'flagems', 'emscnt',
             'lossdiect', 'ssimdict', 'depthdict', 'validdepthdict',
             'emsstartfromiterations', 'selectedlength', 'lasterems',
             'selectviews', 'selectviewslist', 'maxbounds', 'minbounds')


def adapt_train(source):
    if hashlib.sha256(source.encode()).hexdigest() != TRAIN_SHA256:
        raise ValueError('upstream train.py hash differs; audit required')

    def replace(old, new):
        nonlocal source
        if source.count(old) != 1:
            raise ValueError('ambiguous upstream training hook: '+old)
        source = source.replace(old, new)

    replace('numchannel = 9', 'numchannel = 3 if dataset.model == "ours_lite" else 9')
    replace('cam.timestamp == i/duration', 'cam.source_frame == 4120+i')
    loop = '    for iteration in range(first_iter, opt.iterations + 1):'
    restore = ('    selectviews, selectviewslist = {}, []\n'
               '    first_iter, restored_loop = hooks.before_loop(gaussians, opt, locals())\n')
    restore += ''.join(f'    {key} = restored_loop.get({key!r}, {key})\n' for key in LOOP_KEYS)
    replace(loop, restore+loop)
    # Upstream skips the final optimizer update, leaving gradients uncleared.
    # Perform it to make every saved iteration a completed optimization step.
    replace('if iteration < opt.iterations:', 'if iteration <= opt.iterations:')
    marker = '\n\n\nif __name__ == "__main__":'
    replace(marker, '\n        if hooks.after_iteration(gaussians, opt, iteration, locals()):\n'
                    '            break\n'+marker)
    return source

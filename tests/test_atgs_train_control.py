import copy
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from atgs_train_control import run_training_segment
from test_atgs_loop_state import make


class TrainingControlTests(unittest.TestCase):
    def setUp(self):
        self.model, self.sampler, self.a, self.b = make()
        self.loop = dict(iteration=0, micro_steps=0, encoder_visits={}, update_count=0,
                         last_update_iteration=0, ema_loss=0.)
        self.time = 100.
        self.saved = []
        self.steps = []

    def microstep(self, model, key, iteration):
        self.time -= 10
        self.steps.append(iteration)
        (self.a + self.b).sum().backward()
        return key[1], .5

    def update(self, model, count, visits, counter):
        for optimizer in (model.optimizer, model.dy_optimizer):
            for group in optimizer.param_groups:
                for parameter in group['params']:
                    parameter.grad.div_(count)
            optimizer.step()
            optimizer.zero_grad(set_to_none=True)
        counter['count'] += 1

    def checkpoint(self, model, sampler, loop, reason):
        self.saved.append((reason, copy.deepcopy(loop), self.a.grad is None))

    def run_segment(self, **overrides):
        kwargs = dict(model=self.model, sampler=self.sampler, loop=self.loop,
                      max_iterations=4, remaining_seconds=lambda: self.time,
                      microstep=self.microstep, update=self.update, checkpoint=self.checkpoint,
                      checkpoint_interval=1, checkpoint_reserve=15., step_reserve=5.)
        kwargs.update(overrides)
        return run_training_segment(**kwargs)

    def test_balanced_updates_and_periodic_partial_snapshot(self):
        self.assertEqual(self.run_segment(), 'completed')
        self.assertEqual(self.steps, [1, 2, 3, 4])
        self.assertEqual(self.loop['update_count'], 2)
        self.assertEqual([s[0] for s in self.saved], ['periodic'] * 3 + ['completed'])
        self.assertEqual(self.saved[0][1]['micro_steps'], 1)
        self.assertFalse(self.saved[0][2])
        self.assertTrue(self.saved[-1][2])

    def test_deadline_keeps_unaveraged_gradients_and_resume_counters(self):
        self.time = 30.
        self.assertEqual(self.run_segment(), 'deadline')
        self.assertEqual(self.steps, [1])
        self.assertEqual(self.loop['micro_steps'], 1)
        self.assertEqual(self.loop['update_count'], 0)
        self.assertEqual(self.a.grad.item(), 1.)
        self.time = 100.
        self.assertEqual(self.run_segment(max_iterations=2), 'completed')
        self.assertEqual(self.steps, [1, 2])
        self.assertEqual(self.loop['update_count'], 1)

    def test_failed_microstep_never_checkpoints(self):
        def fail(*args):
            raise RuntimeError('synthetic loss failure')
        with self.assertRaisesRegex(RuntimeError, 'synthetic loss'):
            self.run_segment(microstep=fail)
        self.assertEqual(self.saved, [])
        self.assertEqual(self.loop['iteration'], 0)

    def test_exhausted_deadline_does_not_start_work(self):
        self.time = 0.
        with self.assertRaisesRegex(RuntimeError, 'exhausted before checkpoint'):
            self.run_segment()
        self.assertEqual(self.steps, [])
        self.assertEqual(self.saved, [])

    def test_checkpoint_overrun_is_reported(self):
        def slow(*args):
            self.time = 0.
        with self.assertRaisesRegex(RuntimeError, 'during checkpoint'):
            self.run_segment(checkpoint=slow)

    def test_schedule_end_flushes_partial_update(self):
        self.assertEqual(self.run_segment(max_iterations=1), 'completed')
        self.assertEqual(self.loop['update_count'], 1)
        self.assertEqual(self.loop['micro_steps'], 0)
        self.assertTrue(self.saved[-1][2])

    def test_special_boundary_restarts_before_post_update_callback(self):
        events = []
        def after(model, iteration, updated):
            events.append((iteration, updated, self.sampler.epoch, self.sampler.cursor))
        self.run_segment(max_iterations=3, force_update_due=lambda i: i == 1,
                         after_microstep=after)
        self.assertEqual(events[0], (1, True, 2, 0))
        self.assertEqual(events[1], (2, False, 2, 1))
        self.assertEqual(events[2], (3, True, 2, 2))
        self.assertEqual(self.loop['update_count'], 2)

    def test_failed_post_update_callback_never_checkpoints(self):
        def fail(*args):
            raise RuntimeError('synthetic densification failure')
        with self.assertRaisesRegex(RuntimeError, 'densification failure'):
            self.run_segment(after_microstep=fail)
        self.assertEqual(self.saved, [])

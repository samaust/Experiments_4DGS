"""Guarded matcher preparation through worker runtime boundaries; no CUDA."""
import tempfile
from pathlib import Path
import unittest

from vipe_benchmark.files import file_record, write_json


class MatcherPreparationTests(unittest.TestCase):
    def test_actual_geometry_refuses_an_injected_clock_before_model_access(self):
        from vipe_benchmark.final_render_geometry import run
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary)/'result'
            with self.assertRaisesRegex(ValueError,'clock'):
                run({'record_kind':'actual'},'arm',output,object(),
                    invocation_record={'path':'unused'},clock=lambda:0.)
            self.assertFalse(output.exists())

    def test_unapproved_checkpoint_rejected_without_publication(self):
        from vipe_benchmark.final_render_matcher import prepare_inventory, validate_inventory
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for name in ('interpreter','dependency'):
                (root/name).write_text(name)
            weights = root/'weights'; weights.mkdir()
            from vipe_benchmark.final_render_geometry import _matching_helpers
            _,_,pin,expected = _matching_helpers()
            for name in expected:
                (weights/name).write_text('not approved checkpoint bytes')
            with self.assertRaisesRegex(ValueError,'checkpoint hash'):
                prepare_inventory(checkout=root,weights=weights,environment_prefix=root,
                    interpreter=file_record(root/'interpreter'),dependencies=[file_record(root/'dependency')],
                    output=root/'inventory.json')
            self.assertFalse((root/'inventory.json').exists())

    def test_actual_worker_rejects_missing_invocation_before_output(self):
        from vipe_benchmark.final_render_geometry import run
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary)/'result'
            with self.assertRaisesRegex(ValueError,'invocation'):
                run({'record_kind':'actual'},'arm',output,object())
            self.assertFalse(output.exists())

    def test_injected_actual_matcher_rejected_before_model_or_output(self):
        from vipe_benchmark.final_render_geometry import run
        class FakeSDK:
            record_kind = 'actual'
            @property
            def sample_thresh(self):
                raise AssertionError('model must never load')
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary)/'result'
            with self.assertRaisesRegex(ValueError,'exact pinned native'):
                run({'record_kind':'actual'},'arm',output,FakeSDK(),
                    invocation_record={'path':'unused'})
            self.assertFalse(output.exists())

    def test_fixture_cannot_consume_actual_invocation(self):
        from vipe_benchmark.final_render_geometry import run
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary)/'result'
            with self.assertRaisesRegex(ValueError,'fixture geometry cannot'):
                run({'record_kind':'fixture'},'arm',output,object(),
                    invocation_record={'path':'unused'})
            self.assertFalse(output.exists())

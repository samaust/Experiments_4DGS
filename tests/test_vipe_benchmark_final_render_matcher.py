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


class OpenCVProviderTests(unittest.TestCase):
    def _validate(self, providers):
        from unittest.mock import patch
        from vipe_benchmark import final_render_matcher as matcher
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            interpreter = root/'python'; interpreter.write_text('fixture executable')
            weight = root/'weights'; weight.write_text('fixture checkpoint')
            dependencies = []
            names = (matcher.DEPENDENCIES-{'opencv-python'}) | set(providers)
            for name in sorted(names):
                folder = root/(name.replace('-','_')+'-1.0.dist-info'); folder.mkdir()
                metadata = folder/'METADATA'; metadata.write_text('Name: '+name+'\nVersion: 1.0\n')
                record = folder/'RECORD'
                record.write_text(str(metadata.relative_to(root))+',,\n'+str(record.relative_to(root))+',,\n')
                dependencies.extend((file_record(metadata),file_record(record)))
            inventory = dict(schema=matcher.SCHEMA,record_kind='actual',status='prepared',
                checkout=str(root),revision='fixture-revision',environment_prefix=str(root),
                interpreter=file_record(interpreter),weights={'weights':file_record(weight)},
                source_files=[],checkout_files=[],dependencies=dependencies)
            with patch.object(matcher,'_matching_helpers',return_value=(None,None,'fixture-revision',
                    {'weights':file_record(weight)['sha256']})), \
                    patch.object(matcher,'required_sources',return_value=[]), \
                    patch.object(matcher,'_checkout_files',return_value=[]):
                return matcher.validate_inventory(inventory)

    def test_headless_provider_supplies_complete_matcher_inventory(self):
        self.assertEqual(self._validate({'opencv-python-headless'})['status'],'prepared')

    def test_gui_provider_retains_existing_inventory_support(self):
        self.assertEqual(self._validate({'opencv-python'})['status'],'prepared')

    def test_two_providers_rejected_before_any_model_import(self):
        with self.assertRaisesRegex(ValueError,'exactly one OpenCV provider'):
            self._validate({'opencv-python','opencv-python-headless'})

    def test_missing_provider_rejected(self):
        with self.assertRaisesRegex(ValueError,'exactly one OpenCV provider'):
            self._validate(set())

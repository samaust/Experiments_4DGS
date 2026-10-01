import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from vipe_benchmark import d2_preflight
from vipe_benchmark.files import file_record, write_json


class D2PreflightTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / 'source'
        self.source.mkdir()
        license_path = self.source / 'LICENSE'
        license_path.write_text('Apache License Version 2.0')
        self.snapshot = self.root / 'snapshot'
        self.snapshot.mkdir()
        config = self.snapshot / 'config.json'
        config.write_text('{}')
        weights = self.snapshot / 'model.safetensors'
        weights.write_bytes(b'pinned fixture weight')
        source_record = dict(path=str(self.source), revision=d2_preflight.D2_SPEC['code']['revision'],
                             files=[file_record(license_path)])
        snapshot_record = dict(path=str(self.snapshot), revision=d2_preflight.D2_SPEC['weights']['revision'],
                               files=[file_record(config), file_record(weights)])
        assets = self.root / 'assets.json'
        write_json(assets, dict(da3_source=source_record, da3_snapshot=snapshot_record))
        self.inventory = self.root / 'inventory.json'
        write_json(self.inventory, dict(candidates=dict(D2=dict(files=[
            dict(repository='da3', path='model.safetensors',
                 bytes=weights.stat().st_size, lfs_sha256=file_record(weights)['sha256'])]))))
        self.profiles = self.root / 'profiles.json'
        write_json(self.profiles, dict(profiles=dict(D2={})))
        self.e5 = self.root / 'E5-setup-recovery-004'
        self.e5.mkdir()
        interpreter = self.e5 / 'environment/bin/python'
        interpreter.parent.mkdir(parents=True)
        interpreter.write_bytes(b'fixture interpreter')
        runtime = dict(python=str(interpreter), versions=dict(python='3.11'))
        for key in ('inventory', 'imports', 'dependency_lock', 'build_inputs'):
            path = self.e5 / (key + '.json')
            payload = (dict(inventory_only=True, model_imports=False, gpu_operations=False,
                            executable=str(interpreter), versions=runtime['versions'],
                            packages=[dict(name='fixture', version='1',
                                           files=[file_record(interpreter)])])
                       if key == 'inventory' else dict(status='complete'))
            write_json(path, payload)
            runtime[key] = file_record(path)
        result = self.e5 / 'result.json'
        write_json(result, dict(status='complete', environment='E5',
                                assets=file_record(assets), runtime=runtime))
        self.e5_record = file_record(result)
        self.proposal = dict(schema='plan069-depth-execution-proposal/v1', status='REVIEW',
            candidate='D2', candidate_config=d2_preflight.D2_SPEC,
            required_assets=file_record(self.inventory),
            profile_inventory=file_record(self.profiles), max_attempts=1)

    def test_qualifies_exact_reusable_runtime_without_gpu(self):
        with patch.object(d2_preflight, 'INVENTORY', self.inventory), \
             patch.object(d2_preflight, 'PROFILES', self.profiles):
            result = d2_preflight.qualify(self.proposal, self.e5_record, self.root / 'out')
        self.assertEqual(result['status'], 'cpu_preflight_passed')
        self.assertEqual(result['checkpoint']['sha256'],
                         json.loads(self.inventory.read_text())['candidates']['D2']['files'][0]['lfs_sha256'])
        self.assertIn('GPU runtime smoke', result['remaining_gates'])

    def test_rejects_changed_required_checkpoint(self):
        self.proposal['required_assets'] = dict(self.proposal['required_assets'], sha256='0' * 64)
        with patch.object(d2_preflight, 'INVENTORY', self.inventory), \
             patch.object(d2_preflight, 'PROFILES', self.profiles):
            with self.assertRaisesRegex(ValueError, 'changed file'):
                d2_preflight.qualify(self.proposal, self.e5_record, self.root / 'out')
        self.assertFalse((self.root / 'out').exists())


if __name__ == '__main__':
    unittest.main()

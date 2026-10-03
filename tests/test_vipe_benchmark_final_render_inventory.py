"""CPU preparation through the native worker's immutable inventory boundary."""
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import sys

from vipe_benchmark.files import file_record, read_json, write_json


class InventoryTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.checkout = self.root/'checkout'
        self.environment = self.root/'env'
        self.interpreter = self.record('env/bin/python3', b'fixture-interpreter')
        self.record('checkout/src/simple_trainer_freetime_4d_pure_relocation.py', b'fixture-preset')
        self.record('checkout/src/utils.py', b'fixture-utils')
        self.binaries = {name:self.record('env/lib/'+name+'.so', name.encode())
            for name in ('gsplat','fused_ssim')}
        self.checkpoint = self.record('hub/checkpoints/alexnet-owt-7be5be79.pth', b'fixture-checkpoint')
        self.config = self.root/'resolved-config.json'
        write_json(self.config, dict(native={'start_frame':0,'end_frame':50},
            normalization={"transform":[[1,0,0,0],[0,1,0,0],[0,0,1,0],[0,0,0,1]]},scene_scale=1.))
        self.dependencies = {}
        for name in ('torch','numpy','scipy','Pillow','torchvision','torchmetrics','gsplat','fused-ssim'):
            directory = name.replace('-','_')+'-fixture1.dist-info'
            self.dependencies[name] = dict(version='fixture-1',
                metadata=self.record('env/lib/'+directory+'/METADATA',
                    ('Name: '+name+'\nVersion: fixture-1\n').encode()),
                record=self.record('env/lib/'+directory+'/RECORD',
                    (directory+'/METADATA,,\n'+directory+'/RECORD,,\n').encode()))

    def record(self, path, content):
        target = self.root/path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
        return file_record(target)

    def prepare(self, **changes):
        from vipe_benchmark.final_render_inventory import prepare_inventory
        arguments = dict(checkout=self.checkout, environment_prefix=self.environment,
            interpreter=self.interpreter, binaries=self.binaries,
            dependencies=self.dependencies, resolved_config=file_record(self.config),
            lpips_checkpoint=self.checkpoint, output=self.root/'runtime.json')
        arguments.update(changes)
        return prepare_inventory(**arguments)

    def test_prepares_exact_immutable_inventory_without_runtime_authority(self):
        inventory = self.prepare()
        self.assertEqual(inventory['schema'], 'plan069-final-render-native-runtime/v1')
        self.assertEqual(inventory['status'], 'prepared')
        self.assertEqual(inventory['dependencies']['torch']['version'], 'fixture-1')
        self.assertEqual(inventory, read_json(self.root/'runtime.json'))
        self.assertNotIn('execution_authorized', inventory)
        with self.assertRaises(FileExistsError):
            self.prepare()

    def test_changed_dependency_payload_is_rejected_before_publication(self):
        # Dependency metadata is part of the runtime identity, even when its
        # package version text is unchanged.
        target = Path(self.dependencies['torch']['record']['path'])
        target.write_bytes(b'changed-installed-files')
        with self.assertRaises(ValueError):
            self.prepare()
        self.assertFalse((self.root/'runtime.json').exists())

    def test_validation_rejects_configuration_from_another_scene(self):
        from vipe_benchmark.final_render_inventory import validate_inventory
        inventory = self.prepare()
        with self.assertRaisesRegex(ValueError, 'normalization'):
            validate_inventory(inventory, checkout=self.checkout,
                normalization={"transform":[[2,0,0,0],[0,2,0,0],[0,0,2,0],[0,0,0,1]]})
        with self.assertRaisesRegex(ValueError, 'scene scale'):
            validate_inventory(inventory, checkout=self.checkout, scene_scale=2.)

    def test_missing_dependencies_and_binaries_outside_environment_fail_closed(self):
        dependencies = dict(self.dependencies)
        del dependencies['torchmetrics']
        with self.assertRaisesRegex(ValueError, 'dependency'):
            self.prepare(dependencies=dependencies)
        binaries = dict(self.binaries)
        binaries['gsplat'] = self.record('other-env/gsplat.so', b'foreign-binary')
        with self.assertRaisesRegex(ValueError, 'outside exact environment'):
            self.prepare(binaries=binaries)

    def test_inventory_rechecks_source_bytes_and_exact_size(self):
        from vipe_benchmark.final_render_inventory import validate_inventory
        inventory = self.prepare()
        inventory['interpreter']['bytes'] += 1
        with self.assertRaisesRegex(ValueError, 'changed or malformed'):
            validate_inventory(inventory, checkout=self.checkout)

    def test_preparation_rejects_invalid_normalization(self):
        write_json(self.root/'bad-config.json', dict(native={'start_frame':0,'end_frame':50},
            normalization={"transform":[[1]]},scene_scale=1.))
        with self.assertRaisesRegex(ValueError, 'normalization'):
            self.prepare(resolved_config=file_record(self.root/'bad-config.json'))

    def test_active_distribution_must_match_the_prepared_environment(self):
        from vipe_benchmark.final_render_inventory import validate_inventory
        inventory = self.prepare()
        with patch.object(sys, 'path', [str(self.environment/'lib'),*sys.path]):
            self.assertEqual(validate_inventory(inventory, checkout=self.checkout,
                installed_dependencies=True), inventory)
        foreign = self.root/'foreign'
        target = foreign/'torch-fixture1.dist-info/METADATA'
        target.parent.mkdir(parents=True)
        target.write_text('Name: torch\nVersion: fixture-1\n')
        (target.parent/'RECORD').write_text('torch-fixture1.dist-info/METADATA,,\ntorch-fixture1.dist-info/RECORD,,\n')
        with patch.object(sys, 'path', [str(foreign),str(self.environment/'lib'),*sys.path]):
            with self.assertRaisesRegex(ValueError, 'active native dependency differs: torch'):
                validate_inventory(inventory, checkout=self.checkout, installed_dependencies=True)

    def test_preparation_and_validation_do_not_import_gpu_libraries(self):
        import subprocess
        program = """
import builtins
original = builtins.__import__
def cpu_only(name, *args, **kwargs):
    if name.split('.')[0] in {'torch','torchvision','gsplat','fused_ssim','fused_ssim_cuda'}:
        raise AssertionError('GPU library imported: '+name)
    return original(name, *args, **kwargs)
builtins.__import__ = cpu_only
from test_vipe_benchmark_final_render_inventory import InventoryTests
case = InventoryTests('test_prepares_exact_immutable_inventory_without_runtime_authority')
case.setUp()
try:
    case.test_prepares_exact_immutable_inventory_without_runtime_authority()
finally:
    case.doCleanups()
"""
        result = subprocess.run([sys.executable,'-c',program],capture_output=True,text=True)
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == '__main__':
    unittest.main()

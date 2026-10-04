"""Native frame input excludes optional CLI decoder without weakening checks."""
import copy
import sys
import unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from vipe_benchmark import video_environment as environment
from vipe_benchmark.video_native import installed_dependency_versions
from vipe_benchmark.depth_admission import VIDEO_FRAME_PROFILES, selected_profile_inventory
from vipe_benchmark.files import file_record, read_json


class FrameRecipeTests(unittest.TestCase):
    def test_only_optional_decoder_changes_dependency_closure(self):
        old=read_json(environment.PYPI_RECIPE); new=read_json(environment.FRAME_RECIPE)
        self.assertEqual(new['upstream_requirements'],old['upstream_requirements'])
        self.assertEqual(new['constraints'],[pin for pin in old['constraints'] if pin!='decord==0.6.0'])
        self.assertEqual(new['requirements'],[pin for pin in old['requirements'] if pin!='decord'])
        self.assertEqual(len(new['constraints']),48)
        self.assertEqual(new['runtime_observation'],old['runtime_observation'])
    def test_absence_must_be_recorded_and_enforced(self):
        recipe=read_json(environment.FRAME_RECIPE)
        env=dict(recipe=file_record(environment.FRAME_RECIPE),runtime_profile=recipe['runtime_profile'])
        versions=dict(pin.split('==') for pin in recipe['constraints']); versions.update(decord=None,xformers=None)
        environment.validate_runtime_versions(env,versions)
        for bad in ('0.6.0','unobserved'):
            changed=dict(versions,decord=bad)
            if bad=='unobserved':del changed['decord']
            with self.assertRaisesRegex(ValueError,'excluded video'):
                environment.validate_runtime_versions(env,changed)
    def test_inventory_captures_absent_or_present_decoder(self):
        import importlib.metadata
        pins=dict(pin.split('==') for pin in read_json(environment.FRAME_RECIPE)['constraints'])
        def version(name):
            if name in pins:return pins[name]
            raise importlib.metadata.PackageNotFoundError(name)
        setup=dict(runtime_recipe=file_record(environment.FRAME_RECIPE))
        with patch('vipe_benchmark.video_native.importlib.metadata.version',side_effect=version):
            result=installed_dependency_versions(setup)
        self.assertEqual(result,dict(pins,decord=None,xformers=None))
        with patch('vipe_benchmark.video_native.importlib.metadata.version',side_effect=lambda name:'0.6.0' if name=='decord' else version(name)):
            self.assertEqual(installed_dependency_versions(setup)['decord'],'0.6.0')
    def test_only_video_scientific_profiles_are_preserved(self):
        profile=read_json(VIDEO_FRAME_PROFILES)['profiles']['D9']
        proposal=dict(candidate='D9',profile=profile,profile_inventory=file_record(VIDEO_FRAME_PROFILES),runtime_recipe=file_record(environment.FRAME_RECIPE))
        self.assertEqual(selected_profile_inventory(proposal),VIDEO_FRAME_PROFILES)
        changed=copy.deepcopy(proposal); changed['profile']['precision']='changed'
        with self.assertRaisesRegex(ValueError,'scientific'):
            selected_profile_inventory(changed)
        with self.assertRaisesRegex(ValueError,'exact video'):
            selected_profile_inventory(dict(proposal,candidate='D6'))
    def test_actual_module_observation_remains_required(self):
        recipe=read_json(environment.FRAME_RECIPE)
        env=dict(recipe=file_record(environment.FRAME_RECIPE),runtime_profile=recipe['runtime_profile'])
        with self.assertRaisesRegex(ValueError,'actual PyPI'):
            environment.validate_runtime_observation(env,None)
    def test_native_adapter_smoke_uses_frame_model_and_math_utility_only(self):
        import tempfile
        from types import SimpleNamespace
        from unittest.mock import Mock
        from vipe_benchmark.video_native import load_native_video
        from vipe_benchmark.files import write_json
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); source=root/'source'; source.mkdir()
            checkpoint=root/'weights.pth';checkpoint.write_bytes(b'fixture only')
            recipe=read_json(environment.FRAME_RECIPE)
            setup=dict(schema='plan069-video-setup-result/v1',status='complete',candidate='D9',record_kind='actual',
                source_dir=str(source),source_files=[],checkpoint=file_record(checkpoint),
                runtime_recipe=file_record(environment.FRAME_RECIPE),runtime_profile=recipe['runtime_profile'])
            path=root/'result.json';write_json(path,setup)
            model=Mock();model.to.return_value=model;model.eval.return_value=model
            native=SimpleNamespace(__file__=str(source/'video_depth_anything/video_depth.py'),VideoDepthAnything=Mock(return_value=model))
            util=SimpleNamespace(__file__=str(source/'utils/util.py'))
            versions=dict(pin.split('==') for pin in recipe['constraints']);versions.update(decord=None,xformers=None)
            modules={'torch':SimpleNamespace(load=Mock(return_value={'fixture':'state'}))}
            original_path=list(sys.path)
            try:
                with patch.dict(sys.modules,modules), patch('vipe_benchmark.video_native.setup_environment'), \
                        patch('vipe_benchmark.video_native.native_source_records',return_value=[]), \
                        patch('vipe_benchmark.video_native.installed_dependency_versions',return_value=versions), \
                        patch('vipe_benchmark.video_environment.observe_runtime'), \
                        patch('vipe_benchmark.video_native.importlib.import_module',side_effect=[native,util]) as imported:
                    self.assertIs(load_native_video('D9',file_record(path),device='cpu'),model)
                self.assertEqual([call.args[0] for call in imported.call_args_list],['video_depth_anything.video_depth','utils.util'])
                model.load_state_dict.assert_called_once_with({'fixture':'state'},strict=True)
            finally:
                sys.path[:]=original_path

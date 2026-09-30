"""Qualitative package publication seam; synthetic media are engineering fixtures."""
import copy
from pathlib import Path
import sys
import tempfile
import unittest
from PIL import Image
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from vipe_benchmark.files import file_record
from vipe_benchmark.qualitative_package import validate, publish

class PackageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        evidence = self.root / 'evidence.json'
        evidence.write_text('{}')
        image = self.root / 'frame.png'
        Image.new('RGB', (16, 12)).save(image)
        record = file_record(evidence)
        self.manifest = dict(schema='plan067-qualitative-package/v1', id='fixture', mode='qualitative', record_kind='fixture',
            bindings={name: record for name in ('source','config','inputs','amendment')},
            settings=dict(fps=25, resolution=[16,12], color_handling='sRGB', crop=[0,0,16,12], detail_regions=[]),
            selections=[dict(id='frame150',kind='frame',role='selection',camera_id='0',frame_ids=[150],timestamps=[6.0])],
            candidates=[dict(id=name,label=name,is_control=name=='control',stage='fixture',output_type='component',status='available',reason='',
                provenance={key:record for key in ('source_result','ledger_outcome','configuration')},
                media=[dict(selection_id='frame150',kind='frame',record=file_record(image),frame_ids=[150],timestamps=[6.0],resolution=[16,12])]) for name in ('control','candidate')])
    def tearDown(self):
        self.temp.cleanup()
    def test_publish_matched_frames_and_read_only_viewer_once(self):
        result = publish(self.manifest, self.root / 'package')
        self.assertEqual(result['readiness'], 'ready-for-human-review')
        html = Path(result['viewer']['path']).read_text()
        self.assertIn('Original full frame', html)
        self.assertIn('Shared zoom', html)
        self.assertIn('Add current frame/time', html)
        with self.assertRaises(FileExistsError):
            publish(self.manifest, self.root / 'package')
    def test_matched_hash_metadata_corruption_and_role_substitution_rejected(self):
        for mutate in (
            lambda m: m['candidates'][1]['media'][0].update(timestamps=[6.04]),
            lambda m: m['candidates'][1]['media'][0].update(resolution=[12,16]),
            lambda m: m['bindings']['source'].update(bytes=999),
            lambda m: m['selections'][0].update(role='reconstruction'),
            lambda m: m['candidates'][1].update(status='failed',reason='crash'),
        ):
            changed=copy.deepcopy(self.manifest); mutate(changed)
            with self.assertRaises(ValueError):
                validate(changed)
        Path(self.manifest['candidates'][0]['media'][0]['record']['path']).write_bytes(b'not a PNG')
        for c in self.manifest['candidates']:
            c['media'][0]['record']=file_record(self.root/'frame.png')
        with self.assertRaises(OSError):
            validate(self.manifest)
    def test_missing_control_or_mismatched_selection_is_readiness_inventory(self):
        candidate=self.manifest['candidates'][1]
        candidate.update(status='missing',reason='No completed result',media=[])
        self.assertEqual(validate(self.manifest)['readiness'],'readiness-inventory')
        candidate['reason']=''
        with self.assertRaises(ValueError): validate(self.manifest)
    def test_stage_and_output_type_are_required_and_diagnostics_are_not_comparisons(self):
        self.manifest['candidates'][0]['output_type']='invented'
        with self.assertRaises(ValueError): validate(self.manifest)
    def test_continuous_video_decodes_and_wrong_frame_count_sparse_clip_refused(self):
        import subprocess
        path=self.root/'clip.mp4'
        subprocess.run(['ffmpeg','-v','error','-f','lavfi','-i','color=c=red:s=16x12:r=25',
            '-frames:v','3','-c:v','libx264','-pix_fmt','yuv420p',str(path)],check=True)
        selection=dict(id='clip150',kind='clip',role='selection',camera_id='0',frame_ids=[150,151,152],timestamps=[6.,6.04,6.08])
        self.manifest['selections']=[selection]
        for c in self.manifest['candidates']:
            c['media']=[dict(selection_id='clip150',kind='clip',record=file_record(path),frame_ids=[150,151,152],timestamps=[6.,6.04,6.08],resolution=[16,12])]
        self.assertEqual(validate(self.manifest)['readiness'],'ready-for-human-review')
        selection.update(frame_ids=[150,152,154],timestamps=[6.,6.08,6.16])
        for c in self.manifest['candidates']:
            c['media'][0].update(frame_ids=[150,152,154],timestamps=[6.,6.08,6.16])
        with self.assertRaisesRegex(ValueError,'sparse'): validate(self.manifest)
        for c in self.manifest['candidates']: c['media'][0]['kind']='sequence'
        self.assertEqual(validate(self.manifest)['readiness'],'ready-for-human-review')
        selection.update(frame_ids=[150,152],timestamps=[6.,6.08])
        for c in self.manifest['candidates']: c['media'][0].update(frame_ids=[150,152],timestamps=[6.,6.08])
        with self.assertRaisesRegex(ValueError,'frame count'): validate(self.manifest)
    def test_crop_bounds_duplicate_candidates_and_changed_artifact_rejected(self):
        changed=copy.deepcopy(self.manifest)
        changed['settings']['crop']=[2,0,16,12]
        with self.assertRaisesRegex(ValueError,'crop'): validate(changed)
        changed=copy.deepcopy(self.manifest)
        changed['candidates'][1]['id']='control'
        with self.assertRaisesRegex(ValueError,'candidate'): validate(changed)
        with (self.root/'frame.png').open('ab') as stream: stream.write(b'changed')
        with self.assertRaisesRegex(ValueError,'changed file'): validate(self.manifest)

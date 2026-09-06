import copy
import json
from pathlib import Path
import runpy
import sys
import tempfile
import unittest
from unittest.mock import patch

compare = runpy.run_path(str(Path(__file__).resolve().parents[1] / 'scripts/evaluate-atgs-checkpoint.py'))['compare_reports']


class EvaluationTests(unittest.TestCase):
    def test_exact_reports_and_rejection_of_changed_runtime_or_pixels(self):
        report = dict(bundle={}, runtime={}, renderer_sha256='code', manifest_sha256='manifest',
                      iteration=1000, model='atgs', sweep={}, frames=[{'frame_id': i} for i in range(60)],
                      sweep_frames=[{'index': i} for i in range(20)])
        self.assertTrue(compare(report, copy.deepcopy(report))['float_exact'])
        changed = copy.deepcopy(report)
        changed['runtime'] = {'modified': True}
        with self.assertRaisesRegex(ValueError, 'runtime'):
            compare(report, changed)
        changed = copy.deepcopy(report)
        changed['frames'][0]['float_sha256'] = 'modified'
        with self.assertRaisesRegex(ValueError, 'hashes differ'):
            compare(report, changed)
        changed = copy.deepcopy(report)
        changed['sweep_frames'].pop()
        with self.assertRaisesRegex(ValueError, 'incomplete'):
            compare(report, changed)

    def test_failed_launch_records_command_and_keeps_virtualenv_path(self):
        entry = runpy.run_path(str(Path(__file__).resolve().parents[1] / 'scripts/evaluate-atgs-checkpoint.py'))
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest = root / 'manifest.json'
            manifest.write_text(json.dumps({'cameras': [dict(id='0015', split='test',
                frames=[dict(path=f'images/{i}.png') for i in range(60)])]}))
            cache = root / 'cache/hub/checkpoints'
            cache.mkdir(parents=True)
            (cache / 'alexnet-owt-7be5be79.pth').write_bytes(b'fixture')
            base = root / 'base-python'
            base.write_bytes(b'fixture')
            interpreter = root / 'env-python'
            interpreter.symlink_to(base)
            output = root / 'evaluation'
            argv = ['evaluate-atgs-checkpoint.py', '--atgs-python', str(interpreter),
                    '--manifest', str(manifest), '--checkpoint', str(root / 'checkpoint'),
                    '--training-config', str(root / 'config.json'), '--provenance', str(root / 'provenance.json'),
                    '--crops', str(root / 'crops.json'), '--torch-cache', str(root / 'cache'), '--output', str(output)]
            with patch.object(sys, 'argv', argv), patch('subprocess.run', side_effect=OSError('synthetic launch failure')) as run:
                with self.assertRaisesRegex(OSError, 'synthetic launch'):
                    entry['main']()
                self.assertEqual(run.call_args.args[0][0], str(interpreter))
            stages = json.loads((output / 'commands.json').read_text())
            self.assertEqual(stages[0]['status'], 'launch-error')
            self.assertFalse((output / 'evaluation.json').exists())

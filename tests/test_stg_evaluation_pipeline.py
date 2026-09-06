import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch


class EvaluationPipelineTests(unittest.TestCase):
    def setUp(self):
        spec = importlib.util.spec_from_file_location('stg_evaluation',
            Path(__file__).resolve().parents[1]/'scripts/evaluate-stg-checkpoint.py')
        self.module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.module)
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.manifest = self.root/'manifest.json'
        self.manifest.write_text(json.dumps({'cameras': [dict(id='0015', split='test',
            frames=[{'path': f'images/0015/{i:06d}.png'} for i in range(60)])]}))
        self.cache = self.root/'cache'
        self.weights = self.cache/'hub/checkpoints/alexnet-owt-7be5be79.pth'
        self.weights.parent.mkdir(parents=True)
        self.weights.touch()
        self.output = self.root/'output'
        self.argv = ['evaluate', '--checkout', str(self.root/'checkout'),
            '--manifest', str(self.manifest), '--checkpoint', str(self.root/'checkpoint.pt'),
            '--crops', str(self.root/'crops.json'), '--torch-cache', str(self.cache),
            '--output', str(self.output)]

    def test_subprocess_failure_stops_pipeline_and_records_command(self):
        with patch.object(self.module.sys, 'argv', self.argv), \
             patch.object(self.module.subprocess, 'run',
                 return_value=subprocess.CompletedProcess([], 7)) as run:
            with self.assertRaises(SystemExit) as error:
                self.module.main()
        self.assertEqual(error.exception.code, 7)
        self.assertEqual(run.call_count, 1)
        commands = json.loads((self.output/'commands.json').read_text())
        self.assertEqual(len(commands), 1)
        self.assertIn('offline-python.py', commands[0]['command'][1])
        self.assertEqual(run.call_args.kwargs['env']['OMP_NUM_THREADS'], '2')
        self.assertFalse((self.output/'evaluation.json').exists())

    def test_missing_cache_rejected_before_output_or_subprocess(self):
        self.weights.unlink()
        with patch.object(self.module.sys, 'argv', self.argv), \
             patch.object(self.module.subprocess, 'run') as run:
            with self.assertRaises(SystemExit):
                self.module.main()
        run.assert_not_called()
        self.assertFalse(self.output.exists())

    def test_existing_output_is_preserved(self):
        self.output.mkdir()
        marker = self.output/'keep.txt'
        marker.write_text('user data')
        with patch.object(self.module.sys, 'argv', self.argv), \
             patch.object(self.module.subprocess, 'run') as run:
            with self.assertRaises(SystemExit):
                self.module.main()
        run.assert_not_called()
        self.assertEqual(marker.read_text(), 'user data')

"""Metric sanity checks; run with the stg-render interpreter."""
import importlib.util
from pathlib import Path
import unittest


class EvaluatorTests(unittest.TestCase):
    def test_cli_identity_and_perturbation(self):
        try:
            import numpy as np
            from PIL import Image
            import skimage
        except ImportError:
            self.skipTest('requires the research environment')
        import json
        import subprocess
        import sys
        import tempfile
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name in ['reference', 'prediction']:
                (root/name).mkdir()
            source = np.random.default_rng(7).integers(0, 256, (64, 64, 3), dtype=np.uint8)
            Image.fromarray(source).save(root/'reference/frame.png')
            for name, pixels in [('identity', source), ('perturbed', source//2)]:
                Image.fromarray(pixels).save(root/'prediction/frame.png')
                subprocess.run([sys.executable, 'scripts/evaluate-reconstruction.py',
                                '--predictions', str(root/'prediction'),
                                '--ground-truth', str(root/'reference'),
                                '--output', str(root/(name+'.json'))], check=True,
                               cwd=Path(__file__).resolve().parents[1], capture_output=True)
            identity = json.loads((root/'identity.json').read_text())['aggregate']
            perturbed = json.loads((root/'perturbed.json').read_text())['aggregate']
            self.assertEqual(identity, {'psnr': 'Infinity', 'ssim': 1.0})
            self.assertTrue(0 < perturbed['psnr'] < 20)
            self.assertLess(perturbed['ssim'], 0.9)

    def test_identical_and_perturbed_ssim(self):
        try:
            import numpy as np
            import skimage
        except ImportError:
            self.skipTest('requires the research environment')
        spec = importlib.util.spec_from_file_location(
            'evaluator', Path(__file__).resolve().parents[1] / 'scripts/evaluate-reconstruction.py')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        reference = np.random.default_rng(0).random((32, 32, 3)).astype(np.float32)
        self.assertAlmostEqual(module.ssim(reference, reference), 1.0)
        self.assertLess(module.ssim(reference, reference * 0.5), 0.9)

    def test_full_decoder_error_precedes_cuda_import(self):
        import subprocess
        import sys
        result = subprocess.run([
            sys.executable, 'scripts/render-stg-preview.py', '--model', 'full',
            '--rgb-function', 'sandwich', '--checkout', '/missing', '--ply', '/missing/model.ply',
            '--cameras', '/missing/cameras.json', '--output', '/missing/output'],
            cwd=Path(__file__).resolve().parents[1], capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('missing full STG decoder', result.stderr)

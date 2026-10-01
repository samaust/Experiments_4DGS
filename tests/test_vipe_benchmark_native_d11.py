"""D11 processes a folder in one native call and binds frames to predictions."""

from pathlib import Path
import sys
import tempfile
import unittest

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from vipe_benchmark.files import file_record
from vipe_benchmark.marigold_relative import MarigoldLogStage2Adapter, SOURCE_REVISION
from vipe_benchmark.native_d11 import CachedD11Runtime, run_folder


class NativeD11Tests(unittest.TestCase):
    def test_one_native_call_and_exact_order(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            native = root / 'source/scripts/infer.py'
            native.parent.mkdir(parents=True)
            native.write_text('# pinned fixture\n')
            archive = root / 'source.tar.gz'
            archive.write_bytes(b'fixture source')
            assets = []
            for index in range(12):
                path = root / 'assets/checkpoints' / (
                    'Marigold-V2/depth/Log-stage2/trainables.safetensors' if index == 0
                    else f'Qwen-Image-Edit-2509/transformer/file{index}.bin')
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(bytes([index]))
                assets.append(dict(record=file_record(path)))
            setup = dict(schema='plan069-depth-setup-result/v1', status='complete',
                candidate='D11', source_revision=SOURCE_REVISION,
                source_dir=str(root / 'source'), source_archive=file_record(archive),
                native_source=file_record(native), assets=assets)
            interpreter = root / 'python'
            interpreter.write_text('# fixture\n')
            rgb_a = np.full((540, 960, 3), 11, np.uint8)
            rgb_b = np.full((540, 960, 3), 22, np.uint8)
            calls = []

            def run(command, **kwargs):
                calls.append((command, kwargs))
                self.assertNotIn('--width', command)
                self.assertEqual(kwargs['env']['HF_HUB_OFFLINE'], '1')
                target = root / 'out/native/images/predictions_npy'
                target.mkdir(parents=True)
                np.save(target / 'a.npy', np.full((540, 960), .1, np.float32))
                np.save(target / 'b.npy', np.full((540, 960), .2, np.float32))

            rows = run_folder(setup, [('a', rgb_a), ('b', rgb_b)], root / 'out',
                              interpreter=interpreter, timeout_seconds=100, runner=run)
            self.assertEqual(len(calls), 1)
            adapter = MarigoldLogStage2Adapter(CachedD11Runtime(rows))
            K = np.eye(3)
            valid = np.ones((540, 960), np.bool_)
            self.assertAlmostEqual(float(adapter.predict(rgb_a, K, valid).values[0, 0]), .1)
            with self.assertRaisesRegex(ValueError, 'prediction/input mismatch'):
                adapter.predict(rgb_a, K, valid)
            self.assertAlmostEqual(float(adapter.predict(rgb_b, K, valid).values[0, 0]), .2)


if __name__ == '__main__':
    unittest.main()

import importlib.util
from pathlib import Path
import tempfile
import unittest

try:
    from PIL import Image, PngImagePlugin
    import numpy
except ImportError:
    Image = None


@unittest.skipIf(Image is None, 'requires the research environment')
class ReloadComparisonTests(unittest.TestCase):
    def setUp(self):
        spec = importlib.util.spec_from_file_location('reload_compare',
            Path(__file__).resolve().parents[1]/'scripts/compare-render-reloads.py')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        self.compare = module.compare
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.a, self.b = [Path(self.temp.name)/n for n in ('a', 'b')]
        self.a.mkdir()
        self.b.mkdir()
        for directory in (self.a, self.b):
            Image.new('RGB', (4, 3), (10, 20, 30)).save(directory/'00000.png')

    def test_exact_and_metadata_only_difference(self):
        self.assertEqual(self.compare(self.a, self.b, 1)['byte_exact_count'], 1)
        metadata = PngImagePlugin.PngInfo()
        metadata.add_text('comment', 'same pixels, different PNG bytes')
        Image.new('RGB', (4, 3), (10, 20, 30)).save(self.b/'00000.png', pnginfo=metadata)
        report = self.compare(self.a, self.b, 1)
        self.assertEqual(report['byte_exact_count'], 0)
        self.assertEqual(report['pixel_exact_count'], 1)

    def test_reports_numerical_difference(self):
        Image.new('RGB', (4, 3), (13, 20, 30)).save(self.b/'00000.png')
        report = self.compare(self.a, self.b, 1)
        self.assertEqual(report['max_abs_error_0_255'], 3)
        self.assertEqual(report['mean_abs_error_0_255'], 1)

    def test_missing_extra_and_empty_rejected(self):
        for count in (0, 2):
            with self.assertRaises(ValueError):
                self.compare(self.a, self.b, count)
        Image.new('RGB', (4, 3)).save(self.b/'extra.png')
        with self.assertRaises(ValueError):
            self.compare(self.a, self.b, 1)

    def test_wrong_dimensions_and_mode_rejected(self):
        for mode, size in [('RGB', (5, 3)), ('RGBA', (4, 3))]:
            Image.new(mode, size).save(self.b/'00000.png')
            with self.assertRaises(ValueError):
                self.compare(self.a, self.b, 1)

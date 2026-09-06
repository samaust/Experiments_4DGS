"""Exercise the changed unpacking block without importing CUDA dependencies."""
from pathlib import Path
from types import SimpleNamespace
import textwrap
import unittest


def block(patched):
    patch = (Path(__file__).resolve().parents[1] /
             'patches/atgs-render-eval-unpack.patch').read_text()
    hunk = patch.split('\n@@ ', 1)[1].split('\n', 1)[1]
    lines = []
    for line in hunk.splitlines():
        if line.startswith(' ') or line.startswith('+' if patched else '-'):
            lines.append(line[1:])
    source = '\n'.join(lines).split('    if iteration %', 1)[0]
    return textwrap.dedent(source)


def execute(patched, training):
    namespace = dict(is_training=training, pc=SimpleNamespace(), viewpoint_camera=None,
                     iteration=1, visible_mask=None,
                     generate_full_neural_gaussians=lambda *a, **kw: tuple(range(7 if kw['is_training'] else 5)))
    exec(block(patched), namespace)
    return namespace


class ATGSRenderPatchTests(unittest.TestCase):
    def test_original_fails_inference(self):
        with self.assertRaisesRegex(ValueError, 'not enough values'):
            execute(False, False)

    def test_patch_accepts_five_inference_values(self):
        result = execute(True, False)
        self.assertEqual([result[k] for k in ('xyz', 'color', 'opacity', 'scaling', 'rot')], list(range(5)))
        self.assertNotIn('neural_opacity', result)

    def test_training_outputs_unchanged(self):
        original, patched = execute(False, True), execute(True, True)
        for name in ('xyz', 'color', 'opacity', 'scaling', 'rot', 'neural_opacity', 'mask'):
            self.assertEqual(original[name], patched[name])

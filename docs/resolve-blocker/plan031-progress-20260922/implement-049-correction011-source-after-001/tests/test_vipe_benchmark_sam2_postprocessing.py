"""Stdlib fixtures for the pinned SAM2 warning; no native imports or kernels."""
import builtins
import unittest
from unittest import mock
import warnings

from scripts.vipe_benchmark.sam2_postprocessing import require_sam2_postprocessing


# Independently copied from the two hash-verified source warning sites.
NOTICE = (
    "Skipping the post-processing step due to the error above. You can "
    "still use SAM 2 and it's OK to ignore the error above, although some post-processing "
    "functionality may be limited (which doesn't affect the results in most cases; see "
    "https://github.com/facebookresearch/sam2/blob/main/INSTALL.md)."
)


def emit(message, *, module='sam2.sam2_video_predictor', category=UserWarning):
    warnings.warn_explicit(message, category, filename='fixture.py', lineno=1, module=module, registry={})


def fake_predictor(*, fail):
    misc = dict(__name__='sam2.utils.misc', warnings=warnings, notice=NOTICE, fail=fail)
    exec(compile('''
def fill_holes(frame):
    if fail and frame == 1:
        try:
            raise RuntimeError("fixture native error\\nsecond diagnostic line")
        except Exception as error:
            warnings.warn(str(error) + "\\n\\n" + notice, category=UserWarning, stacklevel=2)
            return "unfilled fallback"
    return "filled-" + str(frame)
''', 'fixture_sam2_misc.py', 'exec'), misc)
    video = dict(__name__='sam2.sam2_video_predictor', fill_holes=misc['fill_holes'])
    exec(compile('''
def propagate_in_video():
    for frame in (0, 1):
        yield fill_holes(frame)
''', 'fixture_sam2_video_predictor.py', 'exec'), video)
    return video['propagate_in_video']


class SAM2PostprocessingTests(unittest.TestCase):
    def test_exact_native_notice_raises_for_both_attributed_predictor_modules(self):
        for module in ('sam2.sam2_video_predictor', 'sam2.sam2_image_predictor'):
            for prefix in ('fixture kernel error', 'first line\nsecond line\nthird line', ''):
                with self.subTest(module=module, prefix=prefix):
                    message = prefix + '\n\n' + NOTICE
                    with self.assertRaises(UserWarning) as caught:
                        with require_sam2_postprocessing():
                            emit(message, module=module)
                    self.assertEqual(str(caught.exception), message)

    def test_real_stacklevel_two_fixture_stops_lazy_fallback_and_runs_pair_cleanup(self):
        propagate = fake_predictor(fail=True)
        completed, resets = [], []
        with self.assertRaisesRegex(UserWarning, 'fixture native error'):
            with require_sam2_postprocessing():
                try:
                    result = list(propagate())
                    completed.append(result)
                finally:
                    resets.append('pair state reset')
        self.assertEqual(completed, [])
        self.assertEqual(resets, ['pair state reset'])

    def test_warning_free_lazy_inference_is_unchanged(self):
        propagate = fake_predictor(fail=False)
        expected = list(propagate())
        with require_sam2_postprocessing():
            actual = list(propagate())
        self.assertEqual(actual, expected)
        self.assertEqual(actual, ['filled-0', 'filled-1'])

    def test_other_messages_remain_warnings_including_near_matches(self):
        messages = (
            'unrelated SAM2 warning', NOTICE,
            'error\n\n' + NOTICE + ' additional text',
            'error\n\n' + NOTICE.replace('Skipping', 'skipping'),
            'error\n\nSkipping the post-processing step due to the error above',
        )
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter('always')
            with require_sam2_postprocessing():
                for message in messages:
                    emit(message)
        self.assertEqual([str(item.message) for item in caught], list(messages))

    def test_exact_message_from_other_modules_is_unaffected(self):
        modules = ('other.library', 'sam2.utils.misc', 'sam2.utils.transforms',
                   'sam2.sam2_video_predictor.extra', 'other.sam2.sam2_video_predictor')
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter('always')
            with require_sam2_postprocessing():
                for module in modules:
                    emit('error\n\n' + NOTICE, module=module)
        self.assertEqual(len(caught), len(modules))

    def test_other_warning_categories_remain_unchanged(self):
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter('always')
            with require_sam2_postprocessing():
                emit('error\n\n' + NOTICE, category=RuntimeWarning)
                emit('error\n\n' + NOTICE, category=DeprecationWarning)
        self.assertEqual([item.category for item in caught], [RuntimeWarning, DeprecationWarning])

    def test_known_warning_overrides_ignore_policy_only_within_guard(self):
        message = 'error\n\n' + NOTICE
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter('ignore', UserWarning)
            with self.assertRaises(UserWarning):
                with require_sam2_postprocessing():
                    emit('unrelated warning')
                    emit(message)
            emit(message)
        self.assertEqual(caught, [])

    def test_filters_and_warning_settings_restore_after_success(self):
        with warnings.catch_warnings():
            warnings.simplefilter('ignore', DeprecationWarning)
            original = list(warnings.filters)
            showwarning, default = warnings.showwarning, warnings.defaultaction
            with require_sam2_postprocessing():
                pass
            self.assertEqual(warnings.filters, original)
            self.assertIs(warnings.showwarning, showwarning)
            self.assertEqual(warnings.defaultaction, default)

    def test_filters_restore_after_fallback_warning_and_arbitrary_exception(self):
        with warnings.catch_warnings():
            warnings.simplefilter('always', UserWarning)
            original = list(warnings.filters)
            with self.assertRaises(UserWarning):
                with require_sam2_postprocessing():
                    emit('error\n\n' + NOTICE)
            self.assertEqual(warnings.filters, original)
            sentinel = RuntimeError('fixture caller failure')
            with self.assertRaises(RuntimeError) as caught:
                with require_sam2_postprocessing():
                    raise sentinel
            self.assertIs(caught.exception, sentinel)
            self.assertEqual(warnings.filters, original)

    def test_preexisting_error_policy_for_unrelated_warning_is_preserved(self):
        with warnings.catch_warnings():
            warnings.simplefilter('error', RuntimeWarning)
            original = list(warnings.filters)
            with self.assertRaises(RuntimeWarning):
                with require_sam2_postprocessing():
                    emit('unrelated diagnostic', category=RuntimeWarning)
            self.assertEqual(warnings.filters, original)

    def test_nested_guard_restores_outer_guard_then_prior_filters(self):
        original = list(warnings.filters)
        with require_sam2_postprocessing():
            outer = list(warnings.filters)
            with require_sam2_postprocessing():
                pass
            self.assertEqual(warnings.filters, outer)
            with self.assertRaises(UserWarning):
                emit('error\n\n' + NOTICE)
        self.assertEqual(warnings.filters, original)

    def test_context_does_not_import_native_or_model_packages(self):
        original_import = builtins.__import__
        def guarded(name, *args, **kwargs):
            if name.split('.')[0] in ('sam2', 'torch', 'numpy', 'cv2'):
                raise AssertionError('native/model import prohibited in fixture')
            return original_import(name, *args, **kwargs)
        with mock.patch.object(builtins, '__import__', side_effect=guarded):
            with require_sam2_postprocessing():
                self.assertEqual(list(fake_predictor(fail=False)()), ['filled-0', 'filled-1'])


if __name__ == '__main__':
    unittest.main()

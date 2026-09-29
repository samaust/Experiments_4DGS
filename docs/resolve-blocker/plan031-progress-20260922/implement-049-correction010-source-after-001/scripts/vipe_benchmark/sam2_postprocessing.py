"""Fail on the exact pinned SAM2 warning that skips native postprocessing.

SAM2 revision 2b90b9f5ceec907a1c18123530e92e794ad901a4 emits this warning
in utils.misc.fill_holes_in_mask_scores and utils.transforms.postprocess_masks.
Both use stacklevel=2, attributing it to their video/image predictor callers.
This guard imports no SAM2/native code and changes no model settings.
"""
from contextlib import contextmanager
import re
import warnings


_NOTICE = (
    "Skipping the post-processing step due to the error above. You can "
    "still use SAM 2 and it's OK to ignore the error above, although some post-processing "
    "functionality may be limited (which doesn't affect the results in most cases; see "
    "https://github.com/facebookresearch/sam2/blob/main/INSTALL.md)."
)
# filterwarnings normally ignores message case. Disable that only for the
# exact pinned notice; the original exception prefix may contain any newlines.
_MESSAGE = r'\A(?s:.*)\n\n(?-i:' + re.escape(_NOTICE) + r')\Z'
_MODULE = r'\Asam2\.sam2_(?:video|image)_predictor\Z'


@contextmanager
def require_sam2_postprocessing():
    """Raise the matching UserWarning immediately; restore filters on all exits.

    Enclose the SAM2 predictor calls, including iteration of lazy propagation.
    Caller-owned finally cleanup still runs. Other warnings and exceptions keep
    their existing behavior. This does not establish that a native kernel works.
    """
    with warnings.catch_warnings():
        warnings.filterwarnings('error', message=_MESSAGE, category=UserWarning, module=_MODULE)
        yield

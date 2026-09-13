"""Frozen M0/M1/M2 motion algorithms with explicit, role-bounded state."""
import numpy as np

from .access import Identity, motion_context, role
from .files import object_hash


def gray(rgb):
    import cv2
    if rgb.dtype != np.uint8 or rgb.ndim != 3 or rgb.shape[2] != 3:
        raise ValueError('motion input must be uint8 RGB')
    return cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)


def dilate(mask):
    import cv2
    return cv2.dilate(mask.astype(np.uint8), np.ones((9, 9), np.uint8), iterations=1) > 0


def changing(identity, method, loader):
    frames = motion_context(identity, method, loader.config)
    if method == 'M2':
        raise ValueError('MOG2 must use one chronological RoleMOG2 state per camera/role')
    images = [gray(loader.load(Identity(identity.branch, identity.camera, f))) for f in frames]
    if method == 'M0':
        difference = np.abs(images[0].astype(np.int16) - images[1].astype(np.int16))
    else:
        target = gray(loader.load(Identity(identity.branch, identity.camera, identity.frame)))
        difference = np.abs(target.astype(np.float32) - np.median(images, axis=0))
    rows = [loader.row(Identity(identity.branch, identity.camera, f))['rgb']['sha256'] for f in frames]
    return dilate(difference > 20), dict(context_frames=frames,
        state_sha256=object_hash(dict(method=method, frames=frames, rgb=rows)))


class RoleMOG2:
    def __init__(self, branch, camera, first_frame):
        import cv2
        self.role, self.lo, self.hi = role(first_frame)
        if first_frame != self.lo or (branch == 'reconstruction') != (self.role == 'reconstruction'):
            raise ValueError('MOG2 must cold-start at the branch role boundary')
        self.branch, self.camera, self.next_frame = branch, camera, first_frame
        self.model = cv2.createBackgroundSubtractorMOG2(history=50, varThreshold=16, detectShadows=True)
        self.state = object_hash(dict(method='M2', branch=branch, camera=camera, role=self.role,
                                     history=50, varThreshold=16, detectShadows=True, learningRate=.02))

    def advance(self, identity, rgb, rgb_hash):
        if (identity.branch, identity.camera, identity.frame) != (self.branch, self.camera, self.next_frame):
            raise ValueError('MOG2 duplicate, skipped, reordered or cross-camera input')
        if role(identity.frame)[0] != self.role or identity.pair_start is not None:
            raise ValueError('MOG2 state crossed a role or tracker context')
        native = self.model.apply(rgb, learningRate=.02)
        self.state = object_hash(dict(previous=self.state, frame=identity.frame, rgb_sha256=rgb_hash))
        self.next_frame += 1
        return dilate((native == 127) | (native == 255)), native, dict(
            context_frames=list(range(self.lo, identity.frame + 1)), state_sha256=self.state,
            cold_start_frame=self.lo, shadow_pixels=int((native == 127).sum()))


def pair_union(first, second):
    if first.dtype != np.bool_ or second.dtype != np.bool_ or first.shape != second.shape:
        raise ValueError('invalid pair motion grids')
    return first | second

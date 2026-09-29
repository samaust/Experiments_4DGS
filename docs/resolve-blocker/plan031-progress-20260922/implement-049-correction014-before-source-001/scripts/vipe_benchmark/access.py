"""Diagnostic membership is separate from historical training/fusion guards."""
from dataclasses import asdict, dataclass

from .config import distinct_pair_frames, training_cameras
from .files import file_record, object_hash, safe_path


@dataclass(frozen=True, order=True)
class Identity:
    branch: str
    camera: int
    frame: int
    pair_start: int | None = None

    def key(self):
        return f'{self.branch}/camera{self.camera}/' + (
            f'pair{self.pair_start}/' if self.pair_start is not None else '') + f'frame{self.frame}'

    def record(self):
        return asdict(self)


def role(frame):
    if type(frame) is not int:
        raise ValueError('source frame must be an integer')
    if 0 <= frame <= 49:
        return 'reconstruction', 0, 49
    if 50 <= frame <= 149:
        return 'fit', 50, 149
    if 150 <= frame <= 199:
        return 'selection', 150, 199
    raise ValueError('frame outside permitted diagnostic roles; no final-window images')


def guard(identity, config, *, context=False):
    c, f, t = identity.camera, identity.frame, identity.pair_start
    if type(c) is not int or c not in range(34):
        raise ValueError('physical camera ID required')
    name, _, _ = role(f)
    if identity.branch == 'calibration':
        if name == 'reconstruction' or t is not None:
            raise ValueError('calibration branch/role mismatch')
        if not context and f not in config[name + '_snapshots']:
            raise ValueError('not a calibration snapshot')
    elif identity.branch == 'reconstruction':
        if c not in training_cameras(config) or name != 'reconstruction':
            raise ValueError('held-out camera or wrong reconstruction role')
        if context:
            if t is not None:
                raise ValueError('motion RGB context must have no pair identity')
        elif t not in config['pair_starts'] or f not in (t, t + 1):
            raise ValueError('missing or incorrect tracker-pair context')
    elif identity.branch == 'depth':
        if c not in training_cameras(config) or f not in (
                config['scale_fit_frame'], config['scale_check_frame']) or t is not None:
            raise ValueError('depth camera/frame role mismatch')
    else:
        raise ValueError('unknown diagnostic branch')
    return name


def motion_context(identity, method, config):
    name = guard(identity, config, context=identity.pair_start is None)
    _, lo, hi = role(identity.frame)
    f, t = identity.frame, identity.pair_start
    if method == 'M0':
        return [t, t + 1] if t is not None else [f, f + 1 if f < hi else f - 1]
    if method == 'M1':
        a = max(lo, min(f - 4, hi - 8))
        return list(range(a, a + 9))
    if method == 'M2':
        return list(range(lo, f + 1))
    raise ValueError(f'unknown motion method: {method} in {name}')


def annotation_identities(config):
    calibration = [Identity('calibration', c, f) for c in config['annotation_calibration_cameras']
                   for f in config['annotation_calibration_frames']]
    reconstruction = [Identity('reconstruction', c, f) for c in config['diagnostic_cameras']
                      for f in distinct_pair_frames(config)]
    return calibration + reconstruction


def output_identities(config, branch):
    if branch == 'calibration':
        return [Identity(branch, c, f) for c in range(34)
                for f in config['fit_snapshots'] + config['selection_snapshots']]
    if branch == 'reconstruction':
        return [Identity(branch, c, f, t) for c in training_cameras(config)
                for t in config['pair_starts'] for f in (t, t + 1)]
    if branch == 'depth':
        return [Identity(branch, c, f) for c in training_cameras(config)
                for f in (config['scale_fit_frame'], config['scale_check_frame'])]
    raise ValueError('unknown branch')


def validate_membership(rows, expected):
    keys = [Identity(**r['identity']).key() for r in rows]
    required = {i.key() for i in expected}
    if len(keys) != len(set(keys)) or set(keys) != required:
        raise ValueError('duplicate, missing, extra or colliding input identities')


def validate_grid(row, expected_K, grid):
    import numpy as np
    K = np.asarray(row['K'], dtype=np.float64)
    if row['grid'] != grid or K.shape != (3, 3) or not np.isfinite(K).all():
        raise ValueError('wrong branch/grid/intrinsics')
    if not np.allclose(K, expected_K, rtol=0, atol=1e-10):
        raise ValueError('changed or wrong-grid intrinsics')


class RGBLoader:
    def __init__(self, rows, config):
        self.config = config
        self.rows = {}
        for row in rows:
            identity = Identity(**row['identity'])
            guard(identity, config, context=True)
            if identity.key() in self.rows:
                raise ValueError('duplicate RGB identity')
            self.rows[identity.key()] = row

    def row(self, identity):
        guard(identity, self.config, context=identity.pair_start is None)
        image_identity = Identity(identity.branch, identity.camera, identity.frame)
        try:
            return self.rows[image_identity.key()]
        except KeyError as error:
            raise ValueError('RGB absent from immutable manifest') from error

    def load(self, identity):
        import cv2
        row = self.row(identity)
        file_record(row['rgb']['path'], row['rgb']['sha256'])
        image = cv2.imread(str(safe_path(row['rgb']['path'])), cv2.IMREAD_COLOR)
        if image is None or image.shape != (540, 960, 3):
            raise ValueError('invalid RGB image grid')
        return cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

    def context(self, identity, method):
        frames = motion_context(identity, method, self.config)
        if any(role(f)[0] != role(identity.frame)[0] for f in frames):
            raise ValueError('motion context crossed a role boundary')
        rows = [self.row(Identity(identity.branch, identity.camera, f)) for f in frames]
        return frames, object_hash([r['rgb']['sha256'] for r in rows])

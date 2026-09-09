"""Plan 027 accounting and serial process supervision, preserving Plan 026 files."""
from pathlib import Path

import basketball_study as historical

ROOT = historical.ROOT
ARTIFACTS = ROOT / '.local/basketball-dense-training'
DOCS = ROOT / 'docs/experiments/basketball-dense-training'
ARMS = ('freetimegs-dense-coarse', 'freetimegs-dense-cropped')
ORDER = tuple((arm, seed) for seed in range(3) for arm in ARMS)


def configure():
    historical.ARTIFACTS = ARTIFACTS
    historical.DOCS = DOCS


if __name__ == '__main__':
    configure()
    historical.main()

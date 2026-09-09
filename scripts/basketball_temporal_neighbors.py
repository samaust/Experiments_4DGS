"""Rank training neighbors by shared tracks in the frozen accepted static map."""
import argparse
from collections import Counter
import json
from pathlib import Path
import re

from basketball_study import CAMERAS, ROOT, digest, write_new


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    import pycolmap
    init = json.loads((ROOT / '.local/sync-pivot/basketball-static-init/result.json').read_text())
    path = ROOT / init['map_path']
    reconstruction = pycolmap.Reconstruction(str(path))
    ids = {i: int(re.fullmatch(r'camera(\d+)\.png', image.name)[1])
           for i, image in reconstruction.images.items()}
    overlap = Counter()
    for point in reconstruction.points3D.values():
        cameras = sorted({ids[e.image_id] for e in point.track.elements if ids[e.image_id] in CAMERAS})
        for i, c in enumerate(cameras):
            for other in cameras[:i]:
                overlap[c, other] += 1
                overlap[other, c] += 1
    neighbors = {}
    pairs = []
    for c in CAMERAS:
        ranked = sorted((o for o in CAMERAS if o != c), key=lambda o: (-overlap[c, o], o))
        chosen = [o for o in ranked if overlap[c, o] > 0][:3]
        neighbors[str(c)] = chosen
        for o in ranked:
            pairs.append(dict(reference=c, other=o, shared_tracks=overlap[c, o],
                              selected=o in chosen, reason='selected' if o in chosen else
                              'missing static overlap' if overlap[c, o] == 0 else 'ranked below top three'))
    write_new(a.output, dict(schema='basketball-temporal-neighbors/v1', neighbors=neighbors,
              pairs=pairs, source_files={str(f): digest(f) for f in path.iterdir() if f.suffix == '.bin'},
              adapter_sha256=digest(__file__),
              provenance='reuse accepted calibration-window static tracks only; no image access'))


if __name__ == '__main__':
    main()

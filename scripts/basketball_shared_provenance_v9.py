"""Verify exact frozen v9 sources through explicitly archived packaging-only fixes."""
from pathlib import Path
from basketball_audit import sha256
from basketball_scale import read

CORRECTION=Path('docs/experiments/basketball-shared-timing-v9/corrections/serialization.json')

def verify_hashes(hashes):
    replacements=read(CORRECTION)['source_replacements'] if CORRECTION.exists() else []
    for name,expected in hashes.items():
        actual=sha256(name)
        if actual==expected:continue
        match=next((r for r in replacements if r['path']==str(name) and r['original_sha256']==expected and r.get('corrected_sha256')==actual),None)
        if match is None or sha256(match['archive'])!=expected:raise ValueError('immutable hash mismatch '+str(name))

"""Provenance-checked CPU-only subsetting of complete camera priors."""
import argparse
import json
from pathlib import Path
import shutil
import time
from basketball_audit import sha256
from basketball_protocol import CAMERAS,PROTOCOL,EXCLUDED,manifest_protocol
from basketball_vipe_pilot import intrinsic_stability


def subset(source,output):
    started=time.monotonic()
    result=json.loads((source/'result.json').read_text())
    if result['status']!='priors-generated' or result['blockers']:
        raise ValueError('requires complete passing source priors')
    frames=result['source_frames']
    if not frames or len(set(frames))!=len(frames) or any(f<50 or f>=150 for f in frames):
        raise ValueError('invalid fitting frames')
    selected=[e for e in result['observations'] if e['camera_id'] in CAMERAS]
    expected={(c,f) for c in CAMERAS for f in frames}
    if {(e['camera_id'],e['source_frame_id']) for e in selected}!=expected or len(selected)!=len(expected):
        raise ValueError('missing or duplicate retained priors')
    stability={str(c):intrinsic_stability([e['K_960x540'][0][0] for e in selected if e['camera_id']==c],expected_count=len(frames)) for c in CAMERAS}
    if not all(s['passed'] for s in stability.values()):raise ValueError('retained priors fail the current intrinsic gate')
    artifacts=json.loads((source/'artifacts.json').read_text());copied={}
    for e in selected:
        for suffix in ['.png','-motion.npy','-static.png']+(['-depth.npz'] if e['source_frame_id']==100 else []):
            name=e['stem']+suffix
            if sha256(source/name)!=artifacts[name]:raise ValueError(f'changed prior artifact: {name}')
            copied[name]=artifacts[name]
    output.mkdir(exist_ok=False)
    for name in copied:shutil.copy2(source/name,output/name)
    config=dict(schema='basketball-subset-priors/v1',protocol=manifest_protocol(),source_result_sha256=sha256(source/'result.json'),
                source_artifacts_sha256=sha256(source/'artifacts.json'),adapter_sha256=sha256(__file__),operation='verified CPU-only subset; no new inference')
    (output/'config.json').write_text(json.dumps(config,indent=2)+'\n')
    result.update(protocol=PROTOCOL,excluded_cameras=list(EXCLUDED),observations=selected,intrinsic_stability=stability,
                  source_result_sha256=sha256(source/'result.json'),config_sha256=sha256(output/'config.json'),adapter_sha256=sha256(__file__),
                  inference_reused=True,source_wall_seconds=result['wall_seconds'],wall_seconds=time.monotonic()-started)
    (output/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    (output/'artifacts.json').write_text(json.dumps(copied,indent=2)+'\n')


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();subset(a.source,a.output)


if __name__=='__main__':main()

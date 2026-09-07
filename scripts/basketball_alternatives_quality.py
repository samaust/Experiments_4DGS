"""Replay the existing focus diagnostic for all 34 cameras without prior gates."""
import argparse
import json
from pathlib import Path
import time
import cv2
import basketball_focus as focus
from basketball_alternatives_protocol import CAMERAS,EARLY,LATE,PROTOCOL
from basketball_alternatives_colmap import dump
from basketball_audit import sha256


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--inputs',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args()
    if a.output.exists():raise ValueError('preserve the existing diagnostic')
    source=json.loads((a.inputs/'result.json').read_text())
    if source['status']!='prepared' or tuple(focus.EARLY+focus.LATE)!=EARLY+LATE:
        raise ValueError('unprepared input or changed focus windows')
    entries=source['observations']
    if len(entries)!=340 or {(e['camera_id'],e['source_frame_id']) for e in entries}!={(c,f) for c in CAMERAS for f in EARLY+LATE}:
        raise ValueError('requires exactly 34 cameras and ten fitting samples')
    artifacts={}
    for e in entries:
        artifacts[e['stem']+'.png']=e['image_sha256']
        artifacts[e['stem']+'-static.png']=e['mask_sha256']
    cv2.setRNGSeed(0);start=time.monotonic()
    result=dict(protocol=PROTOCOL,input_sha256=sha256(a.inputs/'result.json'),
        adapter_sha256=sha256(__file__),focus_implementation_sha256=sha256(focus.__file__),
        cameras={c:focus.screen_camera(a.inputs,c,artifacts) for c in CAMERAS})
    result['wall_seconds']=time.monotonic()-start
    dump(a.output,result)
    print({c:r['status'] for c,r in result['cameras'].items()})


if __name__=='__main__':main()

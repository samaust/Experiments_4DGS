"""Measure PNG sequence changes; these are descriptive, not flicker scores."""
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np
from PIL import Image

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--input',type=Path,required=True)
p.add_argument('--output',type=Path,required=True)
p.add_argument('--reference',type=Path)
p.add_argument('--previous-run',type=Path)
a=p.parse_args()
paths=sorted(a.input.glob('*.png'))
adjacent=[];background=[];psnr=[];hashes={};equal=[];prev=None
for path in paths:
    im=np.asarray(Image.open(path).convert('RGB'),dtype=np.float32)
    hashes[path.name]=hashlib.sha256(path.read_bytes()).hexdigest()
    if prev is not None:
        diff=np.abs(im-prev)
        adjacent.append(float(diff.mean()))
        if im.shape[:2]==(1014,1352): background.append(float(diff[80:320,250:950].mean()))
    if a.reference:
        gt=np.asarray(Image.open(a.reference/path.name).convert('RGB'),dtype=np.float32)
        mse=float(np.square(im-gt).mean())
        psnr.append(float(10*np.log10(255**2/mse)) if mse else None)
    if a.previous_run:
        equal.append((a.previous_run/path.name).is_file() and path.read_bytes()==(a.previous_run/path.name).read_bytes())
    prev=im
def summary(values):
    return {'min':min(values),'mean':float(np.mean(values)),'max':max(values)} if values else None
result={'count':len(paths),'dimensions':list(im.shape),'adjacent_mae_0_255':summary(adjacent),
        'blinds_region_mae_0_255':summary(background),'png_psnr_db':summary(psnr),
        'identical_to_previous_count':sum(equal) if equal else None,'sha256':hashes,
        'note':'Adjacent differences include real motion; PNG PSNR uses quantized outputs. Neither is a held-out or temporal-fidelity claim.'}
a.output.write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({k:v for k,v in result.items() if k!='sha256'},indent=2))

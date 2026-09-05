"""Make labeled inspection sheets and pixel-change summaries from PNG evidence."""
import argparse
import json
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--input', type=Path, required=True)
p.add_argument('--output', type=Path, required=True)
p.add_argument('--names', nargs='+')
a=p.parse_args()
paths=[a.input/x for x in a.names] if a.names else sorted(a.input.glob('*.png'))
selected=paths if a.names else [paths[0],paths[len(paths)//2],paths[-1]]
sheet=Image.new('RGB',(480*len(selected),760),'#202020')
draw=ImageDraw.Draw(sheet)
for i,path in enumerate(selected):
    img=Image.open(path).convert('RGB')
    thumb=img.copy();thumb.thumbnail((480,355))
    sheet.paste(thumb,(i*480,24))
    draw.text((i*480+5,5),path.name,fill='white')
    w,h=img.size
    crop=img.crop((w//4,h//4,3*w//4,3*h//4));crop.thumbnail((480,355))
    sheet.paste(crop,(i*480,405))
    draw.text((i*480+5,385),'Center crop',fill='white')
a.output.parent.mkdir(parents=True,exist_ok=True)
sheet.save(a.output)
stats=[]; previous=None
for path in paths:
    im=np.asarray(Image.open(path).convert('RGB'),dtype=np.float32)
    item={'file':str(path),'shape':list(im.shape),'mean':float(im.mean()),'std':float(im.std())}
    if previous is not None and previous.shape==im.shape:
        item['previous_frame_mae_0_255']=float(np.abs(im-previous).mean())
    stats.append(item);previous=im
a.output.with_suffix('.json').write_text(json.dumps(stats,indent=2)+'\n')
print(a.output)

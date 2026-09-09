"""Fixed seed/camera/time comparison from already evaluated Plan 024 images."""
import json
from pathlib import Path
import numpy as np
from PIL import Image
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT=Path(__file__).resolve().parents[1]
LOCAL=ROOT/'.local/sync-pivot/evaluation'
REPORT=ROOT/'docs/research/basketball-sync-pivot'


def main():
    # Fixed seed0 and interpolation frame22 for every held-out camera: no score selection.
    tables={}
    for method in ['stg-full','freetimegs']:
        path=LOCAL/f'{method}-seed0/worker/first/render.json'
        if not path.exists():continue
        tables[method]=(path.parent,{(r['camera'],r['frame_id']):r for r in json.loads(path.read_text())['frames']})
    if not tables:raise ValueError('no retained predictions')
    methods=list(tables);fig,axes=plt.subplots(4,len(methods)+1,figsize=(5*(len(methods)+1),11),squeeze=False)
    for i,c in enumerate(['0','10','20','30']):
        key=(c,22);row=tables[methods[0]][1][key]
        paths=[Path(row['target_path'])]+[tables[m][0]/tables[m][1][key]['path'] for m in methods]
        for j,path in enumerate(paths):
            axes[i,j].imshow(np.asarray(Image.open(path)));axes[i,j].set_xticks([]);axes[i,j].set_yticks([])
            if i==0:axes[i,j].set_title((['Ground truth']+methods)[j])
            if j==0:axes[i,j].set_ylabel(f'Camera {c}',fontsize=12)
    fig.suptitle('Zero-offset controls — seed 0, source frame 22 (temporal holdout)',fontsize=16)
    fig.tight_layout(rect=[0,0,1,.96]);fig.savefig(REPORT/'reconstruction-comparison.jpg',dpi=120);plt.close(fig)


if __name__=='__main__':main()

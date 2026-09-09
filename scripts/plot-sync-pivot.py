"""CPU report figures from retained graph and checkpoint evidence."""
import argparse
import json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('kind',choices=['graph','offsets'])
    p.add_argument('--directory',type=Path,default=Path('docs/research/basketball-sync-pivot'));a=p.parse_args()
    plt.rcParams['svg.fonttype']='none'
    plt.rcParams['svg.hashsalt']='plan024'
    if a.kind=='graph':
        report=json.loads((a.directory/'sift-common-graph.json').read_text())
        freeze=json.loads((a.directory/'basketball-freeze.json').read_text())
        calibration=json.loads(Path(freeze['calibration_path']).read_text())
        if [c['camera_id'] for c in calibration['cameras']]!=list(range(34)):
            raise ValueError('expected original ordered camera IDs')
        xyz=np.array([c['center'] for c in calibration['cameras']])*freeze['scale']
        _,_,vt=np.linalg.svd(xyz-xyz.mean(0),full_matrices=False);xy=(xyz-xyz.mean(0))@vt[:2].T
        global_fit=report['global_fit'];covered=set(global_fit['coverage'])
        bridges={tuple(sorted(e)) for e in global_fit['bridges']};selected=freeze['syncnerf_camera_ids']
        fig,ax=plt.subplots(figsize=(9,3.7))
        for pair in report['pairs']:
            if not pair.get('accepted'):continue
            i,j=int(pair['i']),int(pair['j']);bridge=tuple(sorted([str(i),str(j)])) in bridges
            ax.plot(xy[[i,j],0],xy[[i,j],1],color='#d97706' if bridge else '#9ca3af',linewidth=1.6 if bridge else .8,zorder=1)
        for i,(x,y) in enumerate(xy):
            ax.scatter(x,y,s=100,c='#0072b2' if str(i) in covered else '#bbbbbb',zorder=3)
            if i in selected:ax.scatter(x,y,s=180,facecolors='none',edgecolors='#009e73',linewidths=1.7,zorder=4)
            ax.annotate(str(i),(x,y),xytext=(5,5),textcoords='offset points',fontsize=9,zorder=5)
        ax.set(title='Saved SIFT/LK graph: reference 1 covers 8 of 34 cameras',xlabel='Principal axis 1 (estimated scale)',ylabel='Principal axis 2 (estimated scale)')
        ax.set_aspect('equal');ax.grid(alpha=.15)
        fig.text(.08,.035,'Blue: reference-connected. Gray: unanchored. Green ring: Sync-NeRF subset. Orange: graph bridge.\nSaved fit-window evidence only; connectivity is not timing accuracy.',fontsize=9)
        filename='graph-support.svg'
    else:
        data=json.loads((a.directory/'syncnerf-matched-checkpoint.json').read_text())
        ids=data['camera_ids'];fig,ax=plt.subplots(figsize=(8,5))
        colors=['#0072b2','#d55e00','#009e73']
        for row,color in zip(data['runs'],colors):
            ax.scatter([1000*row['offset_seconds'][str(c)] for c in ids],np.arange(len(ids))+(row['seed']-1)*.13,label=f"Seed {row['seed']}",color=color,s=32)
        ax.axvline(0,color='#777777',linewidth=.8);ax.set_yticks(range(len(ids)),[str(c) for c in ids]);ax.invert_yaxis()
        ax.set(xlabel='Relative offset (ms); corrected time = source time − offset',ylabel='Original camera ID',title=f"Sync-NeRF pilot: matched checkpoint {data['iteration']:,}")
        ax.legend();ax.grid(axis='x',alpha=.2)
        fig.text(.1,.025,'Optimizer seed spread is not ground-truth timing uncertainty. Only eight cameras are represented.',fontsize=9)
        filename='syncnerf-offsets.svg'
    fig.tight_layout(rect=[0,.08,1,1]);fig.savefig(a.directory/filename,metadata={'Date':None})
    svg=a.directory/filename
    svg.write_text('\n'.join(line.rstrip() for line in svg.read_text().splitlines())+'\n')
    fig.savefig(Path('.local/sync-pivot')/filename.replace('.svg','-preview.png'),dpi=120)
    plt.close(fig)


if __name__=='__main__':main()

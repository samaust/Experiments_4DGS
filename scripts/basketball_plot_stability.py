"""Plot blocked calibration diagnostics from a frozen pose-comparison artifact."""
import argparse
import json
from pathlib import Path


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--input',required=True,type=Path)
    p.add_argument('--output',required=True,type=Path)
    p.add_argument('--title',default='Basketball: independent fitting-window pose stability\nSIFT + bounded RoMa, after converged robust refinement — BLOCKED')
    a=p.parse_args()
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    r=json.loads(a.input.read_text())
    fig,axes=plt.subplots(2,1,figsize=(11,6),sharex=True,layout='constrained')
    x=range(len(r['cameras']))
    series=[(r['rotation_degrees'],.5,'Rotation disagreement (degrees)'),
            ([100*v for v in r['center_fraction_of_diameter']],1.,'Center disagreement (% of rig diameter)')]
    for ax,(values,limit,label) in zip(axes,series):
        ax.bar(x,values,color=['#b94a48' if v>limit else '#31708f' for v in values],width=.75)
        ax.axhline(limit,color='#222222',linestyle='--',linewidth=1,label=f'Acceptance limit: {limit:g}')
        ax.set_ylabel(label);ax.legend(loc='upper right');ax.grid(axis='y',alpha=.2);ax.set_axisbelow(True)
    axes[1].set_xticks(list(x),r['cameras']);axes[1].set_xlabel('Retained training camera (original physical ID)')
    fig.suptitle(a.title)
    fig.savefig(a.output,dpi=160)


if __name__=='__main__':main()

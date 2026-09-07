"""Publish compact calibration evidence and per-camera plots from saved runs."""
import argparse
import json
import os
from pathlib import Path
import re
import shutil
import numpy as np
from basketball_audit import sha256
from basketball_alternatives_colmap import dump


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--workspace',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();w=a.workspace;out=a.output;out.mkdir(parents=True,exist_ok=True)
    for name in ('screening','finalists','focus','focus-replay','source-pins','remaining-weight-pins',
                 'vggt-omega-access','database-header-repairs','frozen-winner','validation-consumed'):
        if (w/f'{name}.json').exists():shutil.copy2(w/f'{name}.json',out/f'{name}.json')
    for source,target in [('full-rig-incremental-radial/result.json','full-rig.json'),
                          ('full-rig-incremental-radial/calibration.json','calibration.json'),
                          ('selection-incremental-radial-verified/result.json','selection.json'),
                          ('validation-incremental-radial/result.json','validation.json')]:
        if (w/source).exists():shutil.copy2(w/source,out/target)
    runs={str(path.parent.relative_to(w)):json.loads(path.read_text()) for path in sorted(w.glob('*/result.json'))}
    dump(out/'run-results.json',runs)
    commands={path.name:json.loads(path.read_text()) for path in sorted(w.glob('*-command.json'))}
    dump(out/'commands.json',commands)
    native={}
    for name,r in runs.items():
        folder=w/name
        for pattern in ('native.*','calibration*.json','sparse/*.bin','camera*-observations.npz','camera*-observations.npy'):
            for path in sorted(folder.glob(pattern)):
                native[str(path.relative_to(w))]=dict(sha256=sha256(path),bytes=path.stat().st_size)
    dump(out/'native-artifacts.json',native)
    weights={}
    for folder in sorted((w/'weights').iterdir()):
        if (folder/'pin.json').exists():
            weights[folder.name]=dict(pin=json.loads((folder/'pin.json').read_text()),
                files={p.name:sha256(p) for p in sorted(folder.iterdir()) if p.is_file()})
    cache=Path('.local/cache/torch/hub')
    ancillary={str(cache/'checkpoints'/name):sha256(cache/'checkpoints'/name)
               for name in ('superpoint_v1.pth','superpoint_lightglue_v0-1_arxiv.pth')}
    dinov2={}
    for root,dirs,files in os.walk(cache/'facebookresearch_dinov2_main'):
        dirs[:]=[d for d in dirs if d not in ('prompts','.git','__pycache__')]
        for name in files:
            path=Path(root)/name
            if path.suffix in ('.py','.toml','.cfg','.txt') or name.startswith('LICENSE'):
                dinov2[str(path.relative_to(cache/'facebookresearch_dinov2_main'))]=sha256(path)
    dump(out/'weight-pins.json',dict(weights=weights,frontend=ancillary,
        dinov2=dict(source='facebookresearch/dinov2 Torch Hub main snapshot',files=dinov2,
                    limitation='architecture snapshot hashed after initial inference; upstream commit was not pinned before first download')))
    envs=out/'environments';envs.mkdir(exist_ok=True)
    for path in (w/'environments').glob('*.txt'):shutil.copy2(path,envs/path.name)
    logs={p.name:dict(sha256=sha256(p),bytes=p.stat().st_size) for p in sorted(w.glob('*.log'))}
    dump(out/'logs.json',logs)
    previous=Path('.local/calibration/basketball-v1/gpu-ledger.json')
    ledger=json.loads(previous.read_text())
    resources=dict(cumulative_gpu_limit_seconds=None,historical_ledger_sha256=sha256(previous),
        historical_charged_seconds=sum(r.get('charged_seconds',0.) for r in ledger['attempts']),
        measurement_notes=['Wall times include process setup as specified by each adapter; CPU jobs can overlap.',
            'Torch peak allocation/reservation is process-local, not global NVML usage.',
            'Missing memory measurements remain null; CPU-only jobs are not assigned fabricated GPU use.',
            'Snapshot ranking charges a shared frontend to each mapper; total accounting counts each stored frontend once.',
            'Archived failed and repaired runs are retained separately; some diagnostic probes have no timing record.'],
        snapshots={},recorded_jobs=[])
    for method in ('global','incremental','mast3r','da3','map-anything'):
        selected=[r for name,r in runs.items() if re.fullmatch(re.escape(method)+r'-\d+',name)]
        peak=lambda key:max((r[key] for r in selected if key in r),default=None)
        resources['snapshots'][method]=dict(runs=len(selected),
            wall_seconds=sum(r['wall_seconds'] for r in selected),
            peak_host_rss_kib=peak('peak_host_rss_kib'),peak_allocated_bytes=peak('peak_allocated_bytes'),
            peak_reserved_bytes=peak('peak_reserved_bytes'))
    for name,r in runs.items():
        resources['recorded_jobs'].append(dict(name=name,status=r.get('status'),
            **{k:r.get(k) for k in ('wall_seconds','peak_host_rss_kib','peak_allocated_bytes','peak_reserved_bytes')}))
    dump(out/'resources.json',resources)
    names=set(runs)
    native_names={f'{method}-window-{tag}{side}-seed{seed}'
        for method in ('incremental','map-anything','mast3r')
        for tag in (('','sharp-') if method=='incremental' else ('',))
        for side in ('early','late') for seed in (0,1,2)}
    ba_names={f'{method}-ba-{tag}{policy}-{side}-seed{seed}'
        for method in ('incremental','map-anything','mast3r') for tag in ('','sharp-')
        for policy in ('fixed','focal','radial') for side in ('early','late') for seed in (0,1,2)}
    accounting=dict(primary_snapshot_slots=48,executed_snapshot_runs=30,
        installation_or_checkpoint_blocked_slots=18,nominal_finalist_slots=144,
        duplicate_native_slots_reused=12,unique_native_window_runs=len(native_names & names),
        unique_common_ba_runs=len(ba_names & names),
        logged_iteration_extensions=sum(name+'-iter1000' in names for name in ba_names),
        missing_initial_finalist_runs=sorted((native_names|ba_names)-names),
        finalist_initial_matrix_complete=(native_names|ba_names)<=names)
    dump(out/'matrix-accounting.json',accounting)
    finalists=json.loads((out/'finalists.json').read_text())
    lines=['# Worst-seed five-frame comparison','',
           'Center values are percentages of training-rig diameter. All three seeds must pass every gate.','',
           '| Method | Support | Intrinsic policy | Rotation (degrees) | Center (%) | All training gates |',
           '| --- | --- | --- | ---: | ---: | --- |']
    for r in finalists['configurations']:
        values=[r['method'],'sharp' if r['sharp'] else 'ordinary',r['policy']]
        values+=[f"{r['max_rotation_degrees']:.6f}",f"{r['max_center_fraction']*100:.6f}",'pass' if r['passes_training_gates'] else 'fail'] if r['complete'] else ['pending','pending','pending']
        lines.append('| '+' | '.join(values)+' |')
    (out/'finalist-table.md').write_text('\n'.join(lines)+'\n')
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    plt.rcParams.update({'font.size':10,'svg.fonttype':'none'})
    screening=json.loads((out/'screening.json').read_text())
    rows=[r for r in screening['pairs'] if r.get('per_camera')]
    fig,axes=plt.subplots(1,2,figsize=(15,6),layout='constrained')
    for ax,key,title in zip(axes,['rotation_degrees','center_fraction'],['Rotation disagreement (degrees)','Center disagreement (% rig diameter)']):
        z=np.array([[e[key]*(100 if key=='center_fraction' else 1) for e in r['per_camera']] for r in rows])
        im=ax.imshow(z,aspect='auto',cmap='magma');fig.colorbar(im,ax=ax,shrink=.8)
        ax.set_yticks(range(len(rows)),[f"{r['method']} {r['frames'][0]}/{r['frames'][1]}"+(' [invalid K]' if not r['complete'] else '') for r in rows])
        ax.set_xticks(range(len(rows[0]['per_camera'])),[e['camera_id'] for e in rows[0]['per_camera']],fontsize=8)
        ax.set(xlabel='Physical training camera ID',title=title)
    fig.savefig(out/'snapshot-per-camera.svg');plt.close(fig)
    full=json.loads((out/'full-rig.json').read_text())
    fig,axes=plt.subplots(2,1,figsize=(13,6),sharex=True,layout='constrained')
    for ax,key,threshold,title in zip(axes,['rotation_degrees','center_fraction'],[.5,1.],['Rotation disagreement (degrees)','Center disagreement (% rig diameter)']):
        for row in full['paired']:
            ax.plot(range(34),[e[key]*(100 if key=='center_fraction' else 1) for e in row['per_camera']],marker='.',label=f"seed {row['seed']}")
        ax.axhline(threshold,color='red',linestyle='--',label='limit');ax.set_ylabel(title);ax.legend(ncol=4)
        for c in (0,10,20,30):ax.axvspan(c-.3,c+.3,color='gray',alpha=.15)
    axes[-1].set_xticks(range(34));axes[-1].set_xlabel('Physical camera ID; gray bands mark held-outs')
    fig.savefig(out/'full-rig-repeatability.svg');plt.close(fig)
    if (out/'validation.json').exists():
        validation=json.loads((out/'validation.json').read_text())
        fig,axes=plt.subplots(2,1,figsize=(13,6),sharex=True,layout='constrained')
        for name,key,threshold in [('median','reprojection_median',1.),('p95','reprojection_p95',3.)]:
            axes[0].plot(range(34),[r[key] for r in validation['cameras']],marker='.',label=name)
            axes[0].axhline(threshold,linestyle='--',label=f'{name} limit')
        axes[0].set_ylabel('Final reprojection error (pixels)');axes[0].legend(ncol=4)
        axes[1].bar(range(34),[r['independent_static_points'] for r in validation['cameras']])
        axes[1].axhline(100,color='red',linestyle='--',label='100-point limit');axes[1].legend()
        axes[1].set_ylabel('Independent static points');axes[1].set_xticks(range(34));axes[1].set_xlabel('Physical camera ID')
        fig.savefig(out/'validation-per-camera.svg');plt.close(fig)
    regional={}
    for folder in ('selection-incremental-radial','selection-incremental-radial-geometric',
                   'selection-incremental-radial-verified','validation-incremental-radial'):
        if not (w/folder/'result.json').exists():continue
        per_camera=[]
        for camera in range(34):
            observations=np.load(w/folder/f'camera{camera}-observations.npy')
            cells=[]
            for cy in range(4):
                for cx in range(4):
                    selected=observations[(observations[:,2]>=cx*240)&(observations[:,2]<(cx+1)*240)&
                                          (observations[:,3]>=cy*135)&(observations[:,3]<(cy+1)*135)]
                    finite=selected[np.isfinite(selected[:,4])]
                    cells.append(dict(x=cx,y=cy,observations=len(selected),unique_points=len(set(selected[:,1])),
                        nonfinite=len(selected)-len(finite),
                        median=float(np.median(finite[:,4])) if len(finite) else None,
                        p95=float(np.percentile(finite[:,4],95)) if len(finite) else None))
            per_camera.append(dict(camera_id=camera,cells=cells))
        regional[folder]=per_camera
    dump(out/'regions.json',regional)
    fig,axes=plt.subplots(len(regional),1,figsize=(13,3*len(regional)),layout='constrained',squeeze=False)
    for ax,(name,rows) in zip(axes[:,0],regional.items()):
        z=np.array([[cell['p95'] if cell['p95'] is not None else np.nan for cell in r['cells']] for r in rows]).T
        im=ax.imshow(z,aspect='auto',vmin=0,vmax=3,cmap='magma');fig.colorbar(im,ax=ax,label='p95 pixels (saturated at 3)')
        ax.set_xticks(range(34));ax.set_yticks(range(16));ax.set(title=name,xlabel='Physical camera ID',ylabel='4×4 cell (row major)')
    fig.savefig(out/'region-p95.svg');plt.close(fig)
    # Matplotlib emits trailing spaces in multiline SVG path attributes.
    for path in out.glob('*.svg'):
        path.write_text('\n'.join(line.rstrip() for line in path.read_text().splitlines())+'\n')
    dump(out/'artifacts.json',{str(p.relative_to(out)):sha256(p) for p in sorted(out.rglob('*')) if p.is_file() and p.name!='artifacts.json'})


if __name__=='__main__':main()

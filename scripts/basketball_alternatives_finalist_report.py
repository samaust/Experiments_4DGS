"""Summarize paired windows, all seeds and intrinsic/support configurations."""
import argparse
import json
from pathlib import Path
from basketball_alternatives_compare import load_export,compare
from basketball_alternatives_colmap import dump


def locate(w,method,policy,sharp,side,seed):
    tag='sharp-' if sharp else ''
    if policy=='native':
        if method not in ('incremental','global'):tag=''
        path=w/f'{method}-window-{tag}{side}-seed{seed}'
    else:
        path=w/f'{method}-ba-{tag}{policy}-{side}-seed{seed}'
        extended=path.with_name(path.name+'-iter1000')
        if (extended/'result.json').exists():path=extended
    return path


def support_passed(rows):
    return bool(rows) and all(r['independent_static_points']>=100 and r['other_cameras']>=2 and
        r['occupied_grid_cells']>=6 and r['positive_depth_fraction']>=.95 and
        r['reprojection_median'] is not None and r['reprojection_median']<=1 and
        r['reprojection_p95'] is not None and r['reprojection_p95']<=3 for r in rows)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--workspace',type=Path,required=True)
    p.add_argument('--methods',nargs='+',required=True)
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();rows=[];configurations=[]
    for method in a.methods:
        for sharp in (False,True):
            for policy in ('native','fixed','focal','radial'):
                paired=[];exports={}
                for seed in (0,1,2):
                    row=dict(method=method,sharp=sharp,policy=policy,seed=seed,complete=False)
                    folders=[locate(a.workspace,method,policy,sharp,s,seed) for s in ('early','late')]
                    row['runs']=[str(f) for f in folders]
                    reports=[json.loads((f/'result.json').read_text()) if (f/'result.json').exists() else None for f in folders]
                    row['statuses']=[r['status'] if r else 'not-run' for r in reports]
                    if all(r and r['status']=='complete' for r in reports):
                        paths=[f/f"calibration-{r['model_id']}.json" for f,r in zip(folders,reports)]
                        try:
                            values=[load_export(path) for path in paths]
                            exports[seed]=values
                            row.update(compare(*values));row['complete']=True
                            row['support_passed']=all(support_passed(r.get('per_camera_support',[])) for r in reports)
                            row['converged']=all('NO_CONVERGENCE' not in f.with_suffix('.log').read_text().split('Termination :')[-1] for f in folders)
                            row['score']=max(row['max_rotation_degrees']/.5,row['max_center_fraction']/.01)
                        except ValueError as error:row['error']=str(error)
                    paired.append(row);rows.append(row)
                configuration=dict(method=method,sharp=sharp,policy=policy,complete=all(r['complete'] for r in paired))
                if configuration['complete']:
                    cross=[]
                    for seed in (1,2):
                        for window in (0,1):
                            cross.append(compare(exports[0][window],exports[seed][window]))
                    configuration.update(score=max(r['score'] for r in paired),
                        max_rotation_degrees=max(r['max_rotation_degrees'] for r in paired),
                        max_center_fraction=max(r['max_center_fraction'] for r in paired),
                        cross_seed_max_rotation_degrees=max(r['max_rotation_degrees'] for r in cross),
                        cross_seed_max_center_fraction=max(r['max_center_fraction'] for r in cross),
                        passes_training_gates=all(r['passed'] and r['support_passed'] and r['converged'] for r in paired) and all(r['passed'] for r in cross))
                configurations.append(configuration)
    dump(a.output,dict(schema='basketball-alternatives-finalists/v1',pairs=rows,configurations=configurations))
    for r in configurations:
        if r['complete']:print(r['method'],r['sharp'],r['policy'],r['max_rotation_degrees'],r['max_center_fraction'],r['passes_training_gates'])


if __name__=='__main__':main()

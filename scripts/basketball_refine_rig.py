"""Bounded final refinement of a complete candidate; preserve prior attempts."""
import argparse
import json
from pathlib import Path
import time
from basketball_audit import sha256
from basketball_protocol import TRAINING


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--input',required=True,type=Path)
    p.add_argument('--output',required=True,type=Path)
    a=p.parse_args()
    import pycolmap as colmap
    source=json.loads((a.input/'result.json').read_text())
    if source['status']!='candidate-rig':raise ValueError('requires complete candidate')
    a.output.mkdir(exist_ok=False)
    model=colmap.Reconstruction(a.input/'sparse'/str(source['model_id']))
    if sorted(image.camera_id-1 for image in model.images.values() if image.has_pose)!=list(TRAINING):raise ValueError('wrong candidate camera membership')
    config=dict(schema='basketball-final-refinement/v1',source_result_sha256=sha256(a.input/'result.json'),
                adapter_sha256=sha256(__file__),max_iterations=1000,max_seconds=120,
                function_tolerance=1e-8,gradient_tolerance=1e-8,parameter_tolerance=1e-8,loss='SOFT_L1')
    (a.output/'config.json').write_text(json.dumps(config,indent=2)+'\n')
    started=time.monotonic()
    ba=colmap.BundleAdjustmentOptions(refine_focal_length=True,refine_principal_point=True,refine_extra_params=False)
    ba.ceres.loss_function_type=colmap.LossFunctionType.SOFT_L1
    options=ba.ceres.solver_options
    options.num_threads=8;options.max_num_iterations=1000;options.max_solver_time_in_seconds=120
    options.function_tolerance=options.gradient_tolerance=options.parameter_tolerance=1e-8
    colmap.bundle_adjustment(model,options=ba)
    folder=a.output/'sparse'/str(source['model_id']);folder.mkdir(parents=True)
    model.write(folder)
    report=dict(source)
    report.update(config_sha256=sha256(a.output/'config.json'),wall_seconds=time.monotonic()-started,
                  models=[dict(model_id=source['model_id'],cameras=list(TRAINING),points=model.num_points3D(),
                               mean_reprojection_error=model.compute_mean_reprojection_error())])
    (a.output/'result.json').write_text(json.dumps(report,indent=2)+'\n')


if __name__=='__main__':main()

"""Publish the joint FreeTimeGS/RoMa runtime inventories for the D8 final renders (#34).

CPU only. Resolves the native default-keyframe configuration inside the joint
environment, then freezes the GS runtime and RoMa matcher inventories with the
canonical prepare_inventory seams. Grants no execution authority.
"""
import csv
import json
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT/'scripts'))

from vipe_benchmark.files import file_record, read_json, write_json  # noqa: E402
from vipe_benchmark import final_render_inventory, final_render_matcher  # noqa: E402

REPO = Path('/home/auss/git_repos/samaust/Experiments_4DGS')
ENV = REPO/'.local/envs/plan069-joint-native-001'
SITE = ENV/'lib/python3.14/site-packages'
CHECKOUT = REPO/'.local/FreeTimeGsVanilla'
REVIEW = ROOT/'docs/research/vipe-alternatives/plan069-final-render-review-001'
HERE = Path(__file__).resolve().parent
GS = ('torch', 'numpy', 'scipy', 'Pillow', 'torchvision', 'torchmetrics', 'gsplat', 'fused-ssim')


def resolved_native():
    # Same resolution as NativeFreeTimeRuntime._load, without CUDA or model state.
    code = ('import json,sys;from dataclasses import asdict;sys.path.insert(0,sys.argv[1]);'
            'from freetimegs_training import load_training;cfg=load_training(sys.argv[2])[0];'
            'cfg.start_frame,cfg.end_frame=0,50;print(json.dumps(asdict(cfg)))')
    output = subprocess.run([str(ENV/'bin/python'), '-I', '-c', code, str(ROOT/'scripts'), str(CHECKOUT)],
        check=True, capture_output=True, text=True, env=dict(CUDA_VISIBLE_DEVICES='', PATH='/usr/bin:/bin'))
    return json.loads(output.stdout.strip().splitlines()[-1])


def dist_info(name):
    canonical = name.lower().replace('-', '_')
    matches = [path for path in SITE.glob('*.dist-info') if path.name.lower().split('-')[0] == canonical]
    if len(matches) != 1:
        raise ValueError('ambiguous installed distribution: '+name)
    return matches[0]


def recorded_files(names):
    records = {}
    for name in names:
        info = dist_info(name)
        for row in csv.reader((info/'RECORD').read_text().splitlines()):
            if not row:
                continue
            relative = Path(row[0])
            if 'prompts' in relative.parts or '__pycache__' in relative.parts or relative.suffix in ('.pyc', '.pyo'):
                continue
            path = (SITE/relative).resolve()
            if path.is_relative_to(ENV.resolve()) and path.is_file():
                records[str(path)] = file_record(path)
    return list(records.values())


def main():
    start = time.monotonic()
    request = read_json(REVIEW/'request.json')
    scene = read_json(REVIEW/'scene-freeze.json')
    configuration = dict(native=resolved_native(), normalization=request['initializer_contract']['normalization'],
                         scene_scale=scene['historical_reference']['normalization']['scene_scale'])
    write_json(HERE/'resolved-config.json', configuration)
    interpreter = file_record(ENV/'bin/python')
    dependencies = {}
    for name in GS:
        info = dist_info(name)
        version = info.name[len(info.name.split('-')[0])+1:-len('.dist-info')]
        dependencies[name] = dict(version=version, metadata=file_record(info/'METADATA'), record=file_record(info/'RECORD'))
    final_render_inventory.prepare_inventory(checkout=CHECKOUT, environment_prefix=ENV, interpreter=interpreter,
        binaries=dict(gsplat=file_record(SITE/'gsplat/csrc.so'),
                      fused_ssim=file_record(next(SITE.glob('fused_ssim_cuda.cpython-314-*.so')))),
        dependencies=dependencies, resolved_config=file_record(HERE/'resolved-config.json'),
        lpips_checkpoint=file_record(REPO/'.local/cache/torch/hub/checkpoints/alexnet-owt-7be5be79.pth'),
        output=HERE/'gs-runtime.json')
    matcher_names = sorted((final_render_matcher.DEPENDENCIES-{'opencv-python'}) | {'opencv-python-headless'})
    final_render_matcher.prepare_inventory(checkout=REPO/'.local/RoMa-edgs', weights=REPO/'.local/weights/roma-edgs',
        environment_prefix=ENV, interpreter=interpreter, dependencies=recorded_files(matcher_names),
        output=HERE/'matcher-runtime.json')
    write_json(HERE/'preparation-receipt.json', dict(schema='plan069-final-render-runtime-preparation/v1',
        status='prepared', gs_runtime=file_record(HERE/'gs-runtime.json'),
        matcher_runtime=file_record(HERE/'matcher-runtime.json'), elapsed_seconds=time.monotonic()-start))


if __name__ == '__main__':
    main()

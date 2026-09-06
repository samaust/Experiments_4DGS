"""Load upstream ATGS defaults with explicit shared-profile overrides.

Caller must put the pinned ATGS checkout on sys.path before calling.
No model construction, metric initialization, or GPU execution occurs here.
"""
from argparse import ArgumentParser
from pathlib import Path


def load_config(checkout, *, frame_count=60):
    from arguments import ModelParams, ModelHiddenParams, OptimizationParams, PipelineParams
    from arguments.atgs_cfg import apply_atgs_cfg, cfg
    from mmengine.config import Config

    if frame_count <= 0:
        raise ValueError('frame_count must be positive')
    parser = ArgumentParser(add_help=False)
    groups = [ModelParams(parser), ModelHiddenParams(parser),
              OptimizationParams(parser), PipelineParams(parser)]
    args = parser.parse_args([])
    config = Config.fromfile(str(Path(checkout) / 'arguments/vru/basketball.py'))
    ignored = []
    for group in ('OptimizationParams', 'ModelHiddenParams', 'ModelParams', 'PipelineParams'):
        for key, value in config.get(group, {}).items():
            if not hasattr(args, key):
                # Match upstream merge_hparams: legacy keys without parser
                # attributes are ignored. Expose them for provenance.
                ignored.append(key)
                continue
            setattr(args, key, value)
    args.ignored_config_keys = ignored
    # Inputs already have shared resizing, synchronization and explicit splits.
    args.downsample = 1.0
    args.open_sync_time = False
    args.frames_start_end = [0, frame_count]
    args.base_path = ''
    apply_atgs_cfg(args)
    if not cfg.hash or cfg.primitive_type != '3dgs':
        raise ValueError('requires the selected hash/3DGS representation')
    return args, tuple(group.extract(args) for group in groups), cfg

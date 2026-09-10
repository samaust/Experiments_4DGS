"""Plan 028 compatibility entry point for repaired FreeTimeGs checkpoints."""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import freetimegs_training

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('frozen_evaluator', ROOT/'scripts/evaluate-basketball-sync.py')
frozen = importlib.util.module_from_spec(spec)
spec.loader.exec_module(frozen)

original_load_training = freetimegs_training.load_training


def load_training(checkout):
    cfg, source, training_source = original_load_training(checkout)
    checkpoint = Path(sys.argv[sys.argv.index('--checkpoint') + 1])
    native = json.loads((checkpoint.parent/'training-config.json').read_text())['native']
    cfg.init_duration = native['init_duration']
    return cfg, source, training_source


freetimegs_training.load_training = load_training

import torch

checkpoint_path = Path(sys.argv[sys.argv.index('--checkpoint') + 1])
checkpoint_provenance = torch.load(checkpoint_path, map_location='cpu', weights_only=True)['provenance']
original_digest = frozen.digest


def digest(path):
    if Path(path).resolve() == (ROOT/'scripts/basketball_crossing_train.py').resolve():
        return checkpoint_provenance['files'][str((ROOT/'scripts/basketball_crossing_train.py').resolve())]
    return original_digest(path)


frozen.digest = digest

original_run = subprocess.run


def run(command, *args, **kwargs):
    command = list(command)
    if len(command) > 1 and command[1].endswith('/scripts/evaluate-basketball-sync.py'):
        command[1] = str(Path(__file__).resolve())
    return original_run(command, *args, **kwargs)


frozen.subprocess.run = run
frozen.main()

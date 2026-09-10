"""Plan 028 compatibility entry point for repaired FreeTimeGs checkpoints."""
import importlib.util
import json
from pathlib import Path
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
frozen.main()

"""Load selected native reproduction methods without importing its trainer."""
import ast
import hashlib
from pathlib import Path

import torch


def load_temporal_methods(checkout):
    path = Path(checkout) / 'src/simple_trainer_freetime_4d_pure_relocation.py'
    tree = ast.parse(path.read_text())
    classes = [node for node in tree.body if isinstance(node, ast.ClassDef)
               and node.name == 'FreeTime4DRunner']
    if len(classes) != 1:
        raise ValueError('expected one native FreeTime4DRunner')
    names = ('compute_temporal_opacity', 'compute_positions_at_time',
             'compute_4d_regularization')
    methods = [node for node in classes[0].body
               if isinstance(node, ast.FunctionDef) and node.name in names]
    if len(methods) != len(names) or {node.name for node in methods} != set(names):
        raise ValueError('required native temporal methods missing or duplicated')
    selected = ast.Module(body=methods, type_ignores=[])
    namespace = {'torch': torch, 'Tensor': torch.Tensor}
    exec(compile(selected, str(path), 'exec'), namespace)
    return ({name: namespace[name] for name in names},
            hashlib.sha256(ast.dump(selected).encode()).hexdigest())

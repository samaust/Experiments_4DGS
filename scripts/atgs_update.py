"""Load only pinned ATGS accumulation helpers, avoiding training import effects."""
import ast
import hashlib
from pathlib import Path

import torch


HELPERS = ('optimizer_parameters', 'sanitize_accumulated_gradients',
           'average_accumulated_gradients', 'clip_accumulated_gradients',
           'step_accumulated_gradients')


def load_update_helpers(checkout):
    path = Path(checkout) / 'train_long.py'
    source = path.read_text()
    functions = {node.name: node for node in ast.parse(source).body
                 if isinstance(node, ast.FunctionDef) and node.name in HELPERS}
    if set(functions) != set(HELPERS):
        raise ValueError('required upstream accumulation helpers missing')
    selected = ast.Module(body=[functions[name] for name in HELPERS], type_ignores=[])
    namespace = {'torch': torch}
    exec(compile(selected, str(path), 'exec'), namespace)
    return namespace, hashlib.sha256(ast.dump(selected).encode()).hexdigest()

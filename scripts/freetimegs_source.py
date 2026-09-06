"""Load selected native reproduction methods without importing its trainer."""
import ast
import hashlib
import math
from pathlib import Path

import torch


def load_initializer(checkout):
    """Extract the native initializer and its KNN/SH helpers, without trainer imports."""
    from sklearn.neighbors import NearestNeighbors
    checkout = Path(checkout)
    selected = []
    for relative, names in (
        ('src/utils.py', ('knn', 'rgb_to_sh')),
        ('src/simple_trainer_freetime_4d_pure_relocation.py',
         ('create_splats_with_optimizers_4d',)),
    ):
        tree = ast.parse((checkout / relative).read_text())
        functions = [node for node in tree.body
                     if isinstance(node, ast.FunctionDef) and node.name in names]
        if len(functions) != len(names) or {node.name for node in functions} != set(names):
            raise ValueError('required native initialization functions missing or duplicated')
        selected.extend(functions)
    module = ast.Module(body=[ast.ImportFrom(module='__future__',
                        names=[ast.alias(name='annotations')], level=0), *selected], type_ignores=[])
    ast.fix_missing_locations(module)
    namespace = dict(torch=torch, math=math, NearestNeighbors=NearestNeighbors)
    exec(compile(module, str(checkout / 'src/native-initializer'), 'exec'), namespace)
    return (namespace['create_splats_with_optimizers_4d'],
            hashlib.sha256(ast.dump(module).encode()).hexdigest())


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

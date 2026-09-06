#!/usr/bin/env python3
"""CPU-only check of ATGS config inheritance and explicit CLI precedence."""
import argparse
import ast
import hashlib
import json
from pathlib import Path
import sys


def literal_config(path):
    def value_of(node):
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Mult):
            return value_of(node.left) * value_of(node.right)
        return ast.literal_eval(node)
    result = {}
    for statement in ast.parse(path.read_text()).body:
        if isinstance(statement, ast.Assign):
            value = statement.value
            if isinstance(value, ast.Call) and isinstance(value.func, ast.Name) and value.func.id == 'dict':
                result[statement.targets[0].id] = {item.arg: value_of(item.value)
                                                  for item in value.keywords}
    return result


def verify(checkout):
    from mmengine.config import Config
    base = checkout/'arguments/vru/default.py'
    selected = checkout/'arguments/vru/basketball.py'
    expected = literal_config(base)
    for group, values in literal_config(selected).items():
        expected.setdefault(group, {}).update(values)
    config = Config.fromfile(str(selected))
    assert config.to_dict() == expected, 'config inheritance changed'
    helper = checkout/'utils/general_utils.py'
    function = next(node for node in ast.parse(helper.read_text()).body
                    if isinstance(node, ast.FunctionDef) and node.name == 'merge_hparams')
    namespace = {}
    exec(compile(ast.Module(body=[function], type_ignores=[]), str(helper), 'exec'), namespace)
    args = argparse.Namespace(**{k: None for values in expected.values() for k in values})
    args.iterations = 123
    previous = sys.argv
    try:
        sys.argv = ['verify-atgs-config', '--iterations', '123']
        merged = namespace['merge_hparams'](args, config)
    finally:
        sys.argv = previous
    assert merged.iterations == 123, 'explicit CLI override lost'
    assert merged.hash is True and merged.levels == 13 and merged.downsample == 2
    assert merged.llffhold == 10 and merged.primitive_type == '3dgs'
    for name in ('train_long.py', 'render.py'):
        source = (checkout/name).read_text()
        assert 'from mmengine.config import Config' in source
        assert 'mmcv.Config.fromfile' not in source
    return dict(status='passed', config=expected,
        checks=['all inherited config values', 'explicit CLI iteration precedence',
                'hash/3dgs selection', 'both entry points patched'],
        sha256={str(path): hashlib.sha256(path.read_bytes()).hexdigest()
                for path in (base, selected, helper, checkout/'train_long.py', checkout/'render.py')},
        note='CPU config check only; does not validate native CUDA extensions or training.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--checkout', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error('refusing to overwrite output')
    report = verify(args.checkout.resolve())
    with args.output.open('x') as stream:
        stream.write(json.dumps(report, indent=2)+'\n')
    print(json.dumps({k: v for k, v in report.items() if k not in ('config', 'sha256')}, indent=2))


if __name__ == '__main__':
    main()

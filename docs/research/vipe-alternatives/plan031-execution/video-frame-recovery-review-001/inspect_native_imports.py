"""Read-only static native import traversal; does not import executable models."""
import ast
import hashlib
import json
from pathlib import Path
import sys
import time

started=time.perf_counter()
source=Path(sys.argv[1]).resolve()
queue=['video_depth_anything.video_depth','utils.util']
seen={}; externals=set()
def path_for(module):
    path=source.joinpath(*module.split('.'))
    for candidate in (path.with_suffix('.py'),path/'__init__.py'):
        if candidate.is_file():return candidate
    return None
while queue:
    module=queue.pop()
    if module in seen:continue
    path=path_for(module)
    if path is None:continue
    data=path.read_bytes(); tree=ast.parse(data)
    seen[module]=dict(path=str(path),sha256=hashlib.sha256(data).hexdigest(),bytes=len(data))
    parents=module.split('.') if path.name=='__init__.py' else module.split('.')[:-1]
    for node in ast.walk(tree):
        names=[]
        if isinstance(node,ast.Import):names=[alias.name for alias in node.names]
        elif isinstance(node,ast.ImportFrom):
            base=parents[:len(parents)-node.level+1] if node.level else []
            if node.module:base+=node.module.split('.')
            names=['.'.join(base)]+['.'.join(base+[alias.name]) for alias in node.names if alias.name!='*']
        for name in names:
            if path_for(name):queue.append(name)
            elif name:externals.add(name)
            # Importing a package executes its initializer.
            for count in range(1,len(name.split('.'))):
                package='.'.join(name.split('.')[:count])
                if path_for(package):queue.append(package)
assert not any(name=='decord' or name.startswith('decord.') for name in externals)
assert 'utils.dc_utils' not in seen
print(json.dumps(dict(schema='plan069-native-static-import-evidence/v1',entrypoints=['video_depth_anything.video_depth','utils.util'],local_modules=seen,external_import_names=sorted(externals),decord_reachable=False,cli_decoder_reachable=False,limitations='Static imports include optional branches; no executable source or binary was imported. Dynamic import behavior is not certified.',elapsed_seconds=time.perf_counter()-started),indent=2))

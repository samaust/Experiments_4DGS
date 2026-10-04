"""Verify only installed notice metadata; never import runtime packages."""
import hashlib
import json
from pathlib import Path
import time

ROOT = Path(__file__).resolve().parent
RUN = Path('/home/auss/git_repos/samaust/Experiments_4DGS/.local/vipe-alternatives/plan031-20260913T032700Z')


def record(path):
    path = path.resolve(strict=True)
    if 'prompts' in path.parts:
        raise ValueError('Forbidden path')
    data = path.read_bytes()
    return {'path': str(path), 'sha256': hashlib.sha256(data).hexdigest(), 'bytes': len(data)}


def main():
    started = time.monotonic()
    inventory_path = RUN / 'jobs/plan069-D9-setup-recovery-002/runtime/inventory.json'
    inventory = json.loads(inventory_path.read_text())
    rows = []
    for package in inventory['packages']:
        notices = []
        for item in package['files']:
            if Path(item['path']).name.lower().startswith(('license', 'licence', 'copying', 'notice')):
                actual = record(Path(item['path']))
                if actual != item:
                    raise ValueError('Installed notice changed: ' + item['path'])
                notices.append(actual)
        rows.append({'name': package['name'], 'version': package['version'], 'installed_notices': notices})
    if len(rows) != 48 or len({row['name'].lower() for row in rows}) != 48:
        raise ValueError('Wrong installed package closure')
    result = {'schema': 'plan069-D9-installed-license-inspection/v1',
              'candidate': 'D9', 'inventory': record(inventory_path), 'packages': rows,
              'package_count': 48, 'notice_count': sum(len(row['installed_notices']) for row in rows),
              'model_imports': False, 'gpu_operations': False,
              'native_runtime_qualified': False, 'commercial_admission_granted': False,
              'elapsed_seconds': time.monotonic() - started}
    output = ROOT / 'inspection.json'
    with output.open('x') as stream:
        json.dump(result, stream, indent=2)
        stream.write('\n')
    print(json.dumps({'package_count': 48, 'notice_count': result['notice_count'],
                      'elapsed_seconds': result['elapsed_seconds']}))


if __name__ == '__main__':
    main()

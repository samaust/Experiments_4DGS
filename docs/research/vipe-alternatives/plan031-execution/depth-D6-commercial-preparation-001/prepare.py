"""Prepare D6 commercial review evidence; never grants inference permission."""
import argparse
import hashlib
import json
from pathlib import Path
import time


def binding(path):
    data = path.read_bytes()
    return dict(path=str(path.resolve()), sha256=hashlib.sha256(data).hexdigest(), bytes=len(data))


def load_binding(record):
    path = Path(record['path'])
    assert 'prompts' not in path.resolve().parts
    assert binding(path) == record
    return json.loads(path.read_text())


def package_snapshot(manifest):
    return {p['name'].lower().replace('_', '-'): dict(version=p['version'], license=p.get('license'), classifiers=p.get('classifiers')) for p in manifest['packages']}


def file_snapshot(manifest):
    # Prefix normalization permits distinct environments; byte changes remain visible.
    result = {}
    for f in manifest['files']:
        path = f['path']
        key = path.split('/site-packages/', 1)[-1]
        assert key not in result or result[key] == (f['sha256'], f['bytes']), key
        result[key] = (f['sha256'], f['bytes'])
    return result


def main():
    started = time.monotonic()
    parser = argparse.ArgumentParser()
    parser.add_argument('--checkout', type=Path, required=True)
    parser.add_argument('--manifest', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    assert not args.output.exists(), 'immutable output already exists'
    base = args.checkout / 'docs/research/vipe-alternatives/plan031-execution'
    assessment_path = base / 'depth-D5-commercial-assessment-001.json'
    assessment = json.loads(assessment_path.read_text())
    config_path = args.checkout / 'configs/vipe-alternatives/depth-extension-v1.json'
    config = json.loads(config_path.read_text())['candidates']['D6']
    recipe_base = args.checkout / 'docs/specs/plan031-execution/moge-runtime-recipes-001'
    d5recipe = json.loads((recipe_base/'D5-runtime-environment.json').read_text())
    d6recipe = json.loads((recipe_base/'D6-runtime-environment.json').read_text())
    differences = [k for k in set(d5recipe)|set(d6recipe) if d5recipe.get(k) != d6recipe.get(k)]
    assert sorted(differences) == ['candidate','flex_cache_path']
    assert config['code']['revision'] == assessment['source_revision']
    draft = dict(schema='plan069-D6-commercial-preparation/v1', status='pending', candidate='D6', source_revision=config['code']['revision'], weights_revision=config['weights']['revision'], code='pending', weights='pending', dependencies='pending', inference_outputs='pending', config=binding(config_path), D5_assessment=binding(assessment_path), recipes=dict(D5=binding(recipe_base/'D5-runtime-environment.json'),D6=binding(recipe_base/'D6-runtime-environment.json')), recipe_differences=differences, blockers=['Verify actual D6 setup/source/license and pinned weight card/license bytes','Review exact D6 installed dependency closure, notices and supplemental primary terms','Independent reviewer must approve a separately assembled actual D6 assessment'], scope='Owned workstation local commercial inference and generated depth map/image use; no hosting or redistribution; FFmpeg publication requires separate exact host closure')
    if args.manifest:
        actual = json.loads(args.manifest.read_text())
        assert actual['record_kind'] == 'actual' and actual['candidate'] == 'D6'
        assert actual['schema'] == 'plan069-depth-installed-dependencies/v1'
        assert actual['source_revision'] == config['code']['revision']
        assert actual['model_imports'] is False and actual['gpu_operations'] is False
        load_binding(actual['setup'])
        load_binding(actual['inventory'])
        previous = load_binding(assessment['dependency_manifest'])
        old, new = package_snapshot(previous), package_snapshot(actual)
        oldfiles, newfiles = file_snapshot(previous), file_snapshot(actual)
        draft['dependency_manifest'] = binding(args.manifest)
        draft['closure_comparison'] = dict(packages_changed=sorted(k for k in old.keys()|new.keys() if old.get(k)!=new.get(k)), installed_files_changed=sorted(k for k in oldfiles.keys()|newfiles.keys() if oldfiles.get(k)!=newfiles.get(k)), D5_packages=len(old), D6_packages=len(new), exact_permission_reuse=False)
    draft['elapsed_seconds'] = time.monotonic()-started
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(draft,indent=2)+'\n')
    print(json.dumps(dict(status=draft['status'], elapsed_seconds=draft['elapsed_seconds'])))


if __name__ == '__main__':
    main()

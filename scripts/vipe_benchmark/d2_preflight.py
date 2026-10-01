"""CPU-only binding of the approved D2 slot to the completed E5 runtime.

This receipt establishes reusable local assets and installed runtime lineage. It
does not assert commercial dependency clearance or a passing GPU smoke test.
"""

from pathlib import Path

from .backends import AssetBundle
from .depth_admission import D2_SPEC, INVENTORY, PROFILES
from .files import file_record, object_hash, read_json, verify_record, write_json


SCHEMA = 'plan069-d2-cpu-preflight/v1'


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def qualify(proposal, e5_result, output):
    """Write immutable CPU evidence; never import the model or initialize CUDA."""
    output = Path(output)
    _require(not output.exists(), 'D2 CPU preflight output already exists')
    _require(proposal.get('schema') == 'plan069-depth-execution-proposal/v1' and
             proposal.get('status') == 'REVIEW' and proposal.get('candidate') == 'D2' and
             proposal.get('candidate_config') == D2_SPEC and
             proposal.get('max_attempts') == 1,
             'D2 proposal differs from the frozen one-attempt source and profile')
    reviewed_assets = verify_record(proposal['required_assets'])
    reviewed_profiles = verify_record(proposal['profile_inventory'])
    _require(all(reviewed_assets[key] == file_record(INVENTORY)[key] and
                 reviewed_profiles[key] == file_record(PROFILES)[key]
                 for key in ('sha256', 'bytes')),
             'D2 reviewed inventories differ from local frozen copies')
    expected = read_json(INVENTORY)['candidates']['D2']['files']
    _require(len(expected) == 1 and expected[0]['repository'] == 'da3' and
             expected[0]['path'] == 'model.safetensors',
             'D2 required-only asset inventory changed')
    runtime_result = read_json(verify_record(e5_result)['path'])
    _require(runtime_result.get('status') == 'complete' and
             runtime_result.get('environment') == 'E5',
             'completed E5 runtime receipt required')
    assets_record = verify_record(runtime_result['assets'])
    assets = read_json(assets_record['path'])
    bundle = AssetBundle('D2', assets)
    _require(bundle.records['da3_source']['revision'] == D2_SPEC['code']['revision'] and
             bundle.records['da3_snapshot']['revision'] == D2_SPEC['weights']['revision'],
             'D2 source or checkpoint revision changed')
    checkpoint = next(row for row in bundle.records['da3_snapshot']['files']
                      if Path(row['path']).name == 'model.safetensors')
    _require(checkpoint['bytes'] == expected[0]['bytes'] and
             checkpoint['sha256'] == expected[0]['lfs_sha256'],
             'D2 checkpoint differs from reviewed LFS object')
    _require(any(Path(row['path']).name == 'LICENSE' for row in
                 bundle.records['da3_source']['files']),
             'pinned DA3 source license is absent')
    runtime = runtime_result['runtime']
    interpreter = Path(runtime['python'])
    _require(interpreter.is_file() and interpreter.is_absolute() and
             interpreter.parent.parent.parent == Path(e5_result['path']).parent,
             'E5 interpreter must belong to the completed setup')
    for key in ('inventory', 'imports', 'dependency_lock', 'build_inputs'):
        verify_record(runtime[key])
    imports = read_json(runtime['imports']['path'])
    _require(imports.get('status') == 'complete',
             'native DA3 imports did not qualify')
    result = dict(schema=SCHEMA, status='cpu_preflight_passed', candidate='D2',
        proposal_sha256=object_hash(proposal), e5_result=e5_result,
        source_revision=D2_SPEC['code']['revision'],
        weights_revision=D2_SPEC['weights']['revision'],
        source_license=next(row for row in bundle.records['da3_source']['files']
                            if Path(row['path']).name == 'LICENSE'),
        checkpoint=checkpoint, assets=assets_record,
        runtime=runtime, remaining_gates=[
            'independent source review', 'installed dependency commercial assessment',
            'GPU runtime smoke', 'fresh ledger-bound admission'])
    output.mkdir(parents=True, exist_ok=False)
    write_json(output / 'result.json', result)
    return result

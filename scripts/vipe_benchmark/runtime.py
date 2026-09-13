"""Pinned runtime setup requests and explicit asset/dependency inventories."""
import json
import hashlib
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess
import sys
import tarfile
import time
import urllib.request
import uuid

from .config import ROOT
from .files import digest, file_record, read_json, safe_path, verify_record, write_json

TARGETS = {
    'E0': dict(python='3.14', torch='2.13.0+cu130', torchvision='0.28.0+cu130'),
    'E1': dict(python='3.11', torch='2.5.1+cu124', torchvision='0.20.1+cu124', numpy='1.26.4'),
    'E2': dict(python='3.11', torch='2.5.1+cu124', torchvision='0.20.1+cu124', numpy='1.26.4'),
    'E3': dict(python='3.12', torch='2.10.0+cu128', torchvision='0.25.0+cu128', numpy='1.26.4'),
    'E4': dict(python='3.11', torch='2.5.1+cu124', torchvision='0.20.1+cu124', numpy='2.1.3'),
    'E5': dict(python='3.11', torch='2.5.1+cu124', torchvision='0.20.1+cu124', numpy='1.26.4'),
    'E6': dict(python='3.10', torch='2.0.1+cu118', torchvision='0.15.2+cu118', numpy='1.23.1'),
    'E7': dict(python='3.11', torch='2.5.1+cu124', torchvision='0.20.1+cu124', numpy='1.26.4'),
    'E8': dict(python='3.14', torch='2.13.0+cu130', torchvision='0.28.0+cu130'),
}
ENVIRONMENTS = {'S0': 'E0', 'S1': 'E1', 'S2': 'E2', 'S3': 'E3', 'S4': 'E2',
                'D0': 'E0', 'D1': 'E4', 'D2': 'E5', 'D3': 'E6', 'D4': 'E7'}
SOURCE_REPOS = {
    'samtrack_source': 'z-x-yang/Segment-and-Track-Anything', 'aot_source': 'yoxu515/aot-benchmark',
    'sam_source': 'facebookresearch/segment-anything', 'grounding_source': 'IDEA-Research/GroundingDINO',
    'sam2_source': 'facebookresearch/sam2', 'sam3_source': 'facebookresearch/sam3',
    'unidepth_source': 'lpiccinelli-eth/UniDepth', 'da3_source': 'ByteDance-Seed/Depth-Anything-3',
    'metric3d_source': 'YvanYin/Metric3D', 'depth_pro_source': 'apple/ml-depth-pro',
}
REMOTE_ASSETS = {
    'sam2_checkpoint': ('facebook/sam2.1-hiera-large', '665f8e2ad61cf5f53d65644ff27c8ee525124610', ['sam2.1_hiera_large.pt']),
    'sam3_checkpoint': ('facebook/sam3', '3c879f39826c281e95690f02c7821c4de09afae7', ['sam3.pt']),
    'rtdetr_snapshot': ('PekingU/rtdetr_v2_r50vd', '282494075698cab9faa1096ae26856890030c817', ['model.safetensors']),
    'da3_snapshot': ('depth-anything/DA3METRIC-LARGE', '4010e39f3634a45bc60553321fb49fb760bd594e', ['model.safetensors']),
    'metric3d_checkpoint': ('JUGGHM/Metric3D', '80d2d1410afb4b23cd9d18c6be9144483d4b70b6', ['metric_depth_vit_large_800k.pth']),
    'depth_pro_checkpoint': ('apple/DepthPro', 'ccd1350a774eb2248bcdfb3be430e38f1d3087ef', ['depth_pro.pt']),
}
GROUNDING_WEIGHT_PIN = ('ShilongLiu/GroundingDINO', 'a94c9b567a2a374598f05c584e96798a170c56fb')


def tree_record(path, revision):
    path = safe_path(path).absolute()
    files = []
    for base, dirs, names in os.walk(path):
        dirs[:] = sorted(d for d in dirs if d not in ('prompts', '.git', '__pycache__', '.venv') and
                         not (Path(base) / d).is_symlink())
        for name in sorted(names):
            if name == 'prompts' or name.endswith(('.pyc', '.pyo')):
                continue
            source = safe_path(Path(base) / name)
            # Preserve lexical HF snapshot membership while verifying blob bytes.
            record = file_record(source)
            record['path'] = str(source.absolute())
            record['mode'] = stat.S_IMODE(source.stat().st_mode)
            if source.is_symlink():
                record['symlink_target'] = os.readlink(source)
            files.append(record)
    if not files:
        raise ValueError('empty source/snapshot inventory')
    return dict(path=str(path), revision=revision, files=files)


def historical_assets():
    prior_path = ROOT / '.local/calibration/basketball-v1/no-camera5-priors/result.json'
    prior = read_json(prior_path)
    # The input audit is authoritative; do not infer a neighboring checkout.
    source = Path(read_json(ROOT / '.local/calibration/basketball-v1/input-audit.json')['vipe']['path'])
    revision = subprocess.check_output(['git', '-C', str(source), 'rev-parse', 'HEAD'], text=True).strip()
    if revision != prior['vipe_revision'] or subprocess.check_output(
            ['git', '-C', str(source), 'status', '--porcelain', '--untracked-files=no'], text=True).strip():
        raise ValueError('historical ViPE source pin or tracked state changed')
    sources = [file_record(source / k, v) for k, v in prior['source_sha256'].items()]
    weights = {Path(p).name: file_record(p, h) for p, h in prior['weight_sha256'].items()}
    bert_path = next(Path(p).parent for p in prior['weight_sha256'] if '/models--bert-base-uncased/' in p)
    unidepth_path = next(Path(p).parent for p in prior['weight_sha256'] if '/models--lpiccinelli--unidepth-v2-vitl14/' in p)
    def snapshot(path):
        files = []
        for p, h in prior['weight_sha256'].items():
            if Path(p).parent == path:
                r = file_record(p, h)
                r['path'] = p
                files.append(r)
        return dict(path=str(path), revision=path.name, files=files)
    return dict(vipe_source=dict(path=str(source), revision=revision, files=sources),
        sam_checkpoint=weights['sam_vit_b_01ec64.pth'], aot_checkpoint=weights['R50_DeAOTL_PRE_YTB_DAV.pth'],
        grounding_checkpoint=weights['groundingdino_swint_ogc.pth'],
        bert_snapshot=snapshot(bert_path), unidepth_snapshot=snapshot(unidepth_path)), file_record(prior_path)


def _file_identity(path):
    if not path.exists():
        return None
    value = path.stat()
    return dict(device=value.st_dev, inode=value.st_ino, size=value.st_size, mtime_ns=value.st_mtime_ns)


def download(url, path, transfer_dir, *, limit, run_root=None, artifact_limit=None, use_hf_auth=False):
    from .budgets import download_lock
    run_root = safe_path(run_root or Path(transfer_dir).parent).absolute()
    with download_lock(run_root):
        return _download(url, path, transfer_dir, limit=limit, run_root=run_root,
                         artifact_limit=artifact_limit, use_hf_auth=use_hf_auth)


def _download(url, path, transfer_dir, *, limit, run_root, artifact_limit, use_hf_auth=False):
    """One HTTPS operation, with counted bytes and no automatic network retries."""
    from .budgets import budget_snapshot, download_remaining, record_download_progress
    path = safe_path(path).absolute()
    transfer_dir = safe_path(transfer_dir).absolute()
    run_root = safe_path(run_root or transfer_dir.parent).absolute()
    if not path.is_relative_to(run_root) or not transfer_dir.is_relative_to(run_root):
        raise ValueError('download output and transfer receipts must belong to the declared run')
    if not str(url).startswith('https://'):
        raise ValueError('only explicit HTTPS downloads are admitted')
    partial = path.with_suffix(path.suffix + '.partial')
    if path.exists() or path.is_symlink() or partial.exists() or partial.is_symlink():
        raise ValueError('asset output exists without reuse provenance')
    if artifact_limit is None:
        artifact_limit = int(read_json(ROOT / 'configs/vipe-alternatives/benchmark-v1.json')
                             ['new_artifact_disk_gib_limit'] * 2**30)
    path.parent.mkdir(parents=True, exist_ok=True)
    transfer_dir.mkdir(parents=True, exist_ok=True)
    transfer_id = uuid.uuid4().hex
    initial = budget_snapshot(run_root)
    def remaining():
        return download_remaining(run_root, limit, active_output=path, bytes_received=received,
                                  artifact_limit=artifact_limit)
    received, start, error = 0, time.monotonic(), None
    authentication_used = False
    partial_identity = None
    pending_read_upper_bound = 0
    write_json(transfer_dir / f'active-{transfer_id}.json', dict(transfer_id=transfer_id,
        output=str(path), partial=str(partial), url=url))
    try:
        if remaining() <= 0:
            raise ValueError('new download or artifact allocation exhausted before opening URL')
        request, open_request = url, urllib.request.urlopen
        if use_hf_auth:
            from .hf_auth import build_hf_request, build_hf_opener
            request, authentication_used = build_hf_request(url)
            open_request = build_hf_opener().open
        with partial.open('xb') as stream, open_request(request, timeout=60) as response:
            if not response.geturl().startswith('https://'):
                raise ValueError('download redirected outside HTTPS')
            declared = response.headers.get('Content-Length')
            declared = int(declared) if declared is not None else None
            if declared is not None and declared < 0:
                raise ValueError('invalid download Content-Length')
            while declared is None or received < declared:
                available = remaining()
                if available <= 0:
                    raise ValueError('new download or artifact allocation exhausted before next read')
                count = min(2**20, available, declared - received if declared is not None else 2**20)
                # Persist the permitted read before entering the transport. A
                # killed process or an exception can hide internally consumed
                # body bytes; its reservation must survive either outcome.
                pending_read_upper_bound = received + count
                record_download_progress(run_root, transfer_id, path, received, count)
                block = response.read(count)
                if not block:
                    record_download_progress(run_root, transfer_id, path, received, 0)
                    pending_read_upper_bound = 0
                    if declared is not None and received != declared:
                        raise ValueError('download ended before declared Content-Length')
                    break
                received += len(block)
                if len(block) > count:
                    raise ValueError('transport returned more bytes than the admitted read')
                stream.write(block)
                stream.flush()
                record_download_progress(run_root, transfer_id, path, received, 0)
                pending_read_upper_bound = 0
            os.fsync(stream.fileno())
        partial_identity = _file_identity(partial)
        partial.rename(path)
    except BaseException as exc:
        error = f'{type(exc).__name__}: {exc}'
        raise
    finally:
        write_json(transfer_dir / f'transfer-{transfer_id}.json', dict(transfer_id=transfer_id, url=url,
            output=str(path), partial=str(partial), partial_identity=partial_identity or _file_identity(partial),
            output_identity=_file_identity(path), bytes_received=received,
            received_or_reserved_upper_bound=max(received, pending_read_upper_bound),
            wall_seconds=time.monotonic() - start, error=error, budget_before=initial,
            existing_huggingface_auth_used=authentication_used))
    return file_record(path)


def extract_source(archive, output, revision):
    output = safe_path(output)
    output.mkdir(parents=True, exist_ok=False)
    if not isinstance(revision, str) or not re.fullmatch('[0-9a-f]{40}', revision):
        raise ValueError('source archive requires an exact commit revision')
    members, aliases, archive_root = {}, {}, None
    with tarfile.open(safe_path(archive)) as source:
        # Validate all member metadata before reading any file payload. Links
        # may precede their target in a git archive; none is created this pass.
        for member in source:
            name = member.name.rstrip('/') if member.isdir() else member.name
            parts = name.split('/')
            if (not name or Path(name).is_absolute() or '\\' in name or '\x00' in name or
                    any(part in ('', '.', '..') for part in parts)):
                raise ValueError('unsafe source archive member')
            if not parts[0].endswith('-' + revision):
                raise ValueError('source archive does not identify the exact pinned revision')
            if archive_root is None:
                archive_root = parts[0]
            if parts[0] != archive_root:
                raise ValueError('source archive contains more than one pinned root')
            if member.islnk() or member.mode & 0o7000:
                raise ValueError('unsafe source archive member')
            if not (member.isdir() or member.isfile() or member.issym()):
                raise ValueError('source archive contains a special file')
            if 'prompts' in parts:
                if member.issym():
                    raise ValueError('source archive aliases cannot access prompts')
                continue
            relative = Path(*parts[1:])
            if relative in members:
                raise ValueError('source archive contains a path collision')
            if len(parts) == 1 and not member.isdir():
                raise ValueError('source archive root must be a directory')
            members[relative] = member
            if member.issym():
                text = member.linkname
                link_parts = text.split('/')
                if (not text or Path(text).is_absolute() or '\\' in text or '\x00' in text or
                        re.match(r'^[A-Za-z]:', text) or 'prompts' in link_parts):
                    raise ValueError('unsafe source archive alias target')
                target_parts = list(relative.parent.parts)
                for part in link_parts:
                    if part == '..':
                        if not target_parts:
                            raise ValueError('source archive alias escapes its pinned root')
                        target_parts.pop()
                    elif part not in ('', '.'):
                        target_parts.append(part)
                aliases[relative] = Path(*target_parts)

        for relative in members:
            for parent in relative.parents:
                if parent in members and not members[parent].isdir():
                    raise ValueError('source archive contains a path collision')
        for target in aliases.values():
            if target not in members or not members[target].isfile():
                raise ValueError('source archive alias must target a regular member directly')

        for relative, member in members.items():
            target = safe_path(output / relative)
            if member.isdir():
                target.mkdir(parents=True, exist_ok=True)
            elif member.isfile():
                target.parent.mkdir(parents=True, exist_ok=True)
                with source.extractfile(member) as inp, target.open('xb') as out:
                    shutil.copyfileobj(inp, out)
                target.chmod(member.mode & 0o777)

        for relative, target_relative in aliases.items():
            target = safe_path(output / target_relative)
            if target.is_symlink() or not target.is_file() or not target.resolve().is_relative_to(output.resolve()):
                raise ValueError('source archive alias target changed during extraction')
            link = safe_path(output / relative)
            link.parent.mkdir(parents=True, exist_ok=True)
            link.symlink_to(members[relative].linkname, target_is_directory=False)
    record = tree_record(output, revision)
    record['archive_root'] = archive_root
    record['archive_symlinks'] = [dict(member=members[path].name, target=members[path].linkname,
                                     target_member=members[target].name) for path, target in aliases.items()]
    return record


def acquire_assets(request, output, config):
    from .backends import REQUIRED_ASSETS, SOURCE_PINS
    output = Path(output)
    assets = dict(request['historical_assets'])
    for name, record in request.get('reuse_assets', {}).items():
        for item in record.get('files', [record]):
            verify_record(item)
        assets[name] = record
    needed = sorted({name for c in request['components'] for name in REQUIRED_ASSETS[c]})
    transfer_dir = Path(request['transfer_dir'])
    for name in needed:
        print(f'[setup] asset {name}: start', flush=True)
        if name in assets or name in ('grounding_config', 'bpe_vocabulary'):
            if name in assets:
                for item in assets[name].get('files', [assets[name]]):
                    verify_record(item)
                print(f'[setup] asset {name}: verified reuse', flush=True)
            continue
        if name in SOURCE_REPOS:
            revision = SOURCE_PINS[name]
            archive = output / 'archives' / f'{name}-{revision}.tar.gz'
            receipt = download(f'https://codeload.github.com/{SOURCE_REPOS[name]}/tar.gz/{revision}',
                               archive, transfer_dir, limit=config['new_download_gib_limit'] * 2**30)
            assets[name] = extract_source(archive, output / 'sources' / name, revision)
            assets[name]['archive'] = receipt
            assets[name]['license_files'] = _license_records(assets[name]['files'])
        elif name in REMOTE_ASSETS:
            repo, revision, weight_names = REMOTE_ASSETS[name]
            # Reuse existing access only for the preregistered gated asset.
            # Credential values never enter manifests or transfer receipts.
            auth = {'use_hf_auth': True} if name == 'sam3_checkpoint' else {}
            snapshot = output / 'snapshots' / name
            tree_path = output / 'trees' / (name + '.json')
            download(f'https://huggingface.co/api/models/{repo}/tree/{revision}?recursive=true', tree_path,
                     transfer_dir, limit=config['new_download_gib_limit'] * 2**30, **auth)
            tree = read_json(tree_path)
            choices = [r['path'] for r in tree if r.get('type') == 'file' and 'prompts' not in Path(r['path']).parts and
                       (r['path'] in weight_names or Path(r['path']).suffix in ('.json', '.txt') or
                        Path(r['path']).name.lower().startswith(('license', 'notice', 'readme')))]
            if not set(weight_names) <= set(choices):
                raise ValueError(f'{name}: pinned selected weight missing or inaccessible')
            if len(choices) != len(set(choices)) or any(Path(p).is_absolute() or '..' in Path(p).parts or
                    '\\' in p for p in choices):
                raise ValueError('unsafe or duplicate pinned HF file path')
            records = [download(f'https://huggingface.co/{repo}/resolve/{revision}/{file}',
                       snapshot / file, transfer_dir, limit=config['new_download_gib_limit'] * 2**30, **auth)
                       for file in sorted(choices)]
            for record in records:
                relative = str(Path(record['path']).relative_to(snapshot.resolve()))
                entry = next(r for r in tree if r['path'] == relative)
                expected = entry.get('lfs', {}).get('oid')
                if expected and record['sha256'] != expected:
                    raise ValueError('downloaded HF LFS bytes differ from pinned tree')
                if entry.get('size') is not None and record['bytes'] != entry['size']:
                    raise ValueError('downloaded HF file size differs from pinned tree')
                if not expected and entry.get('oid') and _git_blob_digest(record['path']) != entry['oid']:
                    raise ValueError('downloaded HF metadata bytes differ from pinned git blob')
            assets[name] = (dict(path=str(snapshot.resolve()), revision=revision, files=records,
                                 source_tree=file_record(tree_path)) if name.endswith('_snapshot') else
                            dict(next(r for r in records if Path(r['path']).name == weight_names[0])))
            assets[name]['repository'] = repo
            assets[name]['revision'] = revision
            assets[name]['source_tree'] = file_record(tree_path)
            assets[name]['repository_files'] = records
            assets[name]['license_files'] = _license_records(records)
        else:
            raise ValueError(f'no pinned acquisition recipe for {name}')
        print(f'[setup] asset {name}: ready', flush=True)
    if 'grounding_config' in needed:
        assets['grounding_config'] = file_record(Path(assets['grounding_source']['path']) /
                                                 'groundingdino/config/GroundingDINO_SwinT_OGC.py')
        print('[setup] asset grounding_config: ready', flush=True)
    if 'bpe_vocabulary' in needed:
        root = Path(assets['sam3_source']['path'])
        matches = []
        for base, dirs, names in os.walk(root):
            dirs[:] = [d for d in dirs if d != 'prompts']
            if 'bpe_simple_vocab_16e6.txt.gz' in names:
                matches.append(Path(base) / 'bpe_simple_vocab_16e6.txt.gz')
        if len(matches) != 1:
            raise ValueError('pinned SAM3 BPE vocabulary missing/ambiguous')
        assets['bpe_vocabulary'] = file_record(matches[0])
        print('[setup] asset bpe_vocabulary: ready', flush=True)
    if 'S2' in request['components']:
        _grounding_weight_provenance(assets, request, output, config)
    return assets


def _license_records(records):
    return [record for record in records if Path(record['path']).name.lower().startswith(
        ('license', 'licence', 'notice', 'copying', 'copyright', 'readme'))]


def _git_blob_digest(path):
    path = safe_path(path)
    checksum = hashlib.sha1(f'blob {path.stat().st_size}\0'.encode())
    with path.open('rb') as stream:
        while block := stream.read(2**20):
            checksum.update(block)
    return checksum.hexdigest()


def _grounding_weight_provenance(assets, request, output, config):
    """Bind reused historical bytes to the S2 asset revision, without inference."""
    print('[setup] asset grounding_checkpoint: pinned repository verification', flush=True)
    repo, revision = GROUNDING_WEIGHT_PIN
    directory = output / 'grounding-weight-provenance'
    tree_path = directory / 'tree.json'
    limit = int(config['new_download_gib_limit'] * 2**30)
    download(f'https://huggingface.co/api/models/{repo}/tree/{revision}?recursive=true', tree_path,
             Path(request['transfer_dir']), limit=limit)
    tree = read_json(tree_path)
    choices = [r for r in tree if r.get('type') == 'file' and r['path'] == 'groundingdino_swint_ogc.pth']
    if len(choices) != 1 or not re.fullmatch('[a-f0-9]{64}', choices[0].get('lfs', {}).get('oid', '')):
        raise ValueError('pinned Grounding DINO repository lacks the selected checkpoint identity')
    original = dict(assets['grounding_checkpoint'])
    verified = verify_record(original)
    if verified['sha256'] != choices[0]['lfs']['oid'] or verified['bytes'] != choices[0]['size']:
        raise ValueError('historical Grounding DINO bytes do not match the prescribed S2 HF revision')
    records = [original]
    for entry in tree:
        name = entry['path']
        if entry.get('type') != 'file' or 'prompts' in Path(name).parts or not (
                Path(name).suffix in ('.json', '.txt') or Path(name).name.lower().startswith(
                    ('readme', 'license', 'licence', 'notice', 'copying'))):
            continue
        if Path(name).is_absolute() or '..' in Path(name).parts or '\\' in name:
            raise ValueError('unsafe Grounding DINO repository metadata path')
        record = download(f'https://huggingface.co/{repo}/resolve/{revision}/{name}', directory / name,
                          Path(request['transfer_dir']), limit=limit)
        if record['bytes'] != entry['size'] or (entry.get('lfs') and record['sha256'] != entry['lfs']['oid']) or (
                not entry.get('lfs') and entry.get('oid') and _git_blob_digest(record['path']) != entry['oid']):
            raise ValueError('Grounding DINO metadata differs from the pinned repository tree')
        records.append(record)
    assets['grounding_checkpoint'] = dict(original, repository=repo, revision=revision,
        source_tree=file_record(tree_path), repository_files=records, license_files=_license_records(records),
        pinned_identity_check='historical bytes equal the selected pinned repository LFS SHA256 and size')
    print('[setup] asset grounding_checkpoint: pinned identity verified', flush=True)


def _normalize_name(name):
    return re.sub(r'[-_.]+', '-', name).lower()


def _fixed_versions(requirements):
    result = {}
    for value in requirements:
        match = re.fullmatch(r'([A-Za-z0-9_.-]+)==([^\s;]+)', value)
        if match:
            name, version = _normalize_name(match[1]), match[2]
            if name in result and result[name] != version:
                raise ValueError(f'contradictory required package pins: {name}')
            result[name] = version
    return result


def _validate_setup_request(request):
    from .setup_recipes import recipe
    environment = request['environment']
    expected = recipe(environment)
    if any(request.get(key) != value for key, value in expected.items()):
        raise ValueError('setup request changes a prescribed dependency/build recipe')
    if request['components'] != sorted(c for c, env in ENVIRONMENTS.items() if env == environment):
        raise ValueError('setup environment has the wrong dependent components')
    if request.get('no_runtime_fallback') is not True or request.get('no_automatic_retry') is not True:
        raise ValueError('setup must preserve the single attempt and exact runtime target')
    local = safe_path(request['run_root']).absolute()
    for name in ('uv_cache', 'python_install_dir', 'transfer_dir', 'toolkit_directory'):
        if not safe_path(request[name]).absolute().is_relative_to(local):
            raise ValueError(f'{name} must belong to the declared run')
    if safe_path(request['transfer_dir']).absolute() != local / 'transfers':
        raise ValueError('setup requires the shared run transfer directory')
    return expected


def _aot_link(assets):
    source = safe_path(assets['samtrack_source']['path'])
    aot = safe_path(assets['aot_source']['path']).resolve()
    path = source / 'aot'
    preserved = None
    if path.is_symlink():
        if path.resolve() != aot:
            raise ValueError('SAM-Track aot link does not select its pinned source')
    else:
        if path.exists():
            if not path.is_dir():
                raise ValueError('SAM-Track aot path is neither a directory nor the pinned link')
            # This exact SAM-Track revision vendors AOT; retain its bytes and
            # license evidence while selecting the separately prescribed pin.
            destination = source / ('aot.vendored-' + uuid.uuid4().hex)
            if destination.exists() or destination.is_symlink():
                raise ValueError('AOT preservation destination is already occupied')
            path.rename(destination)
            preserved = dict(path=str(destination.absolute()), original_path=str(path.absolute()),
                             source_asset='samtrack_source', revision=assets['samtrack_source']['revision'])
            if any(destination.iterdir()):
                preserved['inventory'] = tree_record(destination, preserved['revision'])
            else:
                preserved['inventory'] = dict(path=str(destination.absolute()),
                                              revision=preserved['revision'], files=[])
        path.symlink_to(aot, target_is_directory=True)
    return dict(path=str(path.absolute()), target=str(aot), source_asset='aot_source',
                preserved_vendored=preserved)


def _correlation_asset(request, output, config):
    if request['native_correlation'] != 'spatial-correlation-sampler==0.5.0':
        raise ValueError('unexpected native correlation source version')
    metadata = output / 'correlation' / 'pypi-0.5.0.json'
    transfer = Path(request['transfer_dir'])
    limit = int(config['new_download_gib_limit'] * 2**30)
    download('https://pypi.org/pypi/spatial-correlation-sampler/0.5.0/json', metadata, transfer, limit=limit)
    manifest = read_json(metadata)
    if _normalize_name(manifest['info']['name']) != 'spatial-correlation-sampler' or manifest['info']['version'] != '0.5.0':
        raise ValueError('correlation metadata does not identify its exact selected release')
    choices = [item for item in manifest['urls'] if item['packagetype'] == 'sdist' and not item.get('yanked')]
    if len(choices) != 1:
        raise ValueError('exact correlation source distribution missing or ambiguous')
    selected = choices[0]
    filename = selected['filename']
    if Path(filename).name != filename or not filename.endswith('.tar.gz') or not selected['url'].startswith(
            'https://files.pythonhosted.org/') or not re.fullmatch('[a-f0-9]{64}', selected['digests']['sha256']):
        raise ValueError('unsafe correlation source distribution identity')
    path = output / 'correlation' / filename
    download(selected['url'], path, transfer, limit=limit)
    record = file_record(path, selected['digests']['sha256'])
    if record['bytes'] != selected['size']:
        raise ValueError('correlation source archive differs from its published size')
    return dict(record, version='0.5.0', repository='spatial-correlation-sampler',
                source_metadata=file_record(metadata), url=selected['url'])


def _refresh_sources(assets, original):
    updated = dict(assets)
    baseline = read_json(verify_record(original)['path'])
    for name in SOURCE_REPOS.keys() & assets.keys():
        previous = assets[name]
        fresh = tree_record(previous['path'], previous['revision'])
        before = {r['path']: r for r in baseline[name]['files']}
        after = {r['path']: r for r in fresh['files']}
        changes = [dict(path=path, change='added' if path not in before else 'removed' if path not in after else 'changed')
                   for path in sorted(before.keys() | after.keys()) if before.get(path) != after.get(path)]
        updated[name] = dict(previous, **fresh, original_inventory=original,
                             generated_file_changes=changes, license_files=_license_records(fresh['files']))
    return updated


def _check_inventory(inventory, request):
    target = TARGETS[request['environment']]
    if any(inventory['versions'].get(k) != v for k, v in target.items()):
        raise ValueError('resolved environment changed a prescribed Python/torch/torchvision/NumPy version')
    installed = {_normalize_name(item['name']): item['version'] for item in inventory['packages']}
    required = list(request['requirements'])
    if request['native_correlation']:
        required.append(request['native_correlation'])
    for name, version in _fixed_versions(required).items():
        if installed.get(name) != version:
            raise ValueError(f'resolved environment changed prescribed {name}=={version}')
    if request['environment'] == 'E3' and any('flash-attn' in name for name in installed):
        raise ValueError('SAM3 recipe unexpectedly introduced FlashAttention')


def _native_api_imports(environment, assets):
    """Inspect source ownership and required APIs/extensions without builders."""
    import importlib
    import importlib.machinery
    from .setup_recipes import CORE_IMPORTS
    for _, source, _ in CORE_IMPORTS[environment]:
        if source:
            root = safe_path(assets[source]['path']).resolve()
            for path in (root / 'src', root):
                if path.is_dir() and str(path) not in sys.path:
                    sys.path.insert(0, str(path))
    records = []
    for name, source, symbols in CORE_IMPORTS[environment]:
        module = importlib.import_module(name)
        path = safe_path(module.__file__).resolve()
        if source and not path.is_relative_to(safe_path(assets[source]['path']).resolve()):
            raise ValueError(f'{name} imported outside its pinned source')
        if name in ('groundingdino._C', 'sam2._C') and not any(str(path).endswith(suffix)
                for suffix in importlib.machinery.EXTENSION_SUFFIXES):
            raise ValueError(f'{name} is not the mandatory compiled native extension')
        for symbol in symbols:
            if not hasattr(module, symbol):
                raise ValueError(f'{name} lacks required native API {symbol}')
        if name.endswith('networks.layers.attention') and module.enable_corr is not True:
            raise ValueError('AOT correlation import selected an implicit fallback')
        records.append(dict(module=name, source_asset=source, symbols=symbols, file=file_record(path)))
    if environment == 'E1':
        package = importlib.import_module('aot')
        if safe_path(assets['aot_source']['path']).resolve() not in [safe_path(p).resolve() for p in package.__path__]:
            raise ValueError('AOT namespace is not the declared pinned subtree')
    if environment in ('E4', 'E5', 'E6'):
        package = importlib.import_module('xformers')
        if getattr(package, '_has_cpp_library', False) is not True:
            raise ValueError('required xFormers native extension did not load')
    return records


def qualify_imports(request, output):
    """Subprocess entry: import APIs only, with network/ViPE/forwards denied."""
    import importlib.metadata
    import socket
    from unittest.mock import patch
    import torch
    import torchvision
    import cv2
    import numpy as np
    from .isolation import deny_vipe
    settings = read_json(request)
    actual = dict(python=f'{sys.version_info.major}.{sys.version_info.minor}', torch=torch.__version__,
                  torchvision=torchvision.__version__, numpy=np.__version__)
    if actual != TARGETS[settings['environment']]:
        raise ValueError('actually imported base modules differ from the prescribed environment')
    def prohibited(*args, **kwargs):
        raise RuntimeError('setup import qualification prohibits network access and model forwards')
    isolation = deny_vipe(settings['forbidden_vipe_roots'])
    with patch.object(socket, 'create_connection', prohibited), patch.object(socket.socket, 'connect', prohibited), \
         patch.object(socket.socket, 'connect_ex', prohibited), patch.object(torch.nn.Module, '_call_impl', prohibited):
        modules = _native_api_imports(settings['environment'], read_json(verify_record(settings['assets'])['path']))
    write_json(output, dict(status='complete', environment=settings['environment'], modules=modules,
        native_model_constructors_called=False, forwards=0, cuda_context_initialized=bool(torch.cuda.is_initialized()),
        isolation=isolation, offline=True,
        imported_base=dict(torch=torch.__version__, torchvision=torchvision.__version__,
                           opencv=cv2.__version__, numpy=importlib.metadata.version('numpy'))))


def setup(request, output, config):
    """One serial E1--E7 attempt: fixed base, locked dependencies, native imports."""
    _validate_setup_request(request)
    environment, target = request['environment'], TARGETS[request['environment']]
    output = safe_path(output).absolute()
    if not output.is_relative_to(safe_path(request['run_root']).absolute()):
        raise ValueError('setup output must belong to its declared run')
    output.mkdir(parents=True, exist_ok=False)
    write_json(output / 'config.json', request)
    assets = acquire_assets(request, output, config)
    write_json(output / 'assets-before-build.json', assets)
    original = file_record(output / 'assets-before-build.json')
    from .backends import AssetBundle
    for component in request['components']:
        AssetBundle(component, assets)
    env_path = output / 'environment'
    python = str(env_path / 'bin/python')
    runtime_env = dict(os.environ, UV_CACHE_DIR=request['uv_cache'],
        UV_PYTHON_INSTALL_DIR=request['python_install_dir'], UV_LINK_MODE='hardlink',
        UV_HTTP_RETRIES='0', PIP_RETRIES='0', PIP_NO_INPUT='1',
        UV_CONCURRENT_DOWNLOADS='1', UV_CONCURRENT_BUILDS='1', UV_CONCURRENT_INSTALLS='7',
        OMP_NUM_THREADS='7', MAX_JOBS='7', MMCV_WITH_OPS='0', PYTHONDONTWRITEBYTECODE='1',
        PYTHONNOUSERSITE='1')
    runtime_env.pop('PYTHONPATH', None)
    runtime_env.pop('PYTHONHOME', None)
    constraints = output / 'constraints.txt'
    pins = _fixed_versions(request['requirements'])
    constraints.write_text(''.join(f'{name}=={version}\n' for name, version in sorted(pins.items())))
    requirements = output / 'requirements.txt'
    requirements.write_text('\n'.join(request['requirements']) + '\n')
    lock = output / 'requirements.lock'
    executed, receipts = [], []
    def run(command, label, *, offline=False):
        print(f'[setup {environment}] {label}: start', flush=True)
        start, error = time.monotonic(), None
        log = output / 'commands' / f'{len(executed):02d}-{label}.log'
        log.parent.mkdir(exist_ok=True)
        env = dict(runtime_env)
        if offline:
            env.update(HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1', UV_OFFLINE='1')
        try:
            with log.open('x') as stream:
                if command[0] == request['uv']:
                    from .transfer_proxy import uv_proxy
                    with uv_proxy(request['run_root'], int(config['new_download_gib_limit'] * 2**30),
                                  artifact_limit=int(config['new_artifact_disk_gib_limit'] * 2**30)) as proxy:
                        env.update(proxy.environment)
                        try:
                            subprocess.run(command, check=True, env=env, cwd=ROOT,
                                           stdout=stream, stderr=subprocess.STDOUT)
                        finally:
                            proxy.check()
                else:
                    subprocess.run(command, check=True, env=env, cwd=ROOT, stdout=stream, stderr=subprocess.STDOUT)
        except BaseException as exc:
            error = f'{type(exc).__name__}: {exc}'
            raise
        finally:
            receipt = output / 'commands' / f'{len(executed):02d}-{label}.json'
            write_json(receipt, dict(command=command, cwd=str(ROOT), log=file_record(log),
                wall_seconds=time.monotonic() - start, error=error, offline=offline,
                automatic_retries=0, package_transfer_proxy=command[0] == request['uv']))
            executed.append(command)
            receipts.append(file_record(receipt))
            print(f'[setup {environment}] {label}: {"failed" if error else "complete"}', flush=True)
    index = ['--index-url', 'https://pypi.org/simple', '--extra-index-url',
             'https://download.pytorch.org/whl/' + target['torch'].split('+')[1],
             '--index-strategy', 'unsafe-best-match']
    run([request['uv'], 'venv', '--python', target['python'], str(env_path)], 'venv')
    run([request['uv'], 'pip', 'install', '--python', python, *index, '-c', str(constraints),
         *request['base_requirements']], 'base')
    build_inputs = {}
    if environment in ('E1', 'E2'):
        from .toolkit import acquire_toolkit, build_environment
        print(f'[setup {environment}] toolkit: start', flush=True)
        toolkit = acquire_toolkit(request['toolkit_directory'], request['transfer_dir'], config)
        build = build_environment(toolkit, env_path)
        runtime_env.update(build['env'])
        # One selector thread belongs to the package transfer proxy; preserve
        # the total eight-worker ceiling while a native build is supervised.
        runtime_env['MAX_JOBS'] = '7'
        build['env']['MAX_JOBS'] = '7'
        build['proxy_worker_reservation'] = 1
        write_json(output / 'toolkit.json', dict(toolkit=toolkit, build=build))
        build_inputs['toolkit'] = file_record(output / 'toolkit.json')
        print(f'[setup {environment}] toolkit: ready', flush=True)
    run([request['uv'], 'pip', 'compile', '--python', python, *index, '-c', str(constraints),
         '--generate-hashes', '--no-build-isolation', '--output-file', str(lock), str(requirements)], 'resolve')
    if not lock.is_file() or not lock.stat().st_size:
        raise ValueError('resolver did not produce the required immutable dependency lock')
    run([request['uv'], 'pip', 'install', '--python', python, *index, '--require-hashes',
         '--no-build-isolation', '-c', str(constraints), '-r', str(lock)], 'locked-dependencies')
    if environment == 'E1':
        build_inputs['aot_link'] = _aot_link(assets)
        correlation = _correlation_asset(request, output, config)
        build_inputs['correlation'] = correlation
        run([request['uv'], 'pip', 'install', '--python', python, '--no-deps', '--no-build-isolation',
             correlation['path']], 'correlation', offline=True)
    for name in request['editable_sources']:
        run([request['uv'], 'pip', 'install', '--python', python, '--no-deps', '--no-build-isolation',
             '-e', assets[name]['path']], name, offline=True)
    assets = _refresh_sources(assets, original)
    if 'aot_link' in build_inputs:
        assets['samtrack_source']['generated_links'] = [build_inputs['aot_link']]
    write_json(output / 'assets-before-imports.json', assets)
    imports_request = dict(environment=environment, assets=file_record(output / 'assets-before-imports.json'),
                           forbidden_vipe_roots=request['forbidden_vipe_roots'])
    write_json(output / 'imports-request.json', imports_request)
    run([python, '-m', 'scripts.vipe_benchmark.runtime', '--qualify-imports', str(output / 'imports-request.json'),
         '--output', str(output / 'imports.json')], 'native-imports', offline=True)
    qualification = read_json(output / 'imports.json')
    if qualification.get('status') != 'complete' or qualification.get('forwards') != 0 or type(qualification.get(
            'cuda_context_initialized')) is not bool:
        raise ValueError('native import qualification was incomplete or performed model forwards')
    run([python, str(ROOT / 'scripts/vipe_benchmark/runtime_inventory.py'), '--output', str(output / 'inventory.json')],
        'inventory', offline=True)
    inventory = read_json(output / 'inventory.json')
    _check_inventory(inventory, request)
    assets = _refresh_sources(assets, original)
    write_json(output / 'assets.json', assets)
    write_json(output / 'build-inputs.json', build_inputs)
    write_json(output / 'result.json', dict(status='complete', environment=environment,
        components=request['components'], assets=file_record(output / 'assets.json'),
        runtime=dict(python=str((env_path / 'bin/python').absolute()), versions=target,
            inventory=file_record(output / 'inventory.json'), imports=file_record(output / 'imports.json'),
            dependency_lock=file_record(lock), build_inputs=file_record(output / 'build-inputs.json')),
        commands=executed, command_receipts=receipts, setup_attempts=1,
        real_gpu_qualification='pending first allocated candidate result',
        commercial_permission='unverified', non_agpl='unverified'))


if __name__ == '__main__':
    if __spec__ is not None:
        sys.modules.setdefault(__spec__.name, sys.modules[__name__])
    import argparse
    parser = argparse.ArgumentParser(description='Import-only native runtime qualification')
    parser.add_argument('--qualify-imports', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    qualify_imports(args.qualify_imports, args.output)

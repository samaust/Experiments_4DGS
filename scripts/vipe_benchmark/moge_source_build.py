"""Bound administrative FlexGEMM build derivation; never execute source code."""
import copy
import gzip
import hashlib
import io
import os
from pathlib import Path, PurePosixPath
import tarfile

from .files import file_record, read_json, verify_record, write_json


REVISION = 'b2fadb29d41846c7981ade6801ffc689fae119cf'
SETUP_SHA256 = '9c0c166b6fac4375b7f29644fff29bda8fd2e77915ab47dd5af4159b8ba62e4d'
PATCHES = (
    ('os.path.expanduser("~/.flex_gemm")',
     'os.path.dirname(os.environ["FLEX_GEMM_AUTOTUNE_CACHE_PATH"])'),
    ("os.path.expanduser('~/.flex_gemm/autotune_cache.json')",
     'os.environ["FLEX_GEMM_AUTOTUNE_CACHE_PATH"]'),
)


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def cache_path(runtime_directory):
    """Require one owned cache location; preserve HOME and numerical settings."""
    directory = Path(runtime_directory).absolute()
    path = directory / 'flex-cache/autotune_cache.json'
    _require(directory == directory.resolve() and not path.is_symlink() and
             not path.parent.is_symlink(), 'scoped FlexGEMM cache contains a link')
    inherited = os.environ.get('FLEX_GEMM_AUTOTUNE_CACHE_PATH')
    _require(inherited is None or inherited == str(path),
             'inherited FlexGEMM cache path escapes the owned runtime')
    return path


def _members(record):
    """Read only bounded ordinary files; reject unsafe names before content."""
    result = []
    total = 0
    with tarfile.open(verify_record(record)['path'], 'r:gz') as archive:
        members = archive.getmembers()
        _require(0 < len(members) <= 10000, 'source archive member count changed')
        for member in members:
            path = PurePosixPath(member.name)
            _require(not path.is_absolute() and '..' not in path.parts and
                     'prompts' not in path.parts and (member.isdir() or member.isfile()),
                     'unsafe source archive member')
            if member.isfile():
                total += member.size
                _require(total <= 128 * 2**20, 'source archive expanded bound exceeded')
                stream = archive.extractfile(member)
                if stream is None:
                    raise ValueError('source archive file missing')
                result.append((copy.copy(member), stream.read()))
    _require(len({m.name for m, _ in result}) == len(result), 'duplicate source archive file')
    return result


def verify_dependency_archives(recipe, sources):
    """Compare actual pinned archive metadata with the reviewed raw originals."""
    reviews = recipe['dependency_reviews']
    _require([(s['name'], s['revision']) for s in sources] ==
             [(r['name'], r['revision']) for r in reviews],
             'dependency archive lineage changed')
    for review, source in zip(reviews, sources):
        files = _members(source['record'])
        roots = {PurePosixPath(m.name).parts[0] for m, _ in files}
        _require(len(roots) == 1 and next(iter(roots)).endswith('-' + review['revision']),
                 'dependency archive revision root changed')
        for key, name in (('pyproject', 'pyproject.toml'), ('setup', 'setup.py')):
            if key not in review:
                continue
            expected = verify_record(review[key])
            payloads = [payload for m, payload in files
                        if PurePosixPath(m.name).parts[1:] == (name,)]
            _require(len(payloads) == 1 and len(payloads[0]) == expected['bytes'] and
                     hashlib.sha256(payloads[0]).hexdigest() == expected['sha256'],
                     'dependency archive differs from reviewed ' + name)


def derive_flex_archive(original, output):
    """Patch exactly two setup cache expressions; retain pristine source receipt."""
    output = Path(output)
    _require(not output.exists() and not output.with_suffix('.json').exists(),
             'immutable FlexGEMM derivation already exists')
    members = _members(original)
    roots = {PurePosixPath(m.name).parts[0] for m, _ in members}
    _require(len(roots) == 1 and next(iter(roots)).endswith('-' + REVISION),
             'exact pinned FlexGEMM archive required')
    originals, derived, changed = [], [], []
    for member, payload in members:
        relative = PurePosixPath(member.name).relative_to(next(iter(roots))).as_posix()
        originals.append(dict(path=relative, sha256=hashlib.sha256(payload).hexdigest(), bytes=len(payload)))
        if relative == 'setup.py':
            _require(hashlib.sha256(payload).hexdigest() == SETUP_SHA256,
                     'unreviewed FlexGEMM setup source changed')
            text = payload.decode()
            for before, after in PATCHES:
                _require(text.count(before) == 1, 'reviewed cache patch count changed')
                text = text.replace(before, after)
            payload = text.encode()
            changed.append(relative)
        member.size = len(payload)
        derived.append((member, payload))
    _require(changed == ['setup.py'], 'exact administrative setup patch required')
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open('xb') as destination, gzip.GzipFile(fileobj=destination, mode='wb', mtime=0, filename='') as compressed:
        with tarfile.open(fileobj=compressed, mode='w') as archive:
            for member, payload in derived:
                archive.addfile(member, io.BytesIO(payload))
    manifest = dict(schema='plan069-flex-source-derivation/v1', status='complete',
        revision=REVISION, original_archive=verify_record(original), derived_archive=file_record(output),
        changed_files=changed, patches=[dict(before=a, after=b) for a, b in PATCHES],
        original_files=originals,
        derived_files=[dict(path=PurePosixPath(m.name).relative_to(next(iter(roots))).as_posix(),
            sha256=hashlib.sha256(payload).hexdigest(), bytes=len(payload)) for m, payload in derived],
        purpose='scope administrative build cache only; no kernel, runtime config or numerical source changed')
    path = output.with_suffix('.json')
    write_json(path, manifest)
    return dict(name='flex-gemm', revision=REVISION, record=file_record(output),
                original_record=verify_record(original), derivation=file_record(path),
                install_local_offline=True)


def verify_derivation(source):
    """Reconcile pristine/derived bytes and exact allowed patch before importing."""
    manifest = read_json(verify_record(source['derivation'])['path'])
    original = verify_record(source['original_record'])
    installed = verify_record(source['record'])
    _require(source.get('name') == 'flex-gemm' and source.get('revision') == REVISION and
             manifest.get('schema') == 'plan069-flex-source-derivation/v1' and
             manifest.get('status') == 'complete' and
             manifest.get('revision') == REVISION and manifest.get('original_archive') == original and
             manifest.get('derived_archive') == installed and manifest.get('changed_files') == ['setup.py'] and
             manifest.get('patches') == [dict(before=a, after=b) for a, b in PATCHES],
             'reviewed FlexGEMM derivation lineage changed')
    before, after = _members(original), _members(installed)
    _require([m.name for m, _ in before] == [m.name for m, _ in after],
             'derived archive file set changed')
    for (member, raw), (_, payload) in zip(before, after):
        if PurePosixPath(member.name).parts[1:] == ('setup.py',):
            _require(hashlib.sha256(raw).hexdigest() == SETUP_SHA256, 'original setup source changed')
            for old, new in PATCHES:
                _require(raw.count(old.encode()) == 1, 'original setup patch count changed')
                raw = raw.replace(old.encode(), new.encode())
        _require(payload == raw, 'unreviewed derived source edit')
    for key, files in (('original_files', before), ('derived_files', after)):
        inventory = [dict(path=PurePosixPath(member.name).relative_to(PurePosixPath(member.name).parts[0]).as_posix(),
            sha256=hashlib.sha256(payload).hexdigest(), bytes=len(payload)) for member, payload in files]
        _require(manifest.get(key) == inventory, 'derived archive inventory differs')
    return manifest

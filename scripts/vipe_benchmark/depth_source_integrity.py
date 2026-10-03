"""Complete extracted source snapshots for native depth entry gates."""

from pathlib import Path

from .files import file_record, object_hash, safe_path


def source_manifest(root):
    root = safe_path(root).resolve()
    files = []
    for path in sorted(root.rglob('*')):
        safe_path(path)
        if path.is_symlink():
            raise ValueError('native source symlinks prohibited')
        if path.is_file():
            record = file_record(path)
            files.append(dict(path=path.relative_to(root).as_posix(),
                              sha256=record['sha256'], bytes=record['bytes']))
    if not files:
        raise ValueError('native source tree empty')
    return dict(schema='plan069-depth-source-manifest/v1', files=files,
                sha256=object_hash(files))


def verify_source(setup):
    if setup.get('source_manifest') != source_manifest(setup['source_dir']):
        raise ValueError('native source tree changed since setup')
    if setup.get('source_archive') != file_record(setup['source_archive']['path']):
        raise ValueError('native source archive changed since setup')

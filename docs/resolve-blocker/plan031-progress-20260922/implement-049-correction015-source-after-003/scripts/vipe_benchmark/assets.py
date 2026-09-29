"""Explicit, bounded immutable asset acquisition; never discover a latest model."""
import argparse
import hashlib
from pathlib import Path
import time
import urllib.request

from .files import file_record, read_json, safe_path, write_json


def acquire(url, output, *, sha256_prefix, byte_limit, seconds=1200):
    output = safe_path(output)
    if not url.startswith('https://') or len(sha256_prefix) < 8:
        raise ValueError('HTTPS source and published checksum required')
    receipt = output.with_suffix(output.suffix + '.json')
    if output.exists() or receipt.exists():
        raise ValueError('asset already exists; verify its receipt instead of downloading again')
    output.parent.mkdir(parents=True, exist_ok=True)
    partial = output.with_suffix(output.suffix + '.partial')
    start, received = time.monotonic(), 0
    checksum = hashlib.sha256()
    # A failed transfer may leave only this explicitly named partial file. A
    # repository-authorized retry replaces that incomplete transfer, not a model
    # job or a successful write. Every attempt retains a separate audit receipt.
    attempts = list(output.parent.glob(output.name + '.transfer-*.json'))
    attempt = output.parent / f'{output.name}.transfer-{len(attempts) + 1:03d}.json'
    error = None
    try:
        with urllib.request.urlopen(url, timeout=min(60, seconds)) as response:
            length = response.headers.get('Content-Length')
            if length and int(length) > byte_limit:
                raise ValueError('asset exceeds remaining download allocation')
            with partial.open('wb') as stream:
                while chunk := response.read(min(2**20, byte_limit - received + 1)):
                    received += len(chunk)
                    if received > byte_limit:
                        raise ValueError('download allocation exceeded')
                    if time.monotonic() - start >= seconds:
                        raise TimeoutError('asset acquisition time allowance exhausted')
                    stream.write(chunk)
                    checksum.update(chunk)
        if not checksum.hexdigest().startswith(sha256_prefix):
            raise ValueError('downloaded asset checksum does not match published prefix')
        partial.rename(output)
        write_json(receipt, dict(schema='vipe-benchmark-asset/v1', url=url,
                   published_sha256_prefix=sha256_prefix, asset=file_record(output)))
    except BaseException as exc:
        error = f'{type(exc).__name__}: {exc}'
        raise
    finally:
        write_json(attempt, dict(url=url, output=str(output.resolve()), bytes_received=received,
                   wall_seconds=time.monotonic() - start, error=error, complete=error is None))
    return read_json(receipt)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--policy', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    policy = read_json(args.policy)
    teacher = policy['primary']
    print(acquire(teacher['url'], args.output, sha256_prefix=teacher['sha256_prefix'],
                  byte_limit=min(512 * 2**20, policy['limits']['new_download_gib'] * 2**30),
                  seconds=policy['limits']['asset_acquisition_seconds']))


if __name__ == '__main__':
    main()

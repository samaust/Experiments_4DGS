"""One bounded HEAD through the metered inherited route; no setup or inference."""
import argparse
import json
import os
from pathlib import Path
import subprocess

from .transfer_proxy import inherited_https_proxy, uv_proxy


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--direct', action='store_true',
                        help='Explicitly test direct egress; only allowed with no inherited proxy.')
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    environment = dict(os.environ)
    route = inherited_https_proxy(environment)
    if args.direct and route is not None:
        raise SystemExit('direct diagnostic refuses to bypass an inherited proxy route')
    if route is None and not args.direct:
        raise SystemExit('diagnostic requires an inherited HTTPS proxy route')
    with uv_proxy(args.output, 2**20, upstream_proxy=route) as proxy:
        environment.update(proxy.environment)
        result = subprocess.run(
            ['curl', '--head', '--silent', '--show-error', '--fail', '--retry', '0',
             '--connect-timeout', '5', '--max-time', '20', '--output', os.devnull,
             '--write-out', '%{http_code}', 'https://download.pytorch.org/whl/cu130/torch/'],
            env=environment, capture_output=True, text=True, timeout=22)
        proxy.check()
        if result.returncode:
            # Raw stderr can contain environment/route details; retain only exit status.
            raise RuntimeError(f'HEAD failed with curl exit {result.returncode}')
    receipt = args.output / 'uv-transfers' / f'transfer-{proxy.transfer_id}.json'
    print(json.dumps(dict(route='metered direct' if args.direct else 'metered inherited HTTP CONNECT', http_status=result.stdout,
                          bytes_received=proxy.received, receipt=str(receipt))))


if __name__ == '__main__':
    main()

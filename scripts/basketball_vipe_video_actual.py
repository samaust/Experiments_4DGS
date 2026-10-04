"""Reserved D9/D10 native sequence inference, scale checks and clip package."""

import argparse
from pathlib import Path

from vipe_benchmark.config import load
from vipe_benchmark.files import read_json
from vipe_benchmark.ledger import Ledger
from vipe_benchmark.video_depth import (
    MetricVideoDepthAdapter, VideoDepthAdapter, admitted_video_request,
    run_video_actual,
)
from vipe_benchmark.video_native import load_native_video


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--request', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    request = read_json(args.request)
    config = dict(load(), new_download_gib_limit=110,
                  new_artifact_disk_gib_limit=210)
    ledger = Ledger(Path(request['ledger_path']), config)
    admitted_video_request(request, args.output, config, ledger=ledger,
                           request_path=args.request)
    candidate = request['component']
    model = load_native_video(candidate, request['setup'], device='cuda', ledger=ledger,
                              active_map_admission=request['admission'])
    adapter = (MetricVideoDepthAdapter if candidate == 'D10' else VideoDepthAdapter)(
        model, device='cuda')
    run_video_actual(request, args.output, config, backend=adapter, ledger=ledger,
                     request_path=args.request)


if __name__ == '__main__':
    main()

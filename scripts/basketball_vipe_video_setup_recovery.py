"""Execute a separately reserved offline D9 setup recovery; no dispatch authority."""
import argparse
from vipe_benchmark.files import read_json
from vipe_benchmark.video_setup_recovery import run_video_setup_recovery


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--request',required=True)
    parser.add_argument('--output',required=True)
    args=parser.parse_args()
    request=read_json(args.request)
    if request.get('record_kind')!='actual':
        raise ValueError('actual explicitly reserved recovery request required')
    run_video_setup_recovery(request,args.output,request_path=args.request)


if __name__=='__main__':
    main()

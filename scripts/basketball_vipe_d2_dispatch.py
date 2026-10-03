"""Dispatch the admitted D2 attempt using the qualified E5 interpreter."""
import argparse
from vipe_benchmark.d2_actual import dispatch, RUN


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--context', required=True)
    parser.add_argument('--qualification', required=True)
    parser.add_argument('--run-id', default=RUN)
    args = parser.parse_args()
    dispatch(args.context, args.qualification, run_id=args.run_id)


if __name__ == '__main__':
    main()

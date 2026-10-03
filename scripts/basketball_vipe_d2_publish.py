"""Publish four D2 matched clips after confirmed map-worker cleanup."""
import argparse
from vipe_benchmark.d2_actual import publish, RUN


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id', default=RUN)
    args = parser.parse_args()
    publish(run_id=args.run_id)


if __name__ == '__main__':
    main()

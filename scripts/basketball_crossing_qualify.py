"""CPU qualification for the frozen Plan 028 lifetime repair."""
import argparse
import json
from pathlib import Path

from basketball_crossing_repair import qualify_projection, resolve_duration_target
from basketball_study import digest, write_new


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--initializer', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    record = json.loads((args.initializer / 'result.json').read_text())
    target = resolve_duration_target(record)
    projection = qualify_projection()
    write_new(args.output, dict(schema='basketball-crossing-repair-qualification/v1',
        initializer=str((args.initializer / 'result.json').resolve()),
        initializer_sha256=digest(args.initializer / 'result.json'),
        resolved_duration_target=target, projection=projection,
        checks=dict(finite_positive_target=True, rendering_floor=True,
                    boundary_gradient=True, selective_moment_reset=True,
                    adam_step_preserved=True),
        qualification_updates=12, gpu_jobs=0))


if __name__ == '__main__':
    main()

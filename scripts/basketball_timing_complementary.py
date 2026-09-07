"""Check fixed-priority complementary fitting edges, without value-based pruning."""
import argparse
from pathlib import Path
from basketball_scale import read,write
from basketball_audit import sha256
from basketball_timing import graph_offsets
from basketball_continuation_audit import CALIBRATION_SHA


def combine(temporal,absolute):
    edges={}
    for label,source in [('sift-temporal-bias',temporal),('sift-absolute',absolute)]:
        if source['calibration_sha256']!=CALIBRATION_SHA or source.get('selection_consumed') or source.get('final_validation_consumed'):
            raise ValueError('invalid fitting source/calibration/role')
        for e in source['edges']:
            key=(e['a'],e['b'])
            if e['passed'] and key not in edges:
                edges[key]=dict(a=e['a'],b=e['b'],lag=e['lag'],passed=True,source=label)
    return [edges[k] for k in sorted(edges)]


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ['protocol','temporal','absolute','output']:p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();protocol=read(a.protocol)
    if protocol['source_priority']!=['sift-temporal-bias','sift-absolute'] or protocol['timing_gate_frames']!=.25 or protocol['reference_camera']!=1 or protocol['camera_ids']!=list(range(34)):
        raise ValueError('changed compatibility policy')
    edges=combine(read(a.temporal),read(a.absolute));result=graph_offsets(edges,tolerance=.25)
    write(a.output,dict(schema='basketball-timing-complementary-result/v1',**result,edges=edges,
        protocol_sha256=sha256(a.protocol),source_sha256={str(a.temporal):sha256(a.temporal),str(a.absolute):sha256(a.absolute)},
        adapter_sha256=sha256(__file__),calibration_sha256=CALIBRATION_SHA,selection_consumed=False,final_validation_consumed=False))
    print(result);return result['status']!='passed'


if __name__=='__main__':raise SystemExit(main())

"""Verify every historical target/render hash before reusing update-5000 scores."""
import argparse
import json
import math
from pathlib import Path

from basketball_study import MANIFEST, ROOT, digest, verify_files, write_new


def finite(value):
    if isinstance(value, dict):
        return all(finite(v) for v in value.values())
    if isinstance(value, list):
        return all(finite(v) for v in value)
    return not isinstance(value, float) or math.isfinite(value)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    protocol = ROOT / 'docs/research/basketball-sync-pivot/evaluation-protocol-v3.json'
    verify_files(json.loads(protocol.read_text())['files'])
    inputs_path = ROOT / '.local/sync-pivot/evaluation-inputs.json'
    inputs = json.loads(inputs_path.read_text())
    if inputs['protocol_sha256'] != digest(protocol):
        raise ValueError('historical protocol mismatch')
    regions_path = ROOT / '.local/sync-pivot/basketball-evaluation-regions/regions.json'
    regions = json.loads(regions_path.read_text())
    keys = {(r['camera'], r['frame_id']) for r in regions['frames']}
    if len(keys) != 350 or regions['manifest_sha256'] != digest(MANIFEST):
        raise ValueError('evaluation target protocol mismatch')
    for r in regions['frames']:
        if digest(regions_path.parent / r['mask_path']) != r['mask_sha256']:
            raise ValueError('historical mask changed')
    records = []
    for entry in inputs['runs']:
        checkpoint = ROOT / entry['checkpoint']['path']
        path = Path(entry['render'])
        report = json.loads(path.read_text())
        metrics_path = ROOT / f".local/sync-pivot/evaluation/metrics/worker/{entry['method']}-seed{entry['seed']}.json"
        metrics = json.loads(metrics_path.read_text())
        if (digest(checkpoint) != entry['checkpoint']['sha256'] or
            report['checkpoint_sha256'] != digest(checkpoint) or report['iteration'] != 5000 or
            report['regions_sha256'] != digest(regions_path) or report['manifest_sha256'] != digest(MANIFEST) or
            report['script_sha256'] != digest(ROOT / 'scripts/evaluate-basketball-sync.py') or
            metrics['render_sha256'] != digest(path) or not metrics['complete'] or not finite(metrics) or
            metrics['method'] != entry['method'] or metrics['seed'] != entry['seed'] or metrics['iteration'] != 5000):
            raise ValueError('historical checkpoint/render/metric pairing mismatch')
        for rows in (report['frames'], metrics['frames']):
            if len(rows) != 350 or {(r['camera'], r['frame_id']) for r in rows} != keys:
                raise ValueError('historical evaluation coverage mismatch')
        for row in report['frames']:
            if digest(path.parent / row['path']) != row['sha256'] or digest(row['target_path']) != row['target_sha256']:
                raise ValueError('historical prediction/target changed')
        records.append(dict(arm='freetimegs-sparse' if entry['method'] == 'freetimegs' else entry['method'],
            seed=entry['seed'], iteration=5000, checkpoint=str(checkpoint), checkpoint_sha256=digest(checkpoint),
            render=str(path), render_sha256=digest(path), metrics=str(metrics_path), metrics_sha256=digest(metrics_path)))
    summary_path = ROOT / '.local/sync-pivot/evaluation/metrics/worker/summary.json'
    summary = json.loads(summary_path.read_text())
    if summary['script_sha256'] != digest(ROOT / 'scripts/basketball_reconstruction_metrics.py') or summary['inputs_sha256'] != digest(inputs_path):
        raise ValueError('historical metric definitions changed')
    write_new(a.output, dict(schema='basketball-study-baseline-reuse/v1', status='verified',
        protocol_path=str(protocol), protocol_sha256=digest(protocol), records=records,
        verified='all six checkpoint hashes, 2100 render and target pairs, 350 frozen masks, complete finite metric coverage and source definitions'))


if __name__ == '__main__':
    main()

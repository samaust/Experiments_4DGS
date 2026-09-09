"""Independent final coverage, provenance, and closed-ledger audit for Plan 026."""
import argparse
import json
from pathlib import Path

from basketball_study import ARTIFACTS, CURVE, DOCS, MANIFEST, ROOT, digest, verify_files, write_new
from basketball_study_baselines import finite


def require(condition, message):
    if not condition:
        raise ValueError(message)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--index', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    index = json.loads(args.index.read_text())
    manifest = json.loads(MANIFEST.read_text())
    expected = {(c['id'], f) for c in manifest['cameras'] for f in range(50)
                if c['id'] in ('0', '10', '20', '30') or 20 <= f <= 24}
    require(len(expected) == 350, 'target protocol changed')
    protocol = ROOT / 'docs/research/basketball-sync-pivot/evaluation-protocol-v3.json'
    verify_files(json.loads(protocol.read_text())['files'])
    records = index['records']
    required_runs = {(arm, seed, step) for arm in ('stg-full', 'freetimegs-sparse')
                     for seed in range(3) for step in CURVE}
    require(len(records) == 30 and not index['missing_available_results'] and
            {(r['arm'], r['seed'], r['iteration']) for r in records} == required_runs,
            'duplicate, missing, or unexpected curve results')
    for record in records:
        for key in ('checkpoint', 'render', 'metrics'):
            require(digest(record[key]) == record[key + '_sha256'], f'{key} hash changed')
        render = json.loads(Path(record['render']).read_text())
        metrics = json.loads(Path(record['metrics']).read_text())
        # Historical baseline records predate the optional method alias field.
        method = 'freetimegs' if record['arm'] == 'freetimegs-sparse' else 'stg-full'
        require(record.get('method', method) == method, 'incorrect method alias')
        require(render['complete'] and metrics['complete'] and finite(metrics), 'incomplete or nonfinite result')
        require(render['checkpoint_sha256'] == record['checkpoint_sha256'] and
                render['manifest_sha256'] == digest(MANIFEST), 'render provenance mismatch')
        require(metrics['seed'] == record['seed'] and metrics['iteration'] == record['iteration'] and
                metrics['method'] == method and render['method'] == method and
                render['iteration'] == record['iteration'] and metrics['render_sha256'] == record['render_sha256'],
                'metric/render pairing mismatch')
        for result in (render, metrics):
            require(len(result['frames']) == 350 and
                    {(row['camera'], row['frame_id']) for row in result['frames']} == expected,
                    'incorrect evaluation target coverage')
    active, peak, starts, ends = set(), 0, 0, 0
    for event in map(json.loads, (ARTIFACTS / 'ledger.jsonl').read_text().splitlines()):
        key = str(Path(event['output']).resolve())
        if event['event'] == 'start':
            require(key not in active, 'duplicate active segment')
            active.add(key)
            starts += 1
            peak = max(peak, len(active))
        elif event['event'] in ('finish', 'failure'):
            require(key in active, 'unmatched segment completion')
            active.remove(key)
            ends += 1
            require(event['event'] == 'finish' and event['exit_code'] == 0 and not event['interrupted'],
                    'failed or interrupted GPU segment requires assessment')
    require(not active and peak == 1, 'open or overlapping GPU jobs')
    queue = json.loads((ARTIFACTS / 'queue-result.json').read_text())
    require(queue['available_trajectories'] == 6 and queue['new_curve_evaluations'] == 24,
            'queue completion mismatch')
    write_new(args.output, dict(available_trajectories=6, curve_results=30, targets_per_result=350,
        total_metric_rows=10500, all_exact_target_sets=True, all_metrics_finite=True,
        all_arm_seed_checkpoint_pairs_verified=True, all_checkpoint_render_metric_hashes_reverified=True,
        protocol_sha256=digest(protocol), historical_protocol_files_unchanged=True,
        ledger_segments_started=starts, ledger_segments_finished=ends,
        peak_recorded_gpu_job_concurrency=peak, unclosed_segments=[], queue_completed=True,
        full_study_complete=False, dense_prerequisite='not met',
        gpu_training_bitwise_reproducibility='not established; exact restoration and native variability are documented separately'))


if __name__ == '__main__':
    main()

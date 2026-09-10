"""Plan 027 recipe-separated fresh reloads using the frozen Plan 024 renderer."""
import argparse
import json
import os
from pathlib import Path

from basketball_study import CURVE, MANIFEST, ROOT, digest, supervise, verify_files, write_new
from basketball_dense_training import ARTIFACTS, DOCS, ARMS, configure
from basketball_crossing_repair import policy_record

EVALUATION_CURVE = CURVE + (70000,)


def main():
    configure()
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--arm', choices=ARMS, required=True)
    p.add_argument('--seed', type=int, choices=range(3), required=True)
    p.add_argument('--iteration', type=int, choices=EVALUATION_CURVE, required=True)
    p.add_argument('--training', type=Path, required=True)
    p.add_argument('--training-policy', choices=('holdout', 'all-times'), default='holdout')
    p.add_argument('--lifetime-policy', choices=('original', 'repaired'), default='original')
    a = p.parse_args()
    protocol = json.loads((ROOT / 'docs/research/basketball-sync-pivot/evaluation-protocol-v3.json').read_text())
    verify_files(protocol['files'])
    training = a.training
    provenance = json.loads((training / 'study-provenance.json').read_text())
    result = json.loads((training / 'worker-result.json').read_text())
    if result['iteration'] < a.iteration or provenance['arm'] != a.arm or provenance['seed'] != a.seed:
        raise ValueError('training endpoint or pairing mismatch')
    if digest(training / 'study_adapter.py') != provenance['adapter_sha256']:
        raise ValueError('executed training adapter changed')
    if provenance.get('plan') == 28 and (
            provenance.get('training_policy') != a.training_policy or
            provenance.get('lifetime_policy') != a.lifetime_policy):
        raise ValueError('evaluation policy does not match training provenance')
    method = 'stg-full' if a.arm == 'stg-full' else 'freetimegs'
    environment = 'stg-render' if method == 'stg-full' else 'freetimegs'
    checkout = ROOT / ('.local/SpacetimeGaussians' if method == 'stg-full' else '.local/FreeTimeGsVanilla')
    output = ARTIFACTS / f'evaluation/{a.arm}-seed{a.seed}'
    output.mkdir(parents=True, exist_ok=True)
    os.environ['TRAINING_STOP_MONOTONIC'] = 'inf'
    for step in (a.iteration,):
        checkpoint = training / f'checkpoint-{step:06d}.pt'
        checkpoint_hash = digest(checkpoint)
        saved = next(r for r in result['checkpoints'] if r['iteration'] == step)
        binding = json.loads((training/'checkpoint-provenance.json').read_text())
        frozen = json.loads((ARTIFACTS/'initializers'/a.arm/'result.json').read_text())
        if (saved['sha256'] != checkpoint_hash or binding.get('arm') != a.arm or
                binding['method'] != 'freetimegs' or binding['seed'] != a.seed or
                binding['initializer_sha256'] != frozen['archive_sha256']):
            raise ValueError('checkpoint recipe/initializer/seed/hash mismatch')
        folder = output / f'{step:06d}'
        command = [str(ROOT / f'.local/envs/{environment}/bin/python'), 'scripts/evaluate-basketball-sync.py',
            'evaluate', '--method', method, '--checkout', str(checkout), '--manifest', str(MANIFEST),
            '--checkpoint', str(checkpoint), '--regions', str(ROOT / '.local/sync-pivot/basketball-evaluation-regions/regions.json'),
            '--output', str(folder)]
        segment = supervise(command, 'evaluation', ARTIFACTS / f'segments/evaluate-{a.arm}-seed{a.seed}-{step}')
        if segment['exit_code'] or segment['interrupted']:
            raise SystemExit('evaluation stopped; inspect retained segment and worker logs')
        evaluation = json.loads((folder / 'evaluation.json').read_text())
        repeated = evaluation['reload']
        if (not evaluation['complete'] or evaluation['iteration'] != step or
            evaluation['checkpoint_sha256'] != checkpoint_hash or repeated['compared'] != 13 or
            not all(repeated[k] for k in ('fresh_process', 'png_identical', 'float_identical', 'complete'))):
            raise ValueError('curve checkpoint reload validation failed')
        render = folder / 'first/render.json'
        report = json.loads(render.read_text())
        if len(report['frames']) != 350:
            raise ValueError('curve target coverage mismatch')
        record = dict(arm=a.arm, method=method, seed=a.seed, iteration=step,
            training_policy=a.training_policy, lifetime_policy=a.lifetime_policy,
            evaluation_split='training-observation' if a.training_policy == 'all-times' else 'heldout-camera',
            policy=policy_record(a.training_policy, a.lifetime_policy,
                                 .2 if a.lifetime_policy == 'repaired' else .2),
            checkpoint=str(checkpoint), checkpoint_sha256=checkpoint_hash, checkpoint_bytes=checkpoint.stat().st_size,
            render=str(render), render_sha256=digest(render), reload=repeated,
            rendering_fps=report['benchmark']['fps'], peak_allocated_bytes=report['peak_allocated_bytes'],
            peak_reserved_bytes=report['peak_reserved_bytes'], charged_seconds=segment['charged_seconds'])
        write_new(output / f'record-{step:06d}.json', record)
        print(json.dumps(dict(arm=a.arm, seed=a.seed, step=step, status='rendered and reload-verified')), flush=True)


if __name__ == '__main__':
    main()

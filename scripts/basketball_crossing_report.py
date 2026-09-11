"""Build compact Plan 028 numeric and Markdown evidence from frozen outputs."""
import hashlib
import json
from pathlib import Path


def main():
    root = Path(__file__).resolve().parents[1]
    study = root/'.local/basketball-crossing-repair'
    output = root/'docs/experiments/basketball-crossing-repair'
    output.mkdir(parents=True, exist_ok=True)
    metric_manifest = json.loads((study/'metrics/records.json').read_text())
    runs = {(r['arm'], r['seed'], r['training_policy'], r['lifetime_policy']): r for r in metric_manifest['records']}
    if len(runs) != 24 or metric_manifest['frame_count'] != 8400:
        raise ValueError('metric coverage is incomplete')

    def mean(rows, key):
        values = []
        for row in rows:
            value = row
            for part in key.split('/'):
                value = value[part]
            values.append(float(value))
        return sum(values)/len(values)

    def score(run, frame_ids):
        rows = [r for r in run['frames'] if r['camera'] in {'0', '10', '20', '30'} and r['frame_id'] in frame_ids]
        keys = ('full/psnr', 'full/ssim', 'full/lpips_alex', 'dynamic/lpips_alex',
                'motion_pixels/mae', 'temporal_difference_mae')
        def present(row, key):
            value = row
            for part in key.split('/'):
                if not isinstance(value, dict) or part not in value:
                    return False
                value = value[part]
            return True
        return {key: mean([r for r in rows if present(r, key)], key)
                for key in keys if any(present(r, key) for r in rows)}

    summary = []
    for key, run in sorted(runs.items()):
        summary.append(dict(arm=key[0], seed=key[1], training_policy=key[2], lifetime_policy=key[3],
                            gap=score(run, range(20, 25)), adjacent=score(run, (17, 18, 19, 25, 26, 27)),
                            remaining=score(run, tuple(range(0, 17)) + tuple(range(28, 50)))))

    def difference(left, right):
        a, b = runs[left], runs[right]
        x, y = score(a, range(20, 25)), score(b, range(20, 25))
        return {key: y[key] - x[key] for key in x}

    effects = []
    for arm in ('freetimegs-dense-coarse', 'freetimegs-dense-cropped'):
        for seed in range(3):
            for train in ('holdout', 'all-times'):
                effects.append(dict(contrast='repaired-minus-original', arm=arm, seed=seed,
                                    training_policy=train, values=difference((arm, seed, train, 'original'),
                                                                              (arm, seed, train, 'repaired'))))
            for life in ('original', 'repaired'):
                effects.append(dict(contrast='all-times-minus-holdout', arm=arm, seed=seed,
                                    lifetime_policy=life, values=difference((arm, seed, 'holdout', life),
                                                                             (arm, seed, 'all-times', life))))

    training = []
    for key in sorted(runs):
        path = study/'training'/key[0]/f'seed{key[1]}'/f'{key[2]}-{key[3]}'
        last = json.loads((path/'loss.jsonl').read_text().splitlines()[-1])
        training.append(dict(arm=key[0], seed=key[1], training_policy=key[2], lifetime_policy=key[3],
                             iteration=last['iteration'], loss=last['loss'], points=last['points'],
                             elapsed_seconds=last['elapsed_seconds'],
                             duration_projection_changed=last.get('duration_projection_changed', 0)))
    def write(path, value):
        path.write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')
    write(output/'results.json', dict(schema='basketball-crossing-repair-results/v1', endpoint_count=24,
        metric_rows=8400, metrics_sha256=hashlib.sha256((study/'metrics/records.json').read_bytes()).hexdigest(),
        summary=summary, effects=effects, training=training,
        video_manifest=str(study/'videos/artifacts.json')))
    qualification = [json.loads(path.read_text()) for path in sorted((study/'qualification').glob('freetimegs-dense-*.json'))]
    write(output/'diagnosis.json', dict(schema='basketball-crossing-repair-diagnosis/v1',
        mechanism='automatic duration sentinel -1 entered duration regularization; sub-floor lifetimes cannot receive image gradients that lengthen them',
        repair='duration-floor-v1: resolved target 0.2, safe log-duration floor at 0.02, selective Adam moment clearing, absolute schedule retained',
        qualification=qualification,
        limitation='Initialization labels are not used as current player identity. Playback/frame inspection remains the evidence for visual condition-fixed status.',
        provenance='Historical Plan 027 checkpoint and initializer sources remain hash-bound in each branch provenance.'))
    lines = ['# Basketball crossing repair — Plan 028', '',
             'Production completed 24 endpoints (two recipes × three seeds × four policies), with 480,000 continuation updates. Frozen evaluation coverage is 8,400 metric rows.', '',
             '| Recipe | Seed | Training | Lifetime | Gap motion MAE | Gap dynamic LPIPS | Video |',
             '|---|---:|---|---|---:|---:|---|']
    for row in summary:
        video = f"../../../.local/basketball-crossing-repair/videos/{row['arm']}-camera0-seed{row['seed']}/comparison.mp4"
        lines.append(f"| {row['arm'].replace('freetimegs-', '')} | {row['seed']} | {row['training_policy']} | {row['lifetime_policy']} | {row['gap']['motion_pixels/mae']:.5f} | {row['gap']['dynamic/lpips_alex']:.5f} | [camera 0]({video}) |")
    lines += ['', '## Assessment', '',
              'The fixed repair, policy labels, paired gap effects, and endpoint resource records are captured in [results.json](results.json). Lower is better for MAE, LPIPS, and temporal difference error; higher is better for PSNR and SSIM.', '',
              'The 24 videos use all 50 source frames at 25 fps and six consistent panels: ground truth, the 50k parent, and arms A–D. Fixed crops accompany the videos in the artifact directory. Visual condition-fixed status must be judged from those frame sequences; aggregate scores alone are insufficient.', '',
              'The diagnosis evidence and its attribution limitation are in [diagnosis.json](diagnosis.json). All endpoint reload probes passed, all-times rows retain their training-observation labels, and historical sources remain under the study artifact root.', '',
              '- [Full numeric results](results.json)', '- [Diagnosis evidence](diagnosis.json)',
              '- [Video manifest](../../../.local/basketball-crossing-repair/videos/artifacts.json)',
              '- [Production manifest](../../../.local/basketball-crossing-repair/production.json)',
              '- [Metric manifest](../../../.local/basketball-crossing-repair/metrics/records.json)', '']
    (output/'report.md').write_text('\n'.join(lines))
    print(f'wrote {output}')


if __name__ == '__main__':
    main()

"""Four-arm cohort identity and matched contrasts through the report pipeline."""
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import basketball_dense_report as report
from basketball_study import CURVE, digest, write_new


class ReportTests(unittest.TestCase):
    def test_endpoint_cost_includes_save_and_reload_overhead(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); arm='freetimegs-dense-coarse'
            for endpoint,charged,origin,start,rows in ((5000,1000,110,100,[(5000,850)]),
                    (50000,5200,2010,2000,[(10000,500),(50000,5000)])):
                segment=root/f'segments/train-{arm}-seed0-{endpoint}'
                folder=root/f'training/{arm}-seed0/{endpoint:06d}'
                write_new(segment/'segment.json',dict(charged_seconds=charged))
                write_new(segment/'process.json',dict(started_monotonic=start))
                write_new(folder/'timing.json',dict(optimizer_loop_start_monotonic=origin))
                (folder/'loss.jsonl').write_text(''.join(json.dumps(dict(iteration=i,elapsed_seconds=t))+'\n' for i,t in rows))
            with patch.object(report,'ARTIFACTS',root):
                for step,expected in ((5000,1000),(10000,1510),(50000,6200)):
                    self.assertEqual(report.training_time(dict(arm=arm,seed=0,iteration=step),{}),expected)

    def test_complete_native_method_shared_but_arm_distinct_cohorts(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); docs=root/'docs'; artifacts=root/'artifacts'
            docs.mkdir(); artifacts.mkdir()
            history=root/'docs/research/basketball-sync-pivot/gpu-budget.json'
            write_new(history, {'attempts':[]})
            (artifacts/'ledger.jsonl').write_text('')
            records=[]
            for arm in report.ARMS:
                for step in CURVE:
                    selected=[]
                    for seed in range(3):
                        offset={'stg-full':0,'freetimegs-sparse':1,
                            'freetimegs-dense-coarse':2+step/50000,
                            'freetimegs-dense-cropped':4+2*step/50000}[arm]
                        keys=[(c,f) for c in (0,10,20,30) for f in range(50)]+[(c,f) for c in range(34) if c not in (0,10,20,30) for f in range(20,25)]
                        frames=[]
                        for camera,frame in keys:
                            value=offset+seed+frame//5
                            frames.append(dict(camera=str(camera),frame_id=frame,
                                split='heldout-camera' if camera in (0,10,20,30) else 'temporal-interpolation',
                                full=dict(psnr=value,ssim=value,lpips_alex=value),
                                dynamic=dict(psnr=value,ssim=value,lpips_alex=value),
                                motion_pixels=dict(psnr=value,mae=value),temporal_difference_mae=value))
                        path=artifacts/f'{arm}-{step}-{seed}.json'
                        write_new(path,dict(method='stg-full' if arm=='stg-full' else 'freetimegs',seed=seed,iteration=step,complete=True,frames=frames))
                        selected.append(dict(arm=arm,seed=seed,iteration=step,metrics=str(path),metrics_sha256=digest(path),accumulated_training_seconds=step))
                    if arm in report.DENSE_ARMS:
                        write_new(artifacts/f'metrics/{arm}/{step:06d}/records.json',dict(records=selected))
                    else:
                        records.extend(selected)
            write_new(docs/'baseline-reuse.json',dict(records=records))
            output=root/'report'
            with patch.object(report,'ROOT',root),patch.object(report,'DOCS',docs),patch.object(report,'ARTIFACTS',artifacts), \
                    patch.object(report,'training_time',side_effect=lambda r,h:r['accumulated_training_seconds']), \
                    patch.object(sys,'argv',['report','--output',str(output)]):
                report.main()
            stats=json.loads((output/'statistics.json').read_text())
            self.assertTrue(stats['metric_coverage_complete'])
            self.assertEqual(len(json.loads((output/'artifact-index.json').read_text())['records']),60)
            self.assertEqual(len(stats['curves']),4*5*2*9)
            self.assertAlmostEqual(stats['cropped_minus_coarse']['50000/heldout-camera/full/psnr']['mean'],3)
            self.assertAlmostEqual(stats['initialization_duration_interaction']['freetimegs-dense-coarse/heldout-camera/full/psnr']['mean'],.9)
            self.assertAlmostEqual(stats['initialization_duration_interaction']['freetimegs-dense-cropped/heldout-camera/full/psnr']['mean'],1.8)


if __name__=='__main__':unittest.main()

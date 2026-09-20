import copy
import io
import json
from pathlib import Path
import sys
import tarfile
import tempfile
import types
import unittest
from unittest.mock import patch

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from vipe_benchmark.access import Identity
from vipe_benchmark.config import load
from vipe_benchmark.files import file_record, read_json, write_json
from vipe_benchmark.ledger import Ledger
from vipe_benchmark.runtime import extract_source
from vipe_benchmark.stages import segment
from vipe_benchmark.execution import aggregate_record, result_artifact, result_record, qualify_existing, execute_matrix
from vipe_benchmark.supervisor import SupervisionFailure


class FrozenHandoffTests(unittest.TestCase):
    def test_completed_report_is_returned_without_readmission_or_another_pass(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            folder = root / 'jobs/report'
            folder.mkdir(parents=True)
            (folder / 'report.md').write_text('Frozen fixture report.')
            document = dict(status='complete', report=file_record(folder / 'report.md'))
            write_json(folder / 'result.json', document)
            ledger = Ledger(root / 'ledger.jsonl', load())
            ledger.reserve('report', ['fixture'], {})
            ledger.finish('report', 'complete', 1., result=file_record(folder / 'result.json'))
            with patch('vipe_benchmark.execution.common_admission', side_effect=AssertionError('no second admission')):
                self.assertEqual(execute_matrix(root, root / 'docs', load(), None), document)
            self.assertEqual(ledger.totals()['cpu']['attempts'], 1)

    def test_worker_error_cannot_override_supervisor_exclusivity_stop(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            write_json(root / 'jobs/S0-calibration/failure.json', dict(requires_permission_review=False))
            with (patch('vipe_benchmark.execution.common_admission', return_value=dict(status='admitted')),
                    patch('vipe_benchmark.execution.execution_order', return_value=['S0-calibration']),
                    patch('vipe_benchmark.execution.make_request', return_value=(dict(job_id='S0-calibration'), [])),
                    patch('vipe_benchmark.execution.dispatch', side_effect=SupervisionFailure(
                        'exclusive GPU access lost', kind='gpu_exclusivity', stop_required=True)) as dispatch):
                with self.assertRaisesRegex(SupervisionFailure, 'exclusive GPU'):
                    execute_matrix(root, root / 'docs', load(), None)
                self.assertEqual(dispatch.call_count, 1)

    def test_orphaned_passing_scale_cannot_admit_check_and_completed_scale_cannot_change(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            folder = root / 'jobs/D0-fit'
            write_json(folder / 'scale.json', dict(status='passed'))
            write_json(folder / 'result.json', dict(status='complete', scale=file_record(folder / 'scale.json')))
            self.assertIsNone(result_record(root, 'D0-fit'))
            self.assertIsNone(result_artifact(root, 'D0-fit', 'scale'))
            ledger = Ledger(root / 'ledger.jsonl', load())
            ledger.reserve('D0-fit', ['fixture'], {})
            ledger.finish('D0-fit', 'complete', 1., result=file_record(folder / 'result.json'))
            self.assertEqual(result_artifact(root, 'D0-fit', 'scale')['sha256'], file_record(folder / 'scale.json')['sha256'])
            (folder / 'scale.json').write_text('{"status": "passed", "scale": 999}')
            with self.assertRaisesRegex(ValueError, 'changed file'):
                result_artifact(root, 'D0-fit', 'scale')

    def test_annotation_result_and_aggregate_checkpoint_bind_successful_parent(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            ledger = Ledger(root / 'ledger.jsonl', load())
            write_json(root / 'annotations/annotations.json', dict(status='reviewed-proxy'))
            write_json(root / 'annotations/result.json', dict(status='complete', annotations=file_record(root / 'annotations/annotations.json')))
            ledger.reserve('annotations', ['fixture'], {})
            ledger.finish('annotations', 'complete', 1., result=file_record(root / 'annotations/result.json'))
            self.assertIsNotNone(result_artifact(root, 'annotations', 'annotations'))
            folder = root / 'jobs/aggregate-masks'
            write_json(folder / 'metrics.json', dict(status='complete'))
            write_json(folder / 'result.json', dict(status='complete', evidence=file_record(folder / 'metrics.json')))
            self.assertIsNone(aggregate_record(root, 'masks'))
            ledger.reserve('aggregate', ['fixture'], {})
            ledger.checkpoint('aggregate', 1., result=file_record(folder / 'result.json'))
            self.assertEqual(aggregate_record(root, 'masks', artifact=True), file_record(folder / 'metrics.json'))
            (folder / 'result.json').write_text('{"status": "complete"}')
            with self.assertRaisesRegex(ValueError, 'changed file'):
                aggregate_record(root, 'masks')

    def test_failed_readonly_qualification_still_charges_elapsed_cpu(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            with patch('vipe_benchmark.execution._qualify_existing', side_effect=ValueError('fixture mismatch')):
                with self.assertRaisesRegex(ValueError, 'fixture mismatch'):
                    qualify_existing(root, root / 'docs', load())
            ledger = Ledger(root / 'ledger.jsonl', load())
            self.assertGreater(ledger.totals()['cpu']['elapsed_seconds'], 0)
            self.assertEqual(ledger.totals()['cpu']['attempts'], 0)
            self.assertEqual(read_json(root / 'qualification/result.json')['status'], 'failed')


class AtomicEvidenceTests(unittest.TestCase):
    def test_invalid_json_never_publishes_partial_evidence(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'receipt.json'
            with self.assertRaises(ValueError):
                write_json(path, dict(bytes_received=float('nan')))
            self.assertFalse(path.exists())
            write_json(path, dict(bytes_received=10))
            with self.assertRaises(FileExistsError):
                write_json(path, dict(bytes_received=0))
            self.assertEqual(read_json(path), dict(bytes_received=10))
            self.assertEqual(list(Path(temp).iterdir()), [path])


class CheckpointTests(unittest.TestCase):
    def test_three_stages_consume_one_aggregate_attempt_and_charge_only_active_wall(self):
        with tempfile.TemporaryDirectory() as temp:
            ledger = Ledger(Path(temp) / 'ledger.jsonl', load())
            ledger.reserve('aggregate', ['stage1'], {})
            ledger.checkpoint('aggregate', 2., result={'stage': 'masks'})
            ledger.reserve('N0', ['neighbors'], {})
            ledger.finish('N0', 'complete', 1.)
            ledger.resume_checkpoint('aggregate', ['stage2'], {})
            ledger.checkpoint('aggregate', 3., result={'stage': 'finalists'})
            ledger.resume_checkpoint('aggregate', ['stage3'], {})
            ledger.finish('aggregate', 'complete', 4.)
            self.assertEqual(ledger.totals()['cpu']['attempts'], 1)
            self.assertEqual(ledger.totals()['cpu']['elapsed_seconds'], 9.)
            with self.assertRaisesRegex(ValueError, 'no frozen'):
                ledger.resume_checkpoint('aggregate', [], {})

    def test_model_attempts_cannot_use_aggregation_resume(self):
        with tempfile.TemporaryDirectory() as temp:
            ledger = Ledger(Path(temp) / 'ledger.jsonl', load())
            ledger.reserve('S0-calibration', ['fixture'], {})
            with self.assertRaisesRegex(ValueError, 'only aggregation'):
                ledger.checkpoint('S0-calibration', 1.)
            with self.assertRaisesRegex(ValueError, 'only the aggregation'):
                ledger.resume_checkpoint('S0-calibration', [], {})


class SourceArchiveTests(unittest.TestCase):
    def test_revision_and_path_traversal_are_checked_before_extracting(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            archive = root / 'source.tar.gz'
            revision = 'a' * 40
            with tarfile.open(archive, 'w:gz') as stream:
                for name in [f'source-{revision}/module.py', f'source-{revision}/../escape.py']:
                    member = tarfile.TarInfo(name)
                    member.size = 1
                    stream.addfile(member, io.BytesIO(b'0'))
            with self.assertRaisesRegex(ValueError, 'unsafe'):
                extract_source(archive, root / 'out', revision)
            self.assertFalse((root / 'escape.py').exists())


class SegmentationWorkerTests(unittest.TestCase):
    def test_worker_retains_grid_identity_and_validates_first_output_before_continuing(self):
        import cv2
        from vipe_benchmark.backends import SegmentationResult
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            valid = np.ones((540, 960), bool)
            np.save(root / 'valid.npy', valid)
            cv2.imwrite(str(root / 'rgb.png'), np.zeros((540, 960, 3), np.uint8))
            image = file_record(root / 'rgb.png')
            footprint = file_record(root / 'valid.npy')
            rows = [dict(identity=Identity('calibration', 1, f).record(), rgb=image, valid=footprint,
                         K=np.eye(3).tolist(), grid='distorted-opencv-integer') for f in (100, 101)]
            write_json(root / 'inputs.json', dict(rgb=rows))
            labels = np.zeros(valid.shape, np.int32)
            labels[20:25, 30:35] = 1
            result = SegmentationResult(labels, {'1': {'class': 'person', 'native_class': 'person', 'score': .9}}, valid, {})
            backend = types.SimpleNamespace(segment=lambda *a, **k: [result])
            cuda = types.SimpleNamespace(synchronize=lambda: None, max_memory_allocated=lambda: 0,
                                          max_memory_reserved=lambda: 0)
            request = dict(component='S1', branch='calibration', job_id='S1-calibration',
                           inputs=file_record(root / 'inputs.json'), assets={})
            with patch.dict(sys.modules, {'torch': types.SimpleNamespace(cuda=cuda)}), \
                    patch('vipe_benchmark.stages._model_runtime', return_value={}), \
                    patch('vipe_benchmark.stages.output_identities', return_value=[Identity('calibration', 1, 100)]), \
                    patch('vipe_benchmark.backends.build_backend', return_value=backend):
                segment(request, root / 'result', load())
                doc = read_json(root / 'result/result.json')
                self.assertEqual(doc['rows'][0]['source_rgb_sha256'], image['sha256'])
                self.assertEqual(doc['rows'][0]['identity']['frame'], 100)
                self.assertTrue((root / 'result/first-result-qualification.json').is_file())
                backend.segment = lambda *a, **k: []
                with self.assertRaisesRegex(ValueError, 'missing singleton'):
                    segment(request, root / 'bad-result', load())
                self.assertFalse((root / 'bad-result/result.json').exists())





# Literal ordered callback contract consumed without importing this module.
SUBTEST_CASES = {
}


if __name__ == '__main__':
    unittest.main()

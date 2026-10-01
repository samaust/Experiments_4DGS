"""Pure S1 retry identity and immutable clock boundaries; no GPU dispatch."""
from pathlib import Path
import copy
import contextlib
import io
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from vipe_benchmark.s1_identity import is_recovery_job, is_standing_retry_job, job_from_attempt, prior_job


class IdentityTests(unittest.TestCase):
    def test_canonical_fresh_identities_continue_beyond_three_digits(self):
        for attempt, job, previous in (
            (1, 'S1-calibration-recovery-001', None),
            (9, 'S1-calibration-recovery-009', 'S1-calibration-recovery-008'),
            (10, 'S1-calibration-recovery-010', 'S1-calibration-recovery-009'),
            (1000, 'S1-calibration-recovery-1000', 'S1-calibration-recovery-999'),
        ):
            with self.subTest(job=job):
                self.assertEqual(job_from_attempt(attempt), job)
                self.assertTrue(is_recovery_job(job))
                self.assertEqual(is_standing_retry_job(job), attempt >= 10)
                self.assertEqual(prior_job(job), previous)
        for job in (None, 10, '', 'S1-calibration-recovery-000', 'S1-calibration-recovery-10',
                    'S1-calibration-recovery-0010', 'S1-calibration-recovery-010\n',
                    'S1-reconstruction-recovery-010', 'S1-calibration-recovery-+10'):
            with self.subTest(invalid=job):
                self.assertFalse(is_recovery_job(job))
                self.assertFalse(is_standing_retry_job(job))
                with self.assertRaises(ValueError):prior_job(job)
        for attempt in (True, False, 0, -1, 10., '10'):
            with self.assertRaises(ValueError):job_from_attempt(attempt)

    def test_fresh_reservation_clock_retains_finite_immutable_window(self):
        from vipe_benchmark.s1_clock import ReservationClock
        from vipe_benchmark.s1_progress import checked_clock_mapping
        from vipe_benchmark.files import file_record
        temporary=tempfile.TemporaryDirectory();self.addCleanup(temporary.cleanup)
        request=Path(temporary.name)/'request.json';request.write_text('{}')
        mapping=dict(schema='plan041-s1-reservation-clock/v1',job_id='S1-calibration-recovery-010',
            request=file_record(request),
            reservation=dict(sequence=580,event_sha256='b'*64),boot_id='fixture-boot',
            monotonic_start=100.,effective_seconds=3600.,cleanup_reserve_seconds=30.,
            total_deadline=3700.,work_deadline=3670.)
        self.assertEqual(ReservationClock.from_mapping(mapping).mapping(),mapping)
        self.assertEqual(checked_clock_mapping(mapping).mapping(),mapping)
        for change in (dict(job_id='S1-calibration-recovery-0010'),dict(effective_seconds=3601.),
                       dict(work_deadline=3700.),dict(cleanup_reserve_seconds=0.)):
            changed=copy.deepcopy(mapping);changed.update(change)
            for validate in (ReservationClock.from_mapping,checked_clock_mapping):
                with self.assertRaises(ValueError):validate(changed)

    def test_component_recovery_cli_accepts_fresh_canonical_jobs(self):
        from basketball_vipe_benchmark import argument_parser
        parser=argument_parser()
        for job in ('S1-calibration-recovery-001','S1-calibration-recovery-009',
                    'S1-calibration-recovery-010','S1-calibration-recovery-1000'):
            args=parser.parse_args(['--run-id','fixture','component-recovery','--job',job,
                                   '--authorization','/tmp/frozen-review.json'])
            self.assertEqual(args.job,job)
        with contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit):
                parser.parse_args(['--run-id','fixture','component-recovery','--job',
                    'S1-calibration-recovery-0010','--authorization','/tmp/frozen-review.json'])

    def test_fresh_rows_require_frozen_compact_asset_provenance(self):
        from vipe_benchmark.s1_evidence import check_compact_asset_provenance
        from vipe_benchmark.backends import REQUIRED_ASSETS
        from vipe_benchmark.files import object_hash
        assets={name:dict(sha256='a'*64) for name in REQUIRED_ASSETS['S1']}
        request=dict(job_id='S1-calibration-recovery-010',assets=assets)
        for metadata in ({},{'assets_sha256':'changed'},
                         {'assets_sha256':object_hash(assets),'assets':assets}):
            with self.assertRaisesRegex(ValueError,'compact asset provenance'):
                check_compact_asset_provenance(dict(metadata=metadata),request)
        check_compact_asset_provenance(dict(metadata=dict(assets_sha256=object_hash(assets))),request)
        # Historical001–003 retain their original expanded-provenance contract.
        check_compact_asset_provenance(dict(metadata={}),dict(request,job_id='S1-calibration-recovery-003'))

    def test_fresh_worker_routes_clock_and_preserves_failure_evidence(self):
        from unittest.mock import patch
        import basketball_vipe_worker as worker
        from vipe_benchmark.config import load
        from vipe_benchmark.files import file_record, read_json, write_json
        from vipe_benchmark import s1_evidence, s1_recovery, stages
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);configuration=root/'config.json';write_json(configuration,load())
            request=dict(job_id='S1-calibration-recovery-010',configuration=file_record(configuration))
            request_path=root/'request.json';write_json(request_path,request)
            proof_path=root/'fixture-evidence.json';write_json(proof_path,dict(record_kind='fixture'))
            proof=file_record(proof_path)
            # Only worker routing is exercised. Fake operations construct no
            # model and do not claim a qualified clock, result or native output.
            clock=object();observed=[]
            def operation(supplied,output,config,*,clock=None):
                observed.append((supplied,output,clock))
                if output.name=='failed':raise ValueError('fixture worker failure')
            def preserve(supplied,output,identity,error,*,stage,clock=None):
                self.assertIs(clock,expected_clock)
                error.s1_failure_record=proof;error.s1_first_result=proof
            expected_clock=clock
            for outcome in ('complete','failed'):
                output=root/outcome
                argv=['worker','--config',str(configuration),'--request',str(request_path),
                      '--output',str(output),'--operation','component']
                with patch.object(sys,'argv',argv),patch.object(s1_recovery,'worker_clock',return_value=clock), \
                     patch.object(stages,'run',operation),patch.object(s1_evidence,'preserve_failure',preserve):
                    if outcome=='failed':
                        with self.assertRaisesRegex(ValueError,'fixture worker failure'):worker.main()
                        failure=read_json(output/'failure.json')
                        self.assertEqual(failure['failure_evidence'],proof)
                        self.assertEqual(failure['first_result'],proof)
                        self.assertEqual(failure['job_id'],request['job_id'])
                    else:worker.main()
                self.assertEqual(observed[-1],(request,output,clock))


SUBTEST_CASES = {
    'test_vipe_benchmark_s1_identity.IdentityTests.test_canonical_fresh_identities_continue_beyond_three_digits': [
        {'job': 'S1-calibration-recovery-001'},
        {'job': 'S1-calibration-recovery-009'},
        {'job': 'S1-calibration-recovery-010'},
        {'job': 'S1-calibration-recovery-1000'},
        {'invalid': None}, {'invalid': 10}, {'invalid': ''},
        {'invalid': 'S1-calibration-recovery-000'},
        {'invalid': 'S1-calibration-recovery-10'},
        {'invalid': 'S1-calibration-recovery-0010'},
        {'invalid': 'S1-calibration-recovery-010\n'},
        {'invalid': 'S1-reconstruction-recovery-010'},
        {'invalid': 'S1-calibration-recovery-+10'},
    ],
}


if __name__ == '__main__':unittest.main()

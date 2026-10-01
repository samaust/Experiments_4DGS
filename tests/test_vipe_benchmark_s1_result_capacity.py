"""Real CPU aggregate readback, progress publication and closed inventory."""
import copy
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from vipe_benchmark import s1_progress as progress
from vipe_benchmark.access import output_identities
from vipe_benchmark.config import load
from vipe_benchmark.files import file_record, write_json
from test_vipe_benchmark_s1_helper_fixtures import progress_fixture, plan047_state

SUBTEST_CASES = {}


class S1ResultCapacityTests(unittest.TestCase):
    def test_full_aggregate_publication_inventory_and_hash_binding(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            fixture = progress_fixture(root / 'fixture')
            with plan047_state(fixture, root / 'state', qualified=False) as state:
                publisher = progress.Publisher(state.reference, 'reconcile', 1, clock=state.clock, request=fixture['request'])
                self.addCleanup(publisher.close)
                row = copy.deepcopy(fixture['rows'][0])
                row['metadata']['capacity_fixture'] = ['x' * 1024] * 64 + [0] * 2048
                rows = [dict(row, identity=identity.record()) for identity in output_identities(load(), 'calibration')]
                rows[0] = copy.deepcopy(fixture['rows'][0])
                result = dict(rows=rows, status='complete')
                output = root / 'output'
                write_json(output / 'result.json', result)
                result_record = file_record(output / 'result.json')
                self.assertGreater(result_record['bytes'], 35 * 1024 * 1024)
                acceptance = output / 'acceptance.json'
                write_json(acceptance, dict(result=result_record, status='passed', count=510))
                candidates, inventory = progress.candidate_inventory(output, result, state.clock.work_deadline)
                self.assertEqual(len(candidates), 510)
                inventory.recheck(state.clock.work_deadline)
                progress.accepted_progress(publisher, result, result_record, file_record(acceptance))
                trusted = progress.recover(state.cache.reference())
                self.assertTrue(trusted['scan_complete'])
                self.assertEqual(trusted['counts']['qualified'], 510)
                self.assertEqual(trusted['runtime']['final'], result_record)
                with (output / 'result.json').open('ab') as stream:
                    stream.write(b' ')
                with self.assertRaisesRegex(ValueError, 'content mutation'):
                    inventory.recheck(state.clock.work_deadline)
                with self.assertRaisesRegex(ValueError, 'accepted result bytes'):
                    progress.accepted_progress(publisher, result, result_record, file_record(acceptance))
                with (output / 'result.json').open('r+b') as stream:
                    stream.truncate(progress.MAX_RESULT_BYTES + 1)
                with self.assertRaisesRegex(ValueError, 'regular file capacity'):
                    progress.accepted_progress(publisher, result, result_record, file_record(acceptance))
                with self.assertRaisesRegex(ValueError, 'regular file capacity'):
                    inventory.recheck(state.clock.work_deadline)

    def test_aggregate_capacity_remains_finite_before_reading_payload(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / 'result.json'
            with path.open('wb') as stream:
                stream.truncate(510 * 256 * 1024 + 32 * 1024 * 1024 + 1)
            with self.assertRaisesRegex(ValueError, 'regular file capacity'):
                progress.candidate_inventory(root, None, None)

    def test_row_and_envelope_caps_are_independent_of_aggregate_capacity(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            row = dict(values=['x' * 1024] * 256)
            write_json(root / 'result.json', dict(rows=[row]))
            with self.assertRaisesRegex(ValueError, 'byte capacity'):
                progress.candidate_inventory(root, None, None)
            envelope = dict(rows=[], extra=['x' * 1024] * (32 * 1024 + 1))
            (root / 'result.json').unlink()
            write_json(root / 'result.json', envelope)
            with self.assertRaisesRegex(ValueError, 'envelope capacity'):
                progress.candidate_inventory(root, None, None)
            (root / 'result.json').unlink()
            write_json(root / 'result.json', dict(rows=[dict(values=[None] * 65536)]))
            with self.assertRaisesRegex(ValueError, 'primitive capacity'):
                progress.candidate_inventory(root, None, None)
            (root / 'result.json').unlink()
            write_json(root / 'result.json', dict(rows=[], values=[None] * 1048576))
            with self.assertRaisesRegex(ValueError, 'primitive capacity'):
                progress.candidate_inventory(root, None, None)


if __name__ == '__main__':
    unittest.main()

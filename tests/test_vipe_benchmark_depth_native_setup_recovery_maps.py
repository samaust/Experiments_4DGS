"""D8 maps admission accepts only the accepted recovered setup (CPU fixtures)."""
import os
import unittest
from pathlib import Path
from unittest.mock import patch

from test_vipe_benchmark_depth_native_setup_recovery import JOB, ORIGINAL
from test_vipe_benchmark_depth_native_setup_recovery_run import NativeSetupRecoveryRunTests
from vipe_benchmark.config import load
from vipe_benchmark.files import file_record, read_json


class RecoveredSetupMapsTests(NativeSetupRecoveryRunTests):
    """Runner tests are inherited only as fixture helpers; they are not re-collected."""

    def completed_recovery(self):
        from vipe_benchmark.ledger import Ledger
        self.run_worker()
        ledger = Ledger(self.run_root / 'ledger.jsonl', dict(load(), new_download_gib_limit=110,
                                                              new_artifact_disk_gib_limit=210))
        record = file_record(self.run_root / 'jobs' / JOB / 'result.json')
        ledger.finish(JOB, 'complete', 30., result=record, cleanup_confirmed=True, cleanup_uncertain=False,
                      surviving_pids=[])
        return ledger, record

    def test_accepted_setup_selects_the_completed_recovery(self):
        from vipe_benchmark.setup_recovery_core import accepted_setup
        ledger, record = self.completed_recovery()
        result, job = accepted_setup('D8', record, ledger.events(), self.run_root)
        self.assertEqual((job, result['schema']), (JOB, 'plan069-depth-setup-recovery-result/v1'))

    def test_failed_original_setup_is_never_admissible(self):
        from vipe_benchmark.setup_recovery_core import accepted_setup
        ledger, _ = self.completed_recovery()
        failure = file_record(self.run_root / 'jobs' / ORIGINAL / 'failure.json')
        with self.assertRaises(ValueError):
            accepted_setup('D8', failure, ledger.events(), self.run_root)

    def test_unfinished_recovery_is_not_admissible(self):
        from vipe_benchmark.config import load as config
        from vipe_benchmark.ledger import Ledger
        from vipe_benchmark.setup_recovery_core import accepted_setup
        self.run_worker()
        record = file_record(self.run_root / 'jobs' / JOB / 'result.json')
        events = Ledger(self.run_root / 'ledger.jsonl', dict(config(), new_download_gib_limit=110,
                                                              new_artifact_disk_gib_limit=210)).events()
        with self.assertRaises(ValueError):
            accepted_setup('D8', record, events, self.run_root)

    def test_map_allowance_credits_the_recovered_checkpoint_once(self):
        from vipe_benchmark.depth_map_allowance import remaining_map_allocation
        ledger, record = self.completed_recovery()
        result = read_json(record['path'])
        with patch('vipe_benchmark.depth_map_allowance.verify_record', side_effect=lambda row: row):
            stage = remaining_map_allocation(self.maps, record, ledger.events(), self.run_root, result['assets'])
        credit = result['assets'][0]['record']['bytes']
        self.assertEqual(stage['credited_assets_bytes'], credit)
        self.assertEqual(stage['allocation']['download_bytes'], self.maps['allocation']['download_bytes'] - credit)
        self.assertEqual(stage['recovery_lineage']['job_id'], JOB)

    def test_slot_budget_binds_the_recovered_stage_and_counts_hardlinks_once(self):
        from vipe_benchmark.depth_map_allowance import bind_slot_byte_budget, owned_slot_bytes
        ledger, record = self.completed_recovery()
        result = read_json(record['path'])
        original_runtime = self.run_root / 'jobs' / ORIGINAL / 'runtime' / 'shared.bin'
        original_runtime.write_bytes(b'x' * 4096)
        os.link(original_runtime, self.run_root / 'jobs' / JOB / 'shared-link.bin')
        with patch('vipe_benchmark.depth_map_allowance.verify_record', side_effect=lambda row: row):
            from vipe_benchmark.depth_map_allowance import remaining_map_allocation
            stage = remaining_map_allocation(self.maps, record, ledger.events(), self.run_root, result['assets'])
        marker = stage['recovery_lineage']
        separate = owned_slot_bytes(self.run_root, 'D8')
        united = owned_slot_bytes(self.run_root, 'D8', recovery_lineage=marker)
        self.assertLessEqual(separate - united, 4096)
        self.assertGreaterEqual(separate - united, 4096 - 512)
        reading = dict(download_bytes=10, artifact_bytes=20 + united)
        budget = bind_slot_byte_budget(self.maps, stage, ledger.events(), self.run_root, reading)
        self.assertEqual(budget['recovery_lineage'], marker)
        tampered = dict(stage, recovery_lineage=dict(marker, finish_event_sha256='0' * 64))
        with self.assertRaises(ValueError):
            bind_slot_byte_budget(self.maps, tampered, ledger.events(), self.run_root, reading)

    def test_byte_reconciliation_refuses_a_recovered_d8_setup(self):
        from vipe_benchmark.depth_budget_reconciliation import prepare_reconciliation
        ledger, _ = self.completed_recovery()
        with self.assertRaisesRegex(ValueError, 'not defined for this recovered candidate'):
            prepare_reconciliation(self.run_root, 'D8', ledger.events())


for name in [n for n in vars(NativeSetupRecoveryRunTests) if n.startswith('test_')]:
    setattr(RecoveredSetupMapsTests, name, None)

if __name__ == '__main__':
    unittest.main()

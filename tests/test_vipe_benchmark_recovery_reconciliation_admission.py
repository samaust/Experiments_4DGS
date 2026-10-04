"""Exact immutable historical owner alias; no shared state or execution."""
import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch

PATH = Path(__file__).resolve().parents[1] / 'docs/research/vipe-alternatives/plan069-D9-recovery-causal-001/prepare_reconciliation_admission.py'
spec = importlib.util.spec_from_file_location('recovery_admission_producer', PATH)
assert spec and spec.loader
producer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(producer)


class HistoricalPreservationChargeTests(unittest.TestCase):
    def setUp(self):
        self.evidence = dict(path='/home/auss/git_repos/samaust/Experiments_4DGS/.local/plan069-worktrees/'
            'depth-extension/.local/D9-frame-recovery-outcome-001/preservation-receipt.json',
            sha256='f15273481e8a19f2abddc8bd9d705f0b400df8197c6e9a77d61d84740e71c6fe', bytes=1715)
        self.event = dict(sequence=785, event='cpu_preparation_charge', resource='cpu',
            event_sha256='287a285eb7b2dc231f251b477ac9c27476686e0abb57d43ba5bc2fd2dce48017',
            evidence=self.evidence, elapsed_seconds=30.002395444000285)
        self.document = dict(schema='plan069-cpu-preservation/v1', record_kind='actual', cpu_preparation_owner='D9')

    def owner(self, event):
        with patch.object(producer, 'record', return_value=self.evidence), \
             patch.object(producer, 'read', return_value=self.document):
            return producer.preservation_charge_owner(event)

    def test_exact_retained_785_is_consumed_d9_cpu(self):
        self.assertEqual(self.owner(self.event), 'D9')
        self.assertEqual(self.event['elapsed_seconds'], 30.002395444000285)

    def test_no_generic_owner_alias(self):
        self.assertIsNone(self.owner(dict(self.event, sequence=786)))

    def test_mutated_event_or_receipt_rejected(self):
        for key, value in [('event', 'note'), ('resource', 'setup'), ('event_sha256', 'forged'),
                           ('evidence', {}), ('elapsed_seconds', 0)]:
            with self.subTest(key=key), self.assertRaisesRegex(ValueError, 'exact protected historical'):
                self.owner(dict(self.event, **{key: value}))
        self.document['cpu_preparation_owner'] = 'D6'
        with self.assertRaisesRegex(ValueError, 'exact historical D9'):
            self.owner(self.event)

    def test_changed_retained_receipt_bytes_rejected(self):
        with patch.object(producer, 'record', return_value=dict(self.evidence, sha256='changed')):
            with self.assertRaisesRegex(ValueError, 'exact protected historical'):
                producer.preservation_charge_owner(self.event)

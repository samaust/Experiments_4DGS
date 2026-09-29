from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from vipe_benchmark.config import load
from vipe_benchmark.files import file_record, object_hash, write_json
from vipe_benchmark.ledger import Ledger
from vipe_benchmark.licenses import assess, subject_manifest


class LicenseEvidenceTests(unittest.TestCase):
    def fixture(self, root):
        write_json(root / 'inventory.json', dict(packages=[dict(name='fixture', version='1', files=[])]))
        (root / 'LICENSE').write_text('Synthetic evidence fixture; no real permission inference.')
        qualification = dict(runtime=dict(inventory=file_record(root / 'inventory.json')), assets={})
        manifest = subject_manifest('M0', qualification)
        review = dict(component='M0', subject_manifest_sha256=object_hash(manifest),
                      reviewer='fixture-only', reviewed_utc='2026-09-13T00:00:00Z', subjects={})
        return qualification, manifest, review

    def test_model_level_flag_cannot_substitute_for_reviewed_dependency_closure(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            qualification, _, review = self.fixture(root)
            qualification['commercial_permission'] = 'verified'
            self.assertEqual(assess(root, 'M0', qualification)['commercial_permission'], 'unverified')
            write_json(root / 'review.json', review)
            Ledger(root / 'ledger.jsonl', load()).note('license_assessment', component='M0', evidence=file_record(root / 'review.json'))
            with self.assertRaisesRegex(ValueError, 'closure subjects'):
                assess(root, 'M0', qualification)

    def test_restriction_and_exact_inventory_change_propagate(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            qualification, manifest, review = self.fixture(root)
            review['subjects'] = {key: dict(commercial_permission='restricted', non_agpl='verified',
                reason='fixture restriction', evidence=[file_record(root / 'LICENSE')]) for key in manifest['subjects']}
            write_json(root / 'review.json', review)
            Ledger(root / 'ledger.jsonl', load()).note('license_assessment', component='M0', evidence=file_record(root / 'review.json'))
            result = assess(root, 'M0', qualification)
            self.assertEqual(result['commercial_permission'], 'restricted')
            self.assertEqual(result['non_agpl'], 'verified')
            write_json(root / 'changed-inventory.json', dict(packages=[dict(name='fixture', version='2', files=[])]))
            qualification['runtime']['inventory'] = file_record(root / 'changed-inventory.json')
            with self.assertRaisesRegex(ValueError, 'exact current assets'):
                assess(root, 'M0', qualification)


if __name__ == '__main__':
    unittest.main()

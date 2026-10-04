"""A refreshed source review is checked before a one-use setup has side effects."""
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import basketball_vipe_depth_setup_other_dispatch as dispatcher
from vipe_benchmark.files import file_record, write_json


class OtherSetupDispatchTests(unittest.TestCase):
    def test_current_review_selection_precedes_request_and_authorization(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            review = root / 'refreshed-review.json'
            source = root / 'worker.py'
            source.write_text('# fixture source\n')
            records = [file_record(source)]
            proposal = dict(candidate_config=dict(code=dict(revision='pinned')),
                            profile_inventory={'fixture': 'profile'})
            document = dict(schema='plan069-depth-source-review/v1', status='passed',
                candidate='D8', source_revision='pinned', reviewer='independent fixture',
                profile_inventory={'fixture': 'profile'}, local_sources=records)
            ledger = Mock(path=root / 'ledger.jsonl')
            original_read_text = Path.read_text
            def read_text(path, *args, **kwargs):
                if str(path) == '/proc/1/comm':
                    return 'systemd\n'
                return original_read_text(path, *args, **kwargs)
            with patch.object(dispatcher, 'ROOT', root), \
                    patch.object(Path, 'read_text', read_text), \
                    patch.object(dispatcher, 'shared_run_root', return_value=root), \
                    patch.object(dispatcher, 'Ledger', return_value=ledger), \
                    patch.object(dispatcher, 'execution_authorization',
                                 return_value=({}, {}, proposal, {})), \
                    patch.object(dispatcher, 'local_source_records', return_value=records, create=True), \
                    patch.object(dispatcher, 'recipe', return_value={'fixture': 'recipe'}), \
                    patch.object(dispatcher, 'resources', side_effect=RuntimeError('fixture reached live gate')):
                write_json(review, document)
                with self.assertRaisesRegex(RuntimeError, 'live gate'):
                    dispatcher.dispatch('D8', 'plan031-20260913T032700Z',
                                        source_review_path=review)
                self.assertFalse((root / '.local/vipe-alternatives/plan031-20260913T032700Z/requests').exists())
                ledger.authorize_depth_setup.assert_not_called()
                for key, value in (('schema', 'wrong'), ('status', 'failed'),
                                   ('candidate', 'D11'), ('source_revision', 'wrong'),
                                   ('reviewer', ''), ('profile_inventory', {}), ('local_sources', [])):
                    with self.subTest(field=key):
                        invalid = root / f'invalid-{key}.json'
                        write_json(invalid, dict(document, **{key: value}))
                        with self.assertRaisesRegex(ValueError, 'current independent'):
                            dispatcher.dispatch('D8', 'plan031-20260913T032700Z', source_review_path=invalid)
                        ledger.authorize_depth_setup.assert_not_called()
                with self.assertRaises(FileNotFoundError):
                    dispatcher.dispatch('D8', 'plan031-20260913T032700Z',
                                        source_review_path=root / 'missing.json')


if __name__ == '__main__':
    unittest.main()

"""Socket-free checks of completed transfer evidence; no UV commands are run."""
from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from vipe_benchmark.files import write_json


class UVReceiptBindingTests(unittest.TestCase):
    def test_exact_completed_proxy_receipt_is_available_for_binding(self):
        from vipe_benchmark.transfer_proxy import completed_uv_receipt
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            transfer_id='a'*32
            path=root/'uv-transfers'/f'transfer-{transfer_id}.json'
            path.parent.mkdir()
            write_json(path,dict(transfer_id=transfer_id,complete=True,error=None,
                bytes_received=17,reserved_bytes=0))
            self.assertEqual(completed_uv_receipt(root,transfer_id),path)

    def test_unstarted_proxy_cannot_supply_a_completed_receipt(self):
        from vipe_benchmark.transfer_proxy import uv_proxy,TransferProxyError
        with tempfile.TemporaryDirectory() as directory:
            proxy=uv_proxy(directory,100)
            with self.assertRaisesRegex(TransferProxyError,'cleanup'):
                _=proxy.receipt_path

    def test_missing_error_field_cannot_claim_successful_transfer(self):
        from vipe_benchmark.transfer_proxy import completed_uv_receipt,TransferProxyError
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            transfer_id='b'*32
            path=root/'uv-transfers'/f'transfer-{transfer_id}.json'
            path.parent.mkdir()
            write_json(path,dict(transfer_id=transfer_id,complete=True,bytes_received=17,reserved_bytes=0))
            with self.assertRaisesRegex(TransferProxyError,'successful complete'):
                completed_uv_receipt(root,transfer_id)

    def test_failed_unfinished_reserved_or_wrong_identity_receipts_are_rejected(self):
        from vipe_benchmark.transfer_proxy import completed_uv_receipt,TransferProxyError
        for change in [dict(complete=False),dict(error='failed'),dict(reserved_bytes=1),
                dict(transfer_id='c'*32),dict(bytes_received=-1),dict(bytes_received=True)]:
            with self.subTest(change=change), tempfile.TemporaryDirectory() as directory:
                root=Path(directory)
                transfer_id='b'*32
                path=root/'uv-transfers'/f'transfer-{transfer_id}.json'
                path.parent.mkdir()
                write_json(path,dict(dict(transfer_id=transfer_id,complete=True,error=None,
                    bytes_received=17,reserved_bytes=0),**change))
                with self.assertRaisesRegex(TransferProxyError,'successful complete'):
                    completed_uv_receipt(root,transfer_id)

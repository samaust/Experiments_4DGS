"""Regression for the observed baseline persistence failure, without optimization."""
from pathlib import Path
import gzip
import json
import sys
import tempfile
import unittest
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from basketball_shared_serialization_v9 import compressed_write
from basketball_shared_accounting_v9 import CanonicalAdapter,reconcile
from basketball_shared_recovery_v8 import fixture

class SerializationTests(unittest.TestCase):
    def test_full_metadata_and_entry_ledger_roundtrip(self):
        a=CanonicalAdapter(fixture(2,-19.,0.),'serialization-unit');a.fun(a.p.x0/a.scale)
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/'record.json.gz';compressed_write(p,a.export());restored=json.load(gzip.open(p,'rt'))
            self.assertTrue(reconcile(restored)['passed']);self.assertEqual(restored,a.export())

    def test_numpy_metadata_payload(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/'record.json.gz';compressed_write(p,dict(frames=np.array([50,51]),scalar=np.float64(.1)))
            self.assertEqual(json.load(gzip.open(p,'rt')),dict(frames=[50,51],scalar=.1))

    def test_no_empty_artifact_on_encoding_failure(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/'record.json.gz'
            with self.assertRaises(TypeError):compressed_write(p,dict(bad=object()))
            self.assertFalse(p.exists());self.assertEqual(list(Path(t).iterdir()),[])

    def test_nonfinite_metadata_rejected_before_publication(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/'record.json.gz'
            with self.assertRaises(ValueError):compressed_write(p,dict(bad=np.array([np.nan])))
            self.assertFalse(p.exists())

    def test_no_overwrite_and_deterministic_bytes(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/'a.gz';q=Path(t)/'b.gz';compressed_write(p,dict(a=[1.]));compressed_write(q,dict(a=[1.]))
            self.assertEqual(p.read_bytes(),q.read_bytes());old=p.read_bytes()
            with self.assertRaises(FileExistsError):compressed_write(p,dict(a=[2.]))
            self.assertEqual(p.read_bytes(),old)

if __name__=='__main__':unittest.main()

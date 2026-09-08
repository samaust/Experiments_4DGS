"""Plan 015 canonical accounting, isolation, failure and deadline contracts."""
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from basketball_shared_accounting_v9 import CanonicalAdapter,Ledger,reconcile
from basketball_shared_recovery_v8 import fixture
from basketball_shared_stopping_v9 import qualified

class AccountingTests(unittest.TestCase):
    def test_full_accounting_regressions(self):
        from basketball_shared_regressions_v9 import accounting_regressions
        self.assertTrue(accounting_regressions()['passed'])

    def test_problem_and_namespace_isolation(self):
        a=CanonicalAdapter(fixture(2,-19.,0.),'baseline');b=CanonicalAdapter(fixture(2,-19.,0.),'candidate')
        c=CanonicalAdapter(fixture(2,-19.,1.),'baseline')
        self.assertEqual(len({a.problem_key,b.problem_key,c.problem_key}),3)

    def test_independent_observer_detects_omitted_entry(self):
        a=CanonicalAdapter(fixture(2,0.,1.));a.fun(a.p.x0/a.scale)
        data=a.export();data['observed_numerical_entries'].append(data['observed_numerical_entries'][0])
        with self.assertRaises(AssertionError):reconcile(data)

    def test_shared_sanitation_budget(self):
        from basketball_shared_initialization_v9 import sanitize
        a=CanonicalAdapter(fixture(2,-19.,0.));sanitize(a)
        before=len(a.ledger.states);self.assertGreater(before,0)
        a.set_transform(a.p.x0,True)
        self.assertGreaterEqual(len(a.ledger.states),before);reconcile(a.export())

    def test_xtol_not_stationarity(self):
        self.assertFalse(qualified(True,[1.00001e-6],[3.],[]))
        self.assertTrue(qualified(True,[1e-6],[3.],[]))
        self.assertFalse(qualified(True,[0.],[1e-8],[]))

    def test_nested_absolute_deadlines(self):
        from basketball_shared_workflow_v9 import deadline,check
        p=json.loads(Path('configs/basketball-rev2/timing-shared-v9.json').read_text());start=p['investigation_started_unix']
        self.assertEqual(deadline(p,'account'),start+2100)
        self.assertEqual(deadline(p,'package'),start+5400)
        with patch('basketball_shared_workflow_v9.time.time',return_value=start+2100):
            with self.assertRaises(TimeoutError):check(p,'account')

    def test_no_cap_increase(self):
        with self.assertRaises(ValueError):Ledger('x',[1.],max_states=201)
        with self.assertRaises(ValueError):Ledger('x',[1.],max_iterations=201)

if __name__=='__main__':unittest.main()

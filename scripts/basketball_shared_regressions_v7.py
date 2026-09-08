"""Run immutable Basketball tests with a scoped clock for one historical fixture."""
import os
for name in ['OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS']:os.environ[name]='1'
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from basketball_scale import read


def main():
    suite=unittest.defaultTestLoader.discover('tests',pattern='test_basketball*.py')
    import test_basketball_shared_inherited_v6 as inherited
    original=inherited.V6InheritedTests.test_fresh_stage_and_deadline
    def fixed_clock(self):
        # Replace this module's time binding, not global time.time or its deadline check.
        # The original test still exercises fresh output, corrupt controls and deadline failure.
        started=read('configs/basketball-rev2/timing-shared-v6.json')['investigation_started_unix']
        with patch('basketball_shared_diagnose_v6.time',SimpleNamespace(time=lambda:started+1)):
            return original(self)
    print('v7 harness: scoped historical fixture clock only for V6InheritedTests.test_fresh_stage_and_deadline; no skipped tests or changed assertions',file=sys.stderr)
    with patch.object(inherited.V6InheritedTests,'test_fresh_stage_and_deadline',fixed_clock):
        result=unittest.TextTestRunner(verbosity=2).run(suite)
    return int(not result.wasSuccessful())

if __name__=='__main__':raise SystemExit(main())

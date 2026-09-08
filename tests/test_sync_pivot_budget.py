import importlib.util
import json
from pathlib import Path
import sys
from unittest.mock import patch

import pytest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
spec=importlib.util.spec_from_file_location('pivot_supervisor',Path(__file__).resolve().parents[1]/'scripts/run-sync-pivot.py')
runner=importlib.util.module_from_spec(spec);spec.loader.exec_module(runner)


def setup(tmp_path,attempts):
    ledger=tmp_path/'docs/research/basketball-sync-pivot/gpu-budget.json'
    ledger.parent.mkdir(parents=True)
    ledger.write_text(json.dumps(dict(limit_seconds=43200,allocation_limits_seconds={'evaluation':3600},attempts=attempts)))
    command=['runner','--allocation','evaluation','--role','offline-reload','--seconds','60',
             '--output',str(tmp_path/'result'),'--','synthetic-command']
    return ledger,command


@pytest.mark.parametrize('attempt',[dict(role='offline-reload',status='completed',charged_seconds=1,allocation='evaluation'),
                                  dict(role='earlier',status='reserved',charged_seconds=60,allocation='evaluation'),
                                  dict(role='earlier',status='completed',charged_seconds=3590,allocation='evaluation')])
def test_refuse_before_launch(tmp_path,attempt):
    ledger,argv=setup(tmp_path,[attempt])
    with patch.object(runner,'__file__',str(tmp_path/'scripts/run-sync-pivot.py')),patch.object(sys,'argv',argv),patch.object(runner,'supervise') as launch:
        with pytest.raises(SystemExit):runner.main()
        launch.assert_not_called()
    assert json.loads(ledger.read_text())['attempts']==[attempt]


def test_reserve_before_launch_then_charge_elapsed(tmp_path):
    ledger,argv=setup(tmp_path,[]);now=[100.]
    def launch(*args,**kwargs):
        attempt=json.loads(ledger.read_text())['attempts'][0]
        assert attempt['status']=='reserved' and attempt['charged_seconds']==60
        now[0]+=5
        return dict(exit_code=0,stop_requested=False,wall_seconds=5)
    with patch.object(runner,'__file__',str(tmp_path/'scripts/run-sync-pivot.py')),patch.object(sys,'argv',argv),patch.object(runner.time,'monotonic',side_effect=lambda:now[0]),patch.object(runner,'supervise',side_effect=launch):
        runner.main()
    a=json.loads(ledger.read_text())['attempts'][0]
    assert a['status']=='completed' and a['charged_seconds']==5


def test_interruption_keeps_reservation(tmp_path):
    ledger,argv=setup(tmp_path,[])
    with patch.object(runner,'__file__',str(tmp_path/'scripts/run-sync-pivot.py')),patch.object(sys,'argv',argv),patch.object(runner,'supervise',side_effect=KeyboardInterrupt):
        with pytest.raises(KeyboardInterrupt):runner.main()
    a=json.loads(ledger.read_text())['attempts'][0]
    assert a['status']=='reserved' and a['charged_seconds']==60

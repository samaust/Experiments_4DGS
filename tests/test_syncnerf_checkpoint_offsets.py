import importlib.util
import json
from pathlib import Path
import sys
from unittest.mock import patch
import torch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import syncnerf_checkpoint_offsets as module


def test_only_common_iteration_is_used(tmp_path):
    for seed,steps in enumerate([[1000,2000],[1000],[1000,3000]]):
        d=tmp_path/f'syncnerf-seed{seed}/worker/model';d.mkdir(parents=True)
        for step in steps:
            state=dict(global_step=step,model={'cam_offset':torch.tensor([0.,.01,0.,0.,0.,0.,0.,0.])},optimizer={},lr_scheduler={})
            torch.save(state,d/f'{step}-model.pth')
    output=tmp_path/'result.json'
    with patch.object(sys,'argv',['offsets','--runs',str(tmp_path),'--output',str(output)]):module.main()
    data=json.loads(output.read_text())
    assert data['iteration']==1000
    assert abs(data['mean_seconds'][1]+.02475)<1e-7
    assert data['range_seconds']==[0.]*8

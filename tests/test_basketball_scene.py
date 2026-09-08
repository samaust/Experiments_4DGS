import importlib.util
import json
from pathlib import Path
import sys

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from basketball_scene import BasketballScene, FreeTimeBasketballScene, render_calibration
from basketball_sync_audit import select_cameras
from sync_timing import common_training_keys

spec = importlib.util.spec_from_file_location('prepare_basketball', Path(__file__).resolve().parents[1]/'scripts/prepare-basketball-sync.py')
prepare = importlib.util.module_from_spec(spec)
spec.loader.exec_module(prepare)


@pytest.fixture
def scene_file(tmp_path):
    timing = prepare.zero_timing('fixture')
    cameras = []
    for c in timing['camera_ids']:
        cameras.append(dict(id=c, split='test' if c in ['0','10','20','30'] else 'train',
            K=[[800.,0.,480.],[0.,800.,270.],[0.,0.,1.]], width=960,height=540,
            world_to_camera_R=np.eye(3).tolist(),world_to_camera_T=[0.,0.,0.],center=[0.,0.,0.],
            frames=[dict(frame_id=f,normalized_time=f/50,path='unused.png',sha256='unused') for f in range(50)]))
    keys, exclusions = common_training_keys([(c,f,f/25) for c in timing['camera_ids'] for f in range(50)],
                                            [timing], ['0','10','20','30'])
    m=dict(schema='basketball-processed/v1',status='prepared',source_fps=25,
           heldout_camera_ids=['0','10','20','30'], temporal_holdout_seconds=[.8,1.],
           cameras=cameras,timing=timing,comparison_timings=[timing],time=timing['normalization'],
           training_keys=keys,training_exclusions=exclusions)
    path=tmp_path/'manifest.json';path.write_text(json.dumps(m));return path


def test_training_and_temporal_exclusions(scene_file):
    for cls in (BasketballScene,FreeTimeBasketballScene):
        scene=cls(scene_file)
        assert len(scene.training_keys()) == 30*45
        assert not scene.training_keys(20)
        assert len(scene.training_keys(25)) == 30
        for key in [('0',0),('1',22)]:
            with pytest.raises(ValueError,match='holdout'):
                scene.training_camera(key,device='cpu',load_image=False)
        camera=scene.training_camera(('1',26),device='cpu',load_image=False)
        assert getattr(camera,'t',getattr(camera,'timestamp',None)) == pytest.approx(.52)


def test_tampered_exclusion_rejected(scene_file):
    m=json.loads(scene_file.read_text());m['training_keys'].append(['1',22])
    scene_file.write_text(json.dumps(m))
    with pytest.raises(ValueError,match='exclusions'):
        BasketballScene(scene_file)


def test_timing_and_source_range_rejected(scene_file):
    m=json.loads(scene_file.read_text());m['cameras'][1]['frames'][0]['normalized_time']=.001
    scene_file.write_text(json.dumps(m))
    with pytest.raises(ValueError,match='timestamp'):
        BasketballScene(scene_file)
    m['cameras'][1]['frames'][0]['frame_id']=200
    scene_file.write_text(json.dumps(m))
    with pytest.raises(ValueError,match='0–49'):
        BasketballScene(scene_file)


def test_radial_pixel_and_metric_conventions():
    import cv2
    entry=dict(K=[[800.,0.,479.5],[0.,800.,269.5],[0.,0.,1.]],
               camera_model='SIMPLE_RADIAL',parameters_colmap=[800.,480.,270.,-.14],
               R=np.eye(3).tolist(),t=[1.,2.,3.],center=[-1.,-2.,-3.])
    renderer,K,d=render_calibration(entry,2.)
    assert renderer['world_to_camera_T']==[2.,4.,6.]
    np.testing.assert_allclose(np.array(renderer['K'])[:2,2],K[:2,2]+.5)
    point=np.array([[[.3,.2,2.]]])
    pixels,_=cv2.projectPoints(point,np.zeros(3),np.zeros(3),K,np.array(d))
    recovered=cv2.undistortPoints(pixels,K,np.array(d),P=K)
    expected=np.array([[[800*.3/2+479.5,800*.2/2+269.5]]])
    np.testing.assert_allclose(recovered,expected,atol=1e-6)
    # OpenCV area resize maps source centers by (x+.5)/2-.5.
    native=np.array([959.5,539.5]);np.testing.assert_allclose((native+.5)/2-.5,K[:2,2])


def test_overlap_selection_ties_and_heldouts():
    visible={0:{1,2,3,4},1:{1,2},2:{1,3},3:{2,4},4:{4,5}}
    selected,_=select_cameras(visible,count=3)
    assert selected==[1,2,3]
    with pytest.raises(ValueError,match='overlap'):
        select_cameras({1:{1},2:{2}},count=2)

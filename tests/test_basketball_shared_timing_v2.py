import copy
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from basketball_shared_association_v2 import (merge_duplicates,mutual_pairs,appearance_distances,partition,reconstruct,build_groups)
from basketball_shared_tracks_v2 import join_branches,follow
from basketball_shared_timing_v2 import bounded,validate_config,watchdog
from basketball_shared_timing_v1 import synthetic_pairs,predecessor
from basketball_scale import read,write
from basketball_audit import sha256

CONFIG=read('configs/basketball-rev2/timing-shared-v2.json')


def track(value,frames=(50,60),identity='t'):
    return dict(descriptor_checkpoints=[dict(frame=f,descriptor=[value],source_track_id=identity) for f in frames])


class SharedTimingV2Tests(unittest.TestCase):
    def test_checkpoint_minimum_and_distinct_trajectory_runner_up(self):
        a=[track(0),track(5)]; b=[track(.01),track(5.01)]
        pairs,evidence=mutual_pairs(a,b)
        self.assertEqual(pairs,[(0,0),(1,1)])
        self.assertEqual(evidence[0]['a_runner_up_track'],1)
        b[0]['descriptor_checkpoints'].append(dict(frame=60,descriptor=[.001],source_track_id='late'))
        self.assertEqual(mutual_pairs(a,b)[0],pairs)
        self.assertAlmostEqual(appearance_distances(a,b)[0][0,0],.001)

    def test_vectorized_distance_and_provenance_equal_reference(self):
        from scipy.spatial.distance import cdist
        rng=np.random.default_rng(0)
        def items(n):
            return [dict(descriptor_checkpoints=[dict(frame=int(f),descriptor=rng.random(8).tolist()) for f in rng.choice(np.arange(50,150),size=9,replace=False)]) for _ in range(n)]
        a,b=items(7),items(6)
        d,provenance=appearance_distances(a,b)
        for i,aa in enumerate(a):
            for j,bb in enumerate(b):
                candidates=[(float(cdist([ca['descriptor']],[cb['descriptor']])[0,0]),ka,kb) for ka,ca in enumerate(aa['descriptor_checkpoints']) for kb,cb in enumerate(bb['descriptor_checkpoints']) if abs(ca['frame']-cb['frame'])<=25]
                expected,ka,kb=min(candidates)
                self.assertEqual(d[i,j],expected)
                self.assertEqual((provenance[i,j]['a_checkpoint'],provenance[i,j]['b_checkpoint']),(ka,kb))

    def test_duplicate_candidate_filter_equal_all_pairs(self):
        pairs,cams=synthetic_pairs('acceleration',0,n=24)
        items=[]
        for i,(a,_) in enumerate(pairs):
            a=copy.deepcopy(a);a.update(source_track_id=str(i),descriptor_checkpoints=track(i)['descriptor_checkpoints']);items.append(a)
        for i in range(4):
            a=copy.deepcopy(items[i]);a['source_track_id']='duplicate'+str(i);a['xy']+=.25;items.append(a)
        fast,families=merge_duplicates(items,cams[0],CONFIG)
        from unittest.mock import Mock
        tree=Mock();tree.query_pairs.return_value={(i,j) for i in range(len(items)) for j in range(i+1,len(items))}
        with patch('basketball_shared_association_v2.cKDTree',return_value=tree):
            slow,reference=merge_duplicates(items,cams[0],CONFIG)
        self.assertEqual(families,reference)
        for a,b in zip(fast,slow): np.testing.assert_array_equal(a['xy'],b['xy'])

    def test_descriptor_time_filter_and_two_sided_ratio(self):
        self.assertEqual(mutual_pairs([track(0),track(.11)],[track(.05),track(3)])[0],[])
        self.assertEqual(mutual_pairs([track(0),track(5)],[track(.01,(100,)),track(5.01,(100,))])[0],[])
        d,_=appearance_distances([track(0,(50,))],[track(0,(75,)),track(0,(76,))])
        self.assertEqual(d[0,0],0); self.assertTrue(np.isinf(d[0,1]))

    def test_batched_checkpoint_descriptors_equal_individual(self):
        import cv2
        cv2.setNumThreads(1)
        image=np.random.default_rng(0).integers(0,256,(240,320),dtype=np.uint8)
        sift=cv2.SIFT_create(nfeatures=50)
        keys,_=sift.detectAndCompute(image,None)
        keys=list(keys[:8])
        for i,key in enumerate(keys): key.class_id=i
        returned,batch=sift.compute(image,keys)
        individual=np.array([sift.compute(image,[key])[1][0] for key in keys])
        np.testing.assert_array_equal(batch,individual)
        self.assertEqual([k.class_id for k in returned],list(range(len(keys))))

    def test_join_branches_and_discontinuity(self):
        f,xy=join_branches((60,[0,0]),[(59,[-1,0]),(58,[-2,0])],[(61,[1,0])])
        self.assertEqual(f,[58,59,60,61]); self.assertEqual(xy.shape,(4,2))
        with self.assertRaises(ValueError): join_branches((60,[0,0]),[(58,[0,0])],[])
        import cv2
        images={f:np.full((1080,1920),f,np.uint8) for f in range(59,62)}
        flow=lambda prev,cur,xy,*args,**kw:(xy.copy(),np.ones((len(xy),1),np.uint8),None)
        with patch.object(cv2,'calcOpticalFlowPyrLK',side_effect=flow),patch('basketball_shared_tracks_v2.appearance_correlation',return_value=0):
            branches,counts=follow(images,60,[[100,100]],-1,CONFIG,lambda:None)
        self.assertEqual(branches,[[]]); self.assertEqual(counts['appearance_discontinuity'],1)

    def test_duplicate_provenance_and_incompatible_transitive_family(self):
        pairs,cams=synthetic_pairs('acceleration',0,n=1)
        a=copy.deepcopy(pairs[0][0]); a.update(source_track_id='a',descriptor_checkpoints=track(0)['descriptor_checkpoints'])
        b=copy.deepcopy(a); b['xy']+=np.array([.75,0]); b['source_track_id']='b'
        c=copy.deepcopy(a); c['xy']+=np.array([1.5,0]); c['source_track_id']='c'
        merged,f=merge_duplicates([a,b],cams[0],CONFIG)
        self.assertEqual(len(merged),1); self.assertEqual(merged[0]['source_track_ids'],['a','b'])
        self.assertEqual(len(merged[0]['descriptor_checkpoints']),4)
        merged,f=merge_duplicates([a,b,c],cams[0],CONFIG)
        self.assertFalse(merged); self.assertEqual(f['incompatible_families'],1)
        self.assertEqual(f['families'][0]['source_track_ids'],['a','b','c'])

    def test_partition_deterministic_objectives(self):
        matrix=np.array([[1]*24+[0]*2,[0]*2+[1]*24])
        a=partition(matrix); b=partition(matrix)
        self.assertEqual(a['status'],'passed'); self.assertEqual(a['assignment'],b['assignment'])
        counts=matrix@a['assignment']; self.assertTrue(np.all(counts==12))
        self.assertEqual(sum(a['assignment']),13); self.assertEqual(a['maximum_imbalance'],0)
        self.assertEqual(a['total_imbalance'],0); self.assertEqual(len(a['trace']),28)

    def test_partition_minimum_and_mathematically_infeasible(self):
        self.assertEqual(partition(np.ones((2,23),int))['status'],'insufficient_edge_support')
        # For25 groups, all25 subsets omitting one group have24 members. Each
        # must have12 per half, forcing every binary decision to be identical,
        # which cannot meet balanced half sizes.
        matrix=np.ones((25,25),int)-np.eye(25,dtype=int)
        self.assertEqual(partition(matrix)['status'],'infeasible')
        self.assertEqual(partition(np.ones((1,24),int),seconds=0)['status'],'solver_timeout')
        with self.assertRaises(ValueError): partition([[.5]])

    def test_tie_break_timeout_never_returns_partial_assignment(self):
        from types import SimpleNamespace
        good=SimpleNamespace(status=0,message='optimal',fun=0,mip_gap=0,x=np.zeros(26))
        bad=SimpleNamespace(status=1,message='time limit',fun=None,mip_gap=None)
        with patch('basketball_shared_association_v2.milp',side_effect=[good,good,bad]):
            result=partition(np.ones((1,24),int))
        self.assertEqual(result['status'],'deterministic_tie_break_timeout'); self.assertIsNone(result['assignment'])

    def test_reconstruction_detects_original_and_family_leakage(self):
        groups=[dict(group_id=i,members=[dict(camera_id=1,track_id=i)]) for i in range(2)]
        tracks={1:[dict(source_track_ids=['same'],duplicate_family_id=i) for i in range(2)]}
        with self.assertRaises(ValueError): reconstruct(groups,tracks,[],[0,1])
        tracks[1][1]['source_track_ids']=['different']; tracks[1][1]['duplicate_family_id']=0
        with self.assertRaises(ValueError): reconstruct(groups,tracks,[],[0,1])

    def test_group_conflicts_and_training_membership(self):
        p=CONFIG; tracks={c:[{},{}] for c in [0,1,2,3]}
        edges=[dict(a=1,b=2),dict(a=2,b=3),dict(a=1,b=3)]
        with patch('basketball_shared_association_v2.mutual_pairs',side_effect=[([(0,0)],[]), ([(0,0)],[]), ([(1,0)],[])]):
            groups,rejected,_,_=build_groups(tracks,edges,p)
        self.assertFalse(groups); self.assertIn('conflicting camera trajectories',{r['reason'] for r in rejected})
        with patch('basketball_shared_association_v2.mutual_pairs',return_value=([(0,0)],[])):
            groups,_,_,_=build_groups({c:[{}] for c in [0,1,2]},[dict(a=0,b=1),dict(a=1,b=2)],p)
        self.assertFalse(groups)

    def test_deadline_reserve_and_immutable_invariants(self):
        p=copy.deepcopy(CONFIG); p['investigation_started_unix']=time.time()-13201
        with self.assertRaises(TimeoutError): bounded(p)
        bounded(p,package=True)
        p['investigation_started_unix']=time.time()-14401
        with self.assertRaises(TimeoutError): bounded(p,package=True)
        p=copy.deepcopy(CONFIG); p['seed_frames'].append(150)
        with self.assertRaises(ValueError): validate_config(p)
        p=copy.deepcopy(CONFIG); p['roles']['fit']=[50,199]
        with self.assertRaises(ValueError): validate_config(p)

    def test_extraction_reuse_hashes_and_roles(self):
        from basketball_shared_timing_v2 import extraction_sources
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);(root/'tracks').mkdir()
            write(root/'frozen.json',dict(config=CONFIG,source_sha256={'scripts/basketball_shared_tracks_v2.py':sha256('scripts/basketball_shared_tracks_v2.py')}))
            cameras=[]
            for c in range(34):
                file=root/'tracks'/f'camera{c}-tracks.json';write(file,dict(role='fit',camera_id=c,tracks=[]))
                cameras.append(dict(camera_id=c,sha256=sha256(file)))
            write(root/'tracks/result.json',dict(status='complete',role='fit',cameras=cameras,source_sha256={}))
            extraction_sources(root,CONFIG)
            (root/'tracks/camera0-tracks.json').write_text('{}')
            with self.assertRaises(ValueError): extraction_sources(root,CONFIG)

    def test_external_watchdog_terminates_and_preserves_blocker(self):
        import subprocess
        from types import SimpleNamespace
        from unittest.mock import Mock
        child=Mock(pid=12345)
        child.wait.side_effect=[subprocess.TimeoutExpired('worker',1),0]
        with tempfile.TemporaryDirectory() as d:
            output=Path(d)/'fresh'
            a=SimpleNamespace(config=Path('configs/basketball-rev2/timing-shared-v2.json'),output=output,stage='associate',predecessor=None)
            with patch('basketball_shared_timing_v2.bounded'),patch('basketball_shared_timing_v2.subprocess.Popen',return_value=child),patch('basketball_shared_timing_v2.os.killpg') as kill:
                self.assertEqual(watchdog(a),1)
            self.assertEqual(kill.call_args.args[0],12345)
            result=read(output/'result.json')
            self.assertEqual(result['terminal_kind'],'budget_exhaustion')
            self.assertIsNone(result['candidate_offsets'])
            self.assertFalse(result['final_validation_consumed'])

    def test_fresh_output_and_hash_tamper(self):
        from types import SimpleNamespace
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            with patch('basketball_shared_timing_v2.bounded'), self.assertRaises(FileExistsError): watchdog(SimpleNamespace(config=Path('configs/basketball-rev2/timing-shared-v2.json'),output=root,stage='prepare'))
            data=root/'data.json'; write(data,dict(x=1))
            write(root/'result.json',dict(config_sha256='hash',stage='prepare',source_sha256={},artifacts_sha256={str(data):sha256(data)}))
            predecessor(root,'hash',{'prepare'}); data.write_text('{"x":2}')
            with self.assertRaises(ValueError): predecessor(root,'hash',{'prepare'})


if __name__=='__main__': unittest.main()

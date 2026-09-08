"""Hand-authored toy regressions only; never load a scientific attempt fixture."""
import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import time
import unittest
from unittest.mock import patch
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import basketball_shared_trajectory_diagnostic_v11 as d
from basketball_shared_trajectory_verify_v11 import Direct


def toy():
    knots=np.r_[[1.]*4,np.arange(1.4,6.96-1e-12,.4),[6.96]*4]
    C=np.tile([.2,.3,4.],(18,1)); x=C.ravel(); selected=[]
    ident=dict(attempt_id='toy',reference={},policy='toy',run_id='basketball-shared-v10-1788843120',dependency_provenance=None,allocation=None,namespace='toy')
    cams={str(i):dict(R=np.eye(3).tolist(),t=[-(i-1),0.,0.],K=np.eye(3).tolist(),parameters_colmap=[1,0,0,0]) for i in (1,2,3)}
    problem=dict(calibration=cams,observations=[dict(group_id=0,observations=[dict(camera_id=i,frames=list(range(50,150)),xy=[[0.,0.]]*100) for i in (1,2,3)])],
                 offsets={'1':0.,'2':-25.,'3':-25.},free=[],window=[50,149],spacing=10,weight=0.,namespace='toy',provenance=ident)
    key=hashlib.sha256(json.dumps(problem,sort_keys=True).encode()).hexdigest()
    state=dict(identity=hashlib.sha256(key.encode()+b'destination'+x.astype('<f8').tobytes()).hexdigest(),scope='destination',canonical_hex=d.fhex(x),physical_hex=d.fhex(x))
    callback=dict(state=state['identity'],x=x.tolist(),q=x.tolist(),y=x.tolist(),multipliers=[[0.]*300,[0.]*54],objective=1.,min_depth=4.,optimality=1.,barrier_parameter=.1,trust_radius=1.)
    selected=[dict(ordinal=i,callback=callback,state=state,x_hex=d.fhex(x),q_hex=d.fhex(x),y_hex=d.fhex(x)) for i in range(4)]
    a=dict(problem=problem,problem_key=key,states=[state],distinct_states=1,transform_hex=d.fhex(np.eye(54).ravel()),origin_hex=d.fhex([0.]*54),scale_hex=d.fhex([1.]*54),entries=[],observed_numerical_entries=[])
    row=dict(accounting=a,knots=knots.tolist(),center=[1.,0.,0.],diameter=2.,solver_trace=[callback],returned_state=state['identity'],x=x.tolist(),canonical_q=x.tolist(),multipliers_transformed=[0.]*300,policy='toy',seed=None)
    return dict(id='toy',row=row,selected=selected,identity=ident,arm='metric',group=0,weight=0.)


class Tests(unittest.TestCase):
    def test_deadline_and_duplicate_entry_denied_before_call(self):
        with tempfile.TemporaryDirectory() as tmp:
            e=d.Entries(Path(tmp)/'j','toy',['a'],[],time.monotonic()+5)
            e.allocate('a','00'); called=[]
            e.call('a','depth','00',lambda:called.append(1))
            with self.assertRaises(ValueError): e.call('a','depth','00',lambda:called.append(2))
            with self.assertRaises(ValueError): e.allocate('b','00')
            with self.assertRaises(ValueError): e.call('a','residual','01',lambda:called.append(9))
            e.end=time.monotonic()-1
            with self.assertRaises(TimeoutError): e.call('a','residual','00',lambda:called.append(3))
            self.assertEqual(called,[1]); e.close()
    def test_interruption_retains_charge_and_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'j'; e=d.Entries(p,'toy',['a'],[],time.monotonic()+5);e.allocate('a','00')
            with self.assertRaises(KeyboardInterrupt): e.call('a','depth','00',lambda:(_ for _ in ()).throw(KeyboardInterrupt()))
            e.close(); events=[json.loads(l) for l in p.read_text().splitlines()]
            self.assertEqual([r['event'] for r in events],['allocated','entry','error'])
            self.assertEqual(events[1]['counts'],{'depth':1})
    def test_skipped_slots_do_not_transfer(self):
        with tempfile.TemporaryDirectory() as tmp:
            e=d.Entries(Path(tmp)/'j','toy',['a'],[],time.monotonic()+5);e.allocate('a','00');e.finish('a',dict(status='skipped'))
            with self.assertRaises(ValueError):e.allocate('a','00')
            with self.assertRaises(ValueError):e.call('a','residual','00',lambda:None)
            e.close()
    def test_constructor_free_and_independent_arithmetic(self):
        import basketball_shared_spline_v2 as spline
        from basketball_shared_solver_v4 import ConstrainedProblem
        case=toy(); x=np.asarray(case['row']['x'])
        with patch.object(ConstrainedProblem,'__init__',side_effect=AssertionError('raw constructor forbidden')),patch.object(ConstrainedProblem,'hess',side_effect=AssertionError('Hessian forbidden')),patch.object(spline.SplineProblem,'__init__',side_effect=AssertionError('constructor forbidden')),patch.object(spline,'initialize_coefficients',side_effect=AssertionError('init forbidden')),patch.object(np.linalg,'svd',side_effect=AssertionError('SVD forbidden')),patch.object(np.linalg,'lstsq',side_effect=AssertionError('fit forbidden')):
            p=d.decode_case(case,lambda:None);direct=Direct(case)
            z,D=d.primary_depth(p,x);zz,DD=direct.depth(x)
            np.testing.assert_allclose(z,zz,atol=1e-12,rtol=1e-12);np.testing.assert_array_equal(D,DD)
            a=d.primary_residual(p,x);b=direct.objective(x)
            np.testing.assert_allclose(a['objective'],b['objective'],atol=1e-10,rtol=1e-9)
            np.testing.assert_allclose(a['G'],b['G'],atol=1e-10,rtol=1e-8)
    def test_depth_rejection_precedes_objective(self):
        case=toy();p=d.decode_case(case,lambda:None);x=np.tile([.2,.3,-4.],18)
        with tempfile.TemporaryDirectory() as tmp:
            e=d.Entries(Path(tmp)/'j','toy',['a'],[],time.monotonic()+5)
            with patch.object(p,'evaluate',side_effect=AssertionError('objective on infeasible')):r=d.finite_slot(p,x,'a',e)
            self.assertEqual(r['status'],'infeasible');self.assertEqual(e.counts,{'depth':1});e.close()
    def test_projective_and_acceleration_limits(self):
        case=toy(); p=d.decode_case(case,lambda:None);base=np.asarray(case['row']['x']);direction=np.tile([0.,0.,1.],18)
        ray=dict(base_hex=d.fhex(base),direction=direction.tolist(),m=1.)
        out=d.primary_limit(p,ray,1.)
        self.assertEqual(out['classification'],'competitive_feasible_finite_limit');self.assertEqual(out['objective_limit'],0.)
        direct=Direct(case); self.assertEqual(direct.limit(base,direction,1.)['objective_limit'],0.)
        p.weight=1.;direction[9]=.1;ray['direction']=direction.tolist()
        out=d.primary_limit(p,ray,1.); self.assertEqual(out['classification'],'divergent_objective')
        ray['direction']=(-np.tile([0.,0.,1.],18)).tolist();p.weight=0.
        out=d.primary_limit(p,ray,1.);self.assertEqual(out['classification'],'infeasible_at_infinity')
        self.assertGreater(out['first_feasibility_boundary'],0.)
    def test_exact_support_not_tiny_slope(self):
        case=toy();p=d.decode_case(case,lambda:None);B=p.spline([2.]);dd=np.zeros((18,3));dd[0,2]=1.
        proof=d.structural_components(p.spline.t,np.array([2.]),B,dd,np.eye(3));self.assertTrue(proof[0,2])
        dd[:]=0.;dd[4,2]=1e-200
        proof=d.structural_components(p.spline.t,np.array([2.]),B,dd,np.eye(3));self.assertFalse(proof[0,2]);self.assertGreater((B@dd)[0,2],0.)
    def test_degenerate_ray_keeps_direction_unavailable(self):
        case=toy(); direct=Direct(case); base,delta,m,direction=direct.ray(case,0,1)
        self.assertEqual(m,0.); self.assertIsNone(direction)
        self.assertEqual(direct.limit(base,direction,1.)['classification'],'degenerate')
    def test_direct_worker_cannot_bypass_supervisor(self):
        with tempfile.TemporaryDirectory() as tmp,patch.object(d,'ROOT',Path(tmp)):
            with self.assertRaises(FileNotFoundError):d.worker(time.monotonic()+1)
    def test_original_growth_floor(self):
        self.assertFalse(1093.05435>max(1e6,100*4.09954));self.assertTrue(1000001>max(1e6,100*4.09954))
    def test_tampered_ownership_receipt_and_returned(self):
        case=toy();row=case['row'];ident=case['identity'];a=row['accounting'];item=dict(id='toy',identity=ident,reference={},row=row)
        events=[dict(event='allocated',identity=ident),dict(event='problem',problem=a['problem'],problem_key=a['problem_key'],scale_hex=a['scale_hex'],transform_hex=a['transform_hex'],origin_hex=a['origin_hex']),dict(event='state',**a['states'][0]),dict(event='solver_invocation'),dict(event='completed',artifact_sha256='a',receipt_sha256='r',id='toy')]
        receipt=dict(id='toy',artifact_sha256='a',verification=dict(passed=True))
        d.validate_item(item,events,receipt,'a','r')
        bad=copy.deepcopy(receipt);bad['artifact_sha256']='tampered'
        with self.assertRaises(AssertionError):d.validate_item(item,events,bad,'a','r')
        for mutation in ('state','multiplier','returned'):
            bad=copy.deepcopy(item)
            if mutation=='state':bad['row']['solver_trace'][0]['state']='bad'
            elif mutation=='multiplier':bad['row']['solver_trace'][0]['multipliers'][0]=[0.]*299
            else:bad['row']['x'][0]+=1
            with self.assertRaises((AssertionError,KeyError)):d.validate_item(bad,events,receipt,'a','r')
    def test_runtime_optimizer_guards(self):
        import basketball_shared_spline_v2 as spline
        import scipy.optimize as opt
        with patch.object(spline.SplineProblem,'__init__'),patch.object(spline,'initialize_coefficients'),patch.object(spline,'least_squares'),patch.object(spline,'minimize_scalar'),patch.object(opt,'minimize'),patch.object(opt,'least_squares'),patch.object(opt,'minimize_scalar'),patch.object(np.linalg,'lstsq'),patch.object(np.linalg,'svd'):
            d.forbid_fitting()
            for call in (lambda:opt.minimize(None,None),lambda:spline.SplineProblem(None,None,None,None,None,None,None),lambda:spline.initialize_coefficients(),lambda:np.linalg.svd(np.eye(2))):
                with self.assertRaises(RuntimeError):call()


if __name__=='__main__':unittest.main()

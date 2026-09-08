"""Exactly twelve fixed Plan 019 toy cases. No archived fixture access."""
import hashlib
import json
import os
from pathlib import Path
import struct
import sys
import tempfile
import time
import unittest
from fractions import Fraction as F
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import basketball_acceleration_reference_v12 as A
import basketball_acceleration_control_v12 as B

U=list(map(F,[0,0,0,0,1,1,1,1]));Q=[F(0),F(1,2),F(1)]

class FixedCases(unittest.TestCase):
    def calculate(self,controls,knots=U,samples=Q):
        C=[[F(c),F(0),F(0)] for c in controls]
        a=A.bundle_a(A.setup_a(knots,samples),C,F(1));b=B.bundle_b(B.setup_b(knots,samples),C,F(1))
        self.assertEqual(a,b)
        for j in (1,2,4,5):self.assertEqual(a['gradient'][j],0)
        return a
    def test_01_constant(self):
        r=self.calculate([2,2,2,2]);self.assertEqual(r['cost'],0);self.assertEqual(r['gradient'],[0]*6);self.assertEqual(r['accelerations'],[[0]*3]*3)
    def test_02_linear(self):
        r=self.calculate([0,1,2,3]);self.assertEqual(r['cost'],0);self.assertEqual(r['gradient'],[0]*6);self.assertEqual(r['accelerations'],[[0]*3]*3)
    def test_03_square(self):
        r=self.calculate([0,0,F(1,3),1]);self.assertEqual(r['cost'],4);self.assertEqual([r['gradient'][0],r['gradient'][3]],[12,-12]);self.assertEqual([v[0] for v in r['accelerations']],[2,2,2])
    def test_04_cube(self):
        r=self.calculate([0,0,0,1]);self.assertEqual(r['cost'],15);self.assertEqual([r['gradient'][0],r['gradient'][3]],[6,18]);self.assertEqual([v[0] for v in r['accelerations']],[0,3,6])
    def test_05_endpoints(self):
        self.assertEqual(A.setup_a(U,[F(0),F(1)]),[[6,-12,6,0],[0,6,-12,6]])
        for setup in (A.setup_a,B.setup_b):
            with self.assertRaises(ValueError):setup(U,[F(-1)])
            with self.assertRaises(ValueError):setup(U,[F(2)])
    def test_06_nonuniform(self):
        knots=list(map(F,[0,0,0,0]))+[F(1,2)]+list(map(F,[2,2,2,2]))
        r=self.calculate([0,0,F(1,3),2,4],knots,[F(0),F(1,2),F(2)]);self.assertEqual(r['cost'],4);self.assertEqual([v[0] for v in r['accelerations']],[2,2,2])
    def test_07_cancellation(self):
        r=self.calculate([0,0,F(-1,6),F(1,2)]);self.assertEqual(r['cost'],10);self.assertEqual([r['gradient'][0],r['gradient'][3]],[0,24]);self.assertEqual([r['absolute_sums'][0],r['absolute_sums'][3]],[8,32]);self.assertEqual([v[0] for v in r['accelerations']],[-1,2,5])
    def test_08_support(self):
        self.assertTrue(A.support([(1,50)],{'1':0},[F(1),F(3,2)])['strictly_separated'])
        for ends in ([F(2)],[F(3)]):
            with self.assertRaises(ValueError):A.support([(1,50)],{'1':0},ends)
    def test_09_tampering(self):
        raw=struct.pack('<d',.1);digest=hashlib.sha256(raw).hexdigest()
        self.assertEqual(A.state_bytes(raw.hex(),digest,8),raw)
        with self.assertRaises(ValueError):A.state_bytes(struct.pack('<d',.2).hex(),digest,8)
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'source';p.write_text('old');mapping={str(p):A.sha(p)};A.hashes(mapping);p.write_text('new')
            with self.assertRaises(ValueError):A.hashes(mapping)
    def test_10_ledger(self):
        ledger=A.Ledger({'A/toy':'bytes','A/other':'other'},time.monotonic()+10,cap=1)
        with self.assertRaises(RuntimeError):ledger.enter('A','toy','bytes',lambda:(_ for _ in ()).throw(RuntimeError('consumed failure')))
        self.assertEqual(ledger.used,['A/toy'])
        for method,slot,h in [('A','toy','bytes'),('B','toy','bytes'),('A','missing','bytes'),('A','other','other')]:
            with self.assertRaises(ValueError):ledger.enter(method,slot,h,lambda:self.fail('forbidden callback'))
        expired=A.Ledger({'A/toy':'bytes'},time.monotonic()-1)
        with self.assertRaises(TimeoutError):expired.enter('A','toy','bytes',lambda:self.fail('expired callback'))
        self.assertEqual(expired.used,[])
    def test_11_supervisor(self):
        # Two specified cleanup modes on a nonscientific stdlib child.
        with tempfile.TemporaryDirectory() as d:
            for mode in ('timeout','interrupted'):
                p=Path(d)/mode;p.mkdir()
                code='import pathlib,time; p=pathlib.Path('+repr(str(p))+'); (p/"entry").write_text("consumed"); (p/"partial").write_text("retained"); time.sleep(10)'
                result=A.supervise([sys.executable,'-c',code],time.monotonic()+2.3,p/'log',p/'identity',interrupt_after=.2 if mode=='interrupted' else None)
                self.assertTrue(result['worker_stopped']);self.assertTrue(result['within_deadline']);self.assertEqual(result['reason'],mode)
                self.assertEqual((p/'entry').read_text(),'consumed');self.assertEqual((p/'partial').read_text(),'retained')
                with self.assertRaises(ProcessLookupError):os.killpg(result['child_pid'],0)
    def test_12_allocation_and_package(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'consumed';started={'token':'toy','supervisor_pid':123}
            with self.assertRaises(ValueError):A.worker_guard(started,None,123,p)
            self.assertFalse(p.exists());A.worker_guard(started,'toy',123,p)
            with self.assertRaises(FileExistsError):A.worker_guard(started,'toy',123,p)
            with self.assertRaises(FileExistsError):A.publish(p,{'replacement':True})
        good=A.serialized(self.calculate([0,0,F(1,3),1]));state={'slot':A.SLOTS[0][0],'archived':{m:{'G':[0.0]*54,'acceleration_cost':4.0} for m in ('primary','independent')}}
        result=A.compare_pair(good,good,state);self.assertTrue(result['reference_agreement']);self.assertEqual(result['archived']['primary']['gradient_status'],'outside_tolerance')
        bad={**good,'cost':['5','1']};result=A.compare_pair(good,bad,state);self.assertFalse(result['reference_agreement']);self.assertEqual(result['archived']['primary']['gradient_status'],'unverified')
        result=A.compare_pair(good,None,state);self.assertEqual(result['archived']['independent']['acceleration_cost']['status'],'unverified')

if __name__=='__main__':unittest.main(verbosity=2)

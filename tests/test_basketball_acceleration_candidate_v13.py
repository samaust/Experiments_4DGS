"""Plan020 fixed twelve analytic/dummy cases, durable at most two invocations."""
import decimal as dec
from decimal import Decimal as D
import hashlib
import io
import json
import os
from pathlib import Path
import struct
import sys
import tempfile
import time
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import basketball_acceleration_candidate_v13 as H
import basketball_acceleration_decimal_v13 as C
U=[0,0,0,0,1,1,1,1];Q=[0,.5,1]

class FixedCases(unittest.TestCase):
    def calc(self,x,u=U,q=Q,all_axes=False):
        h=H.fhex([v for a in x for v in ([a]*3 if all_axes else [a,0,0])])
        s=C.setup(H.fhex(u),H.fhex(q));return s,C.bundle(s,h)
    def values(self,r):return [D(r['cost']['decimal'])]+[D(g['decimal']) for g in r['gradient']]
    def expect(self,r,cost,g0=0,g1=0):
        expected=[cost,g0,0,0,g1,0,0]
        with dec.localcontext(C.context()):
            for a,b in zip(self.values(r),expected):self.assertLessEqual(abs(a-D(b)),D('1e-65'))
    def test_01_constant(self):self.expect(self.calc([7]*4,all_axes=True)[1],0)
    def test_02_linear(self):self.expect(self.calc([0,1,2,3])[1],0)
    def test_03_quadratic(self):self.expect(self.calc([0,0,1,3])[1],36,36,-36)
    def test_04_cubic(self):self.expect(self.calc([0,0,0,1])[1],15,6,18)
    def test_05_nonuniform(self):
        s,r=self.calc([0,1,3,5,6],[0,0,0,0,1,2,2,2,2],[0,.5,1,1.5,2]);self.expect(r,0)
        self.assertEqual([x[0] for x in s['spans']],[1,1,2,2,2]);self.assertEqual(s['spans'][-1][2],1)
    def test_06_repeated(self):
        u=[0,0,0,0,1,1,2,2,2,2]
        s,r=self.calc([0]*6,u,[0,.5,1,1.5,2]);self.expect(r,0)
        self.assertEqual([x[0] for x in s['spans']],[1,1,3,3,3])
        self.assertEqual([x[2] for x in s['spans']],list(map(D,['0','.5','0','.5','1'])))
        for knots,q in [(u,[-1]),(u,[3]),([0]*8,[0])]:
            with self.assertRaises(ValueError):C.setup(H.fhex(knots),H.fhex(q))
    def test_07_translation(self):self.expect(self.calc([2**40+i for i in range(4)])[1],0)
    def test_08_decode(self):
        raw=struct.pack('<2d',.1,-0.);v=C.decode(raw.hex(),2,hashlib.sha256(raw).hexdigest())
        self.assertEqual(v[0],D('0.1000000000000000055511151231257827021181583404541015625'))
        self.assertEqual(v[1].as_tuple(),D('-0').as_tuple());self.assertEqual(H.fhex(list(map(float,v))),raw.hex())
        for h,n,d in [(H.fhex([float('inf')]),1,None),(raw.hex(),1,None),(raw.hex(),2,'bad')]:
            with self.assertRaises(ValueError):C.decode(h,n,d)
    def test_09_context(self):
        before=dec.getcontext().copy()
        with dec.localcontext() as ambient:
            ambient.prec=3;ambient.rounding=dec.ROUND_UP;ambient.traps[dec.Inexact]=True
            settings=C.metadata(ambient)
            _,r=self.calc([0,0,0,1]);self.expect(r,15,6,18)
            self.assertEqual([r['cost']['hex']]+[g['hex'] for g in r['gradient']],[H.fhex([v]) for v in [15,6,0,0,18,0,0]])
            self.assertEqual(C.metadata(ambient),settings)
        self.assertEqual(C.metadata(dec.getcontext()),C.metadata(before))
        c=C.context();self.assertEqual((c.prec,c.rounding,c.Emin,c.Emax,c.capitals,c.clamp),(80,dec.ROUND_HALF_EVEN,-999999,999999,1,0))
        self.assertEqual({k for k,v in c.traps.items() if v},{dec.InvalidOperation,dec.DivisionByZero,dec.Overflow,dec.Underflow,dec.FloatOperation})
    def test_10_export(self):
        for d,v in [(D('.1'),.1),(D('-0'),-0.)]:
            r=C.export(d);self.assertEqual(r['hex'],H.fhex([v]));C.validate_export(r)
        for v in [D('1e10000'),D('NaN'),D('Infinity'),'bad']:
            with self.assertRaises(ValueError):C.export(v)
        for r in [dict(C.export(D(1)),hex='00'),dict(C.export(D(1)),value=float('inf'))]:
            with self.assertRaises(ValueError):C.validate_export(r)
    def test_11_ownership(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);schedule={'candidate/'+str(i):str(i) for i in range(7)}
            ledger=H.Ledger(schedule,time.monotonic()+10,p/'ledger',cap=6)
            with self.assertRaises(RuntimeError):ledger.enter('candidate','0','0',lambda:(_ for _ in ()).throw(RuntimeError('charged failure')))
            self.assertEqual(ledger.used,['candidate/0'])
            for slot,h in [('0','0'),('1','wrong')]:
                with self.assertRaises(ValueError):ledger.enter('candidate',slot,h,lambda:self.fail('entered'))
            for i in range(1,6):ledger.enter('candidate',str(i),str(i),lambda:None)
            with self.assertRaises(ValueError):ledger.enter('candidate','6','6',lambda:self.fail('seventh'))
            source=p/'source';source.write_text('old');mapping={str(source):H.sha(source)};source.write_text('new')
            with self.assertRaises(ValueError):H.hashes(mapping)
            alloc=p/'allocation';started={'token':'toy','supervisor_pid':123}
            with self.assertRaises(ValueError):H.worker_guard(started,None,123,alloc)
            self.assertFalse(alloc.exists());H.worker_guard(started,'toy',123,alloc)
            with self.assertRaises(FileExistsError):H.worker_guard(started,'toy',123,alloc)
            with self.assertRaises(FileExistsError):H.publish(alloc,{})
            self.assertEqual(len((p/'ledger').read_text().splitlines()),6)
    def test_12_deadlines_cleanup(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);end=time.monotonic()-1
            with self.assertRaises(TimeoutError):H.setup_enter(end,root/'setup',lambda:self.fail('expired setup'))
            self.assertFalse((root/'setup').exists())
            ledger=H.Ledger({'candidate/toy':'bytes'},end)
            with self.assertRaises(TimeoutError):ledger.enter('candidate','toy','bytes',lambda:self.fail('expired entry'))
            self.assertEqual(ledger.used,[])
            for mode in ('timeout','interrupted'):
                p=root/mode;p.mkdir()
                code='import pathlib,time; p=pathlib.Path('+repr(str(p))+'); (p/"entry").write_text("consumed"); (p/"partial").write_text("retained"); time.sleep(10)'
                r=H.supervise([sys.executable,'-c',code],time.monotonic()+2.4,p/'log',p/'identity',interrupt_after=.2 if mode=='interrupted' else None)
                self.assertTrue(r['worker_stopped']);self.assertTrue(r['within_deadline']);self.assertEqual(r['reason'],mode)
                self.assertEqual((p/'entry').read_text(),'consumed');self.assertEqual((p/'partial').read_text(),'retained')
                with self.assertRaises(ProcessLookupError):os.killpg(r['child_pid'],0)

if __name__=='__main__':
    H.deadline(H.read(H.AUTH),'implementation_ready')
    root=H.ROOT;freeze=root/'toy-freeze.json'
    if not freeze.exists():H.publish(freeze,dict(test_sha256=H.sha(H.TEST),cases=12,monotonic=time.monotonic()))
    assert H.read(freeze)['test_sha256']==H.sha(H.TEST)
    slot=next((i for i in (1,2) if not (root/('toy-suite-%02d-entry.json'%i)).exists()),None)
    if slot is None:raise RuntimeError('both toy suite invocations consumed')
    stem='toy-suite-%02d'%slot;begin=time.monotonic()
    sources={str(p):H.sha(p) for p in (H.SCRIPT,H.CONTROL,H.TEST)}
    H.publish(root/(stem+'-entry.json'),dict(entry_monotonic=begin,source_sha256=sources,command=[sys.executable,*sys.argv],cases=12))
    with (root/(stem+'.log')).open('x') as log:
        result=unittest.TextTestRunner(stream=log,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(FixedCases))
    H.publish(root/(stem+'-result.json'),dict(passed=result.wasSuccessful(),cases=result.testsRun,source_sha256=sources,entry_monotonic=begin,return_monotonic=time.monotonic(),failures=len(result.failures),errors=len(result.errors)))
    print((root/(stem+'.log')).read_text());sys.exit(0 if result.wasSuccessful() else 1)

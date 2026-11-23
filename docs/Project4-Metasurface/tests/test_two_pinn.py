"""Numerical and prospective-integrity checks for the supporting PINN study."""
import hashlib
import json
from pathlib import Path
import sys
import unittest
import numpy as np
import torch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'code'))
import two_pinn_study as study

class TwoPinnTests(unittest.TestCase):
    def test_capacity(self):
        self.assertEqual(sum(p.numel() for p in study.Model('monolithic').parameters()),4676)
        self.assertEqual(sum(p.numel() for p in study.Model('two_specialists').parameters()),4672)

    def test_analytic_reference(self):
        for d,a in [(.2084,.1516),(.25,.11),(.035,.29),(.35,.065)]:
            for s in (0,1):
                expected=study.response(a+d,a/(a+d),s)[0]
                self.assertLess(abs(study.exact([d],[a])[0,s]-expected),1e-12)

    def test_spatial_jets(self):
        torch.manual_seed(5)
        for mode in ('monolithic','two_specialists'):
            model=study.Model(mode)
            x=torch.tensor([.2,.5,.8]); d=torch.tensor([.1,.208,.3]); s=torch.tensor([0.,1.,1.])
            _, dx=model.evaluate(x,d,s,True)
            fd=(model.evaluate(x+1e-6,d,s)-model.evaluate(x-1e-6,d,s))/(2e-6)
            self.assertLess(float((dx-fd).abs().max().detach()),1e-8)

    def test_design_autodiff(self):
        model=study.Model('two_specialists')
        d=torch.tensor([.1,.208,.3],requires_grad=True)
        r=study.predict(model,d,.36-d)
        grad=torch.autograd.grad(r.real.sum(),d)[0]
        with torch.no_grad():
            fd=(study.predict(model,d+1e-6,.36-d-1e-6).real.sum(1)-study.predict(model,d-1e-6,.36-d+1e-6).real.sum(1))/(2e-6)
        self.assertLess(float((grad-fd).abs().max()),1e-7)

    def test_thresholds(self):
        r=np.array([[1,np.exp(1j*np.deg2rad(166))],[1,-.799],[1,np.exp(1j*np.deg2rad(164))]])
        self.assertEqual(study.feasible(r).tolist(),[True,False,False])

    def test_frozen_separation(self):
        path=ROOT/'assets/two-pinn-protocol.json'
        plan=json.loads(path.read_text())
        receipt=json.loads((ROOT/'assets/two-pinn-freeze-receipt.json').read_text())
        self.assertEqual(study.digest(path),receipt['protocol_sha256'])
        self.assertEqual(study.digest(Path(study.__file__)),plan['source_sha256'])
        ds=np.sort([r['d'] for r in plan['designs']])
        self.assertGreaterEqual(float(min(np.diff(ds))),plan['minimum_d_separation'])
        for split,n in [('train',256),('validation',128),('final',320)]:
            rows=[r for r in plan['designs'] if r['split']==split]
            self.assertEqual(len(rows),n)
            self.assertEqual(sum(r['band'] for r in rows),n//2)
        historical=[]
        for p in (ROOT.parent/'Project3-Metasurface/outputs').rglob('frozen-protocol.json'):
            historical.extend(r['d'] for r in json.loads(p.read_text()).get('designs',[]) if 'd' in r)
        self.assertGreaterEqual(float(min(abs(d-h) for d in ds for h in historical)),1e-8)

    def test_saved_results_independent_numpy(self):
        path=ROOT/'assets/two-pinn-results.json'
        if not path.exists(): self.skipTest('Full run has not completed')
        result=json.loads(path.read_text())
        seal=json.loads((ROOT/'assets/two-pinn-checkpoint-seal.json').read_text())
        payload=json.dumps([r['weights'] for r in result['runs']],sort_keys=True).encode()
        self.assertEqual(hashlib.sha256(payload).hexdigest(),seal['weights_sha256'])
        plan=json.loads((ROOT/'assets/two-pinn-protocol.json').read_text())
        self.assertEqual(result['protocol_sha256'],study.digest(ROOT/'assets/two-pinn-protocol.json'))
        self.assertEqual(len(result['runs']),6)
        ds=np.array([r['d'] for r in plan['designs'] if r['split']=='final'])
        aa=np.array([r['a'] for r in plan['designs'] if r['split']=='final'])
        for run in result['runs']:
            model=study.Model(run['mode'])
            model.load_state_dict({k:torch.tensor(v) for k,v in run['weights'].items()})
            d=np.repeat(ds,2); a=np.repeat(aa,2); s=np.tile([0.,1.],len(ds)); vals=np.empty((len(d),4))
            for k,net in enumerate(model.nets):
                selected=np.ones(len(d),dtype=bool) if len(model.nets)==1 else (study.inside(d) if k else ~study.inside(d))
                lo,hi=net.bounds
                features=np.stack((-np.ones(sum(selected)),2*(d[selected]-lo)/(hi-lo)-1,2*s[selected]-1),axis=1)
                def layer(x,name):
                    return x@np.array(run['weights'][f'nets.{k}.{name}.weight']).T+np.array(run['weights'][f'nets.{k}.{name}.bias'])
                vals[selected]=layer(np.tanh(layer(np.tanh(layer(features,'a')),'b')),'c')
            pred=((1-vals[:,2]-1j*vals[:,3])*np.exp(-2*study.CFG.gamma*a)).reshape(-1,2)
            with torch.no_grad(): expected=study.predict(model,ds,aa).numpy()
            self.assertLess(float(np.max(abs(pred-expected))),1e-12)
            errors=abs(pred-study.exact(ds,aa)).max(axis=1)
            self.assertAlmostEqual(float(np.quantile(errors,.95)),run['final']['reflection_p95'],places=12)
            self.assertEqual(run['updates'],4000)
            self.assertEqual(run['interior_point_state_evaluations'],1024000)

if __name__=='__main__': unittest.main()

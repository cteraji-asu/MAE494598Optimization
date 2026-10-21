import random
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"code"))
try:
    import torch
except ImportError:
    torch=None


@unittest.skipIf(torch is None,"Optional controlled-study dependency PyTorch is absent")
class ControlledStudyTests(unittest.TestCase):
    def test_raw_and_normalized_residual_scaling(self):
        from controlled_study import losses
        from helmholtz import Network
        p=torch.tensor(Network(24,0).p)
        points=torch.tensor([.1,.37,.83])
        _,normal=losses(p,10,points)
        _,raw=losses(p,10,points,raw_scaling=True)
        self.assertAlmostEqual(float(raw["pde"]),10000*float(normal["pde"]),delta=1e-9)
        self.assertAlmostEqual(float(raw["outgoing"]),100*float(normal["outgoing"]),delta=1e-10)
        self.assertAlmostEqual(float(raw["dirichlet"]),float(normal["dirichlet"]),delta=1e-12)

    def test_vectorized_loss_and_gradients_match_independent_python(self):
        from controlled_study import losses
        from helmholtz import Network,loss_gradient
        for mode in ("pinn","supervised"):
            net=Network(24,2)
            points=[0.1,0.37,0.83]
            total,_,gradient=loss_gradient(net,10,points,mode)
            p=torch.tensor(net.p,requires_grad=True)
            objective,_=losses(p,10,torch.tensor(points),mode)
            objective.backward()
            self.assertAlmostEqual(float(objective.detach()),total,delta=1e-12)
            self.assertLess(max(abs(a-b) for a,b in zip(p.grad.tolist(),gradient)),1e-12)

    def test_spatial_jets_match_autograd(self):
        from controlled_study import jets
        from helmholtz import Network
        p=torch.tensor(Network(24,1).p,requires_grad=True)
        x=torch.tensor([0.1,0.37,0.83],requires_grad=True)
        u,ux,uxx=jets(p,x)
        for c in (0,1):
            dx=torch.autograd.grad(u[:,c].sum(),x,create_graph=True,retain_graph=True)[0]
            dxx=torch.autograd.grad(dx.sum(),x,retain_graph=True)[0]
            self.assertLess(float((dx-ux[:,c]).abs().max().detach()),1e-12)
            self.assertLess(float((dxx-uxx[:,c]).abs().max().detach()),1e-12)

    def test_paired_adam_reproduces_original_updates(self):
        from controlled_study import train as vectorized
        from helmholtz import train as original
        p,_,_,_,evaluations=vectorized(1,0,10,8)
        net,_,_=original(1,0,"pinn",10,24,8)
        self.assertEqual(evaluations,10)
        self.assertLess(max(abs(a-b) for a,b in zip(p.tolist(),net.p)),1e-11)


if __name__=="__main__":
    unittest.main()

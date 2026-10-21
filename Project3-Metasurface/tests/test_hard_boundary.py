from pathlib import Path
import sys,unittest
from unittest.mock import patch
import torch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'code'))
from hard_boundary_control import HardFieldNet,losses,impedance,complex_channels
from switched_surrogate import losses as original_losses

class HardBoundaryTests(unittest.TestCase):
    def setUp(self):
        torch.manual_seed(17);self.model=HardFieldNet(8)
        self.d=torch.tensor([.1,.208395,.25,.3]);self.state=torch.tensor([0.,1.,0.,1.]);self.x=torch.tensor([.13,.37,.61,.89])
    def test_exact_conditions_and_all_parameter_gradients_remain_connected(self):
        zero=torch.zeros_like(self.d);v0,i0=complex_channels(self.model.values(zero,self.d,self.state));v1,_=complex_channels(self.model.values(zero+1,self.d,self.state))
        self.assertLess(float(abs(v1).max()),1e-13);self.assertLess(float(abs(v0+(1+impedance(self.state))*i0-2).max()),1e-13)
        loss,_=losses(self.model,self.x,self.d,self.state,True);loss.backward()
        self.assertTrue(all(p.grad is not None and torch.isfinite(p.grad).all() for p in self.model.parameters()))
    def test_spatial_chain_rule_against_autograd(self):
        x=self.x.clone().requires_grad_();value,dx=self.model.jets(x,self.d,self.state)
        ordinary=self.model.values(x,self.d,self.state)
        torch.testing.assert_close(value,ordinary,rtol=1e-13,atol=1e-13)
        for channel in range(4):
            derivative=torch.autograd.grad(ordinary[:,channel].sum(),x,retain_graph=True)[0]
            torch.testing.assert_close(dx[:,channel],derivative,rtol=1e-12,atol=1e-12)
    def test_hard_objective_matches_explicit_full_physics_loss_without_label_access(self):
        expected=original_losses(self.model,self.x,self.d,self.state,'pinn')[0]
        with patch('switched_surrogate.reference_right',side_effect=AssertionError('label access')):
            actual,_=losses(self.model,self.x,self.d,self.state,True)
        torch.testing.assert_close(actual,expected,rtol=1e-13,atol=1e-13)
    def test_parameter_gradient_and_fast_reflection_path(self):
        loss,_=losses(self.model,self.x,self.d,self.state,True);loss.backward()
        parameter=self.model.first.weight;index=(0,0);analytical=float(parameter.grad[index]);original=float(parameter.data[index]);h=1e-6
        parameter.data[index]=original+h;plus=float(losses(self.model,self.x,self.d,self.state,True)[0].detach())
        parameter.data[index]=original-h;minus=float(losses(self.model,self.x,self.d,self.state,True)[0].detach());parameter.data[index]=original
        self.assertAlmostEqual(analytical,(plus-minus)/(2*h),places=6)
        zero=torch.zeros_like(self.d);full=self.model.values(zero,self.d,self.state);fast=self.model.port_values(zero,self.d,self.state)
        torch.testing.assert_close(full[:,2:],fast[:,2:],rtol=0,atol=0)

if __name__=='__main__':unittest.main()

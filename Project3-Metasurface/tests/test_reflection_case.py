import cmath
import math
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"code"))
try:
    import torch
except ImportError:
    torch=None


@unittest.skipIf(torch is None,"Optional reflection-study dependency PyTorch is absent")
class ReflectionTests(unittest.TestCase):
    def test_exact_incoming_and_terminal_conditions(self):
        from reflection_case import exact_field
        k,h=10,1e-5
        for state in ("dirichlet","neumann"):
            f=lambda x:exact_field(x,k,state)
            dx=(f(h)-f(-h))/(2*h)
            self.assertLess(abs(dx+1j*k*f(0)-2j*k),1e-6)
            if state=="dirichlet":
                self.assertLess(abs(f(1)),1e-12)
            else:
                self.assertLess(abs((f(1+h)-f(1-h))/(2*h)),1e-6)
        r1=exact_field(0,k,"dirichlet")-1
        r2=exact_field(0,k,"neumann")-1
        self.assertLess(abs(r1/r2+1),1e-12)

    def test_reference_refinement(self):
        from reflection_case import exact_field,finite_difference
        from helmholtz import relative_l2
        for state in ("dirichlet","neumann"):
            errors=[]
            for n in (128,256,512):
                x,u=finite_difference(10,n,state)
                errors.append(relative_l2(u,[exact_field(a,10,state) for a in x]))
            self.assertGreater(errors[0]/errors[1],3.8)
            self.assertGreater(errors[1]/errors[2],3.8)

    def test_reflection_phase_metric_wraps(self):
        from reflection_case import phase_error
        self.assertAlmostEqual(phase_error(cmath.exp(1j*math.radians(-179)),cmath.exp(1j*math.radians(179))),2)
        self.assertIsNone(phase_error(0,1))

    def test_reflection_loss_gradients(self):
        from reflection_case import losses
        from helmholtz import Network
        x=torch.tensor([.1,.37,.83],dtype=torch.float64)
        for state in ("dirichlet","neumann"):
            p=torch.tensor(Network(24,0).p,dtype=torch.float64,requires_grad=True)
            self.assertTrue(torch.autograd.gradcheck(lambda q:losses(q,10,x,state=state)[0],(p,),atol=1e-5,rtol=1e-4))


if __name__=="__main__":
    unittest.main()

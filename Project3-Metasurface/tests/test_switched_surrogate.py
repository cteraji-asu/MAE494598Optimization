import math
from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"code"))
import torch
from switched_line import Config,field,response
from switched_surrogate import FieldNet,classification,complex_channels,freeze,losses,reference_right


class SurrogateTests(unittest.TestCase):
    def test_value_only_inference_matches_jets(self):
        torch.manual_seed(19)
        model=FieldNet(8)
        x=torch.tensor([0.,.3,1.])
        d=torch.tensor([.04,.208,.30])
        state=torch.tensor([0.,1.,0.])
        self.assertTrue(torch.equal(model.values(x,d,state),model.jets(x,d,state)[0]))

    def test_analytic_spatial_jets_match_autograd(self):
        torch.manual_seed(7)
        model=FieldNet(8)
        x=torch.tensor([.13,.47,.91],requires_grad=True)
        d=torch.tensor([.04,.208,.30])
        s=torch.tensor([0.,1.,1.])
        value,dx=model.jets(x,d,s)
        for j in range(4):
            automatic=torch.autograd.grad(value[:,j].sum(),x,retain_graph=True)[0]
            self.assertLess(float((automatic-dx[:,j]).abs().max().detach()),1e-12)

    def test_reference_and_factorization_match_full_circuit(self):
        config=Config()
        for d in (.04,.2084,.25,.32):
            x=torch.tensor([0.,.31,1.])
            for state in (0,1):
                v,i=complex_channels(reference_right(x,torch.full_like(x,d),torch.full_like(x,float(state))))
                for a in (.02,.08):
                    scale=complex(torch.exp(torch.tensor(-config.gamma*a)))
                    for j,local in enumerate(x.tolist()):
                        ve,ie=field(local,1,a+d,a/(a+d),state)
                        self.assertLess(abs(complex(v[j])*scale-ve),1e-12)
                        self.assertLess(abs(complex(i[j])*scale-ie),1e-12)
                    local_r=1-complex(i[0])
                    self.assertLess(abs(scale*scale*local_r-response(a+d,a/(a+d),state)[0]),1e-12)

    def test_loss_parameter_gradients(self):
        torch.manual_seed(8)
        model=FieldNet(6)
        x=torch.tensor([.12,.83])
        d=torch.tensor([.12,.24]);s=torch.tensor([0.,1.])
        parameter=model.first.weight
        for mode in ("pinn","supervised"):
            model.zero_grad()
            loss=losses(model,x,d,s,mode)[0]
            loss.backward()
            for index in ((0,0),(2,1),(4,2)):
                analytic=float(parameter.grad[index])
                original=float(parameter[index].detach())
                with torch.no_grad():parameter[index]=original+1e-6
                plus=float(losses(model,x,d,s,mode)[0].detach())
                with torch.no_grad():parameter[index]=original-1e-6
                minus=float(losses(model,x,d,s,mode)[0].detach())
                with torch.no_grad():parameter[index]=original
                self.assertAlmostEqual(analytic,(plus-minus)/2e-6,delta=2e-7)

    def test_frozen_split_has_no_duplicate_or_block_training(self):
        task_root=Path(__file__).resolve().parents[3]
        with tempfile.TemporaryDirectory(dir=task_root) as directory:
            self.assertTrue(Path(directory).resolve().is_relative_to(task_root.resolve()))
            plan=freeze(Path(directory))
            self.assertEqual(plan,freeze(Path(directory)))
        ds=sorted(r["d"] for r in plan["designs"])
        self.assertGreaterEqual(min(b-a for a,b in zip(ds,ds[1:])),2e-5)
        for row in plan["designs"]:
            blocked=.195<=row["d"]<=.222
            self.assertEqual(blocked,row["split"]=="test_blocked")
            self.assertTrue(.30<=row["length"]<=.42)
            self.assertTrue(.15<=row["switch_fraction"]<=.90)

    def test_class_rates_and_phase_masking(self):
        rows=[]
        for exact,predicted,valid in ((180,180,True),(180,0,True),(0,180,True),(0,0,True),(180,None,False)):
            rows.append(dict(exact_phase_valid=True,predicted_phase_valid=valid,
                exact_separation=exact,predicted_separation=predicted,
                exact_min_magnitude=1,predicted_min_magnitude=1))
        result=classification(rows,15,.8)
        self.assertEqual([result[k] for k in ("tp","fn","tn","fp")],[1,2,1,1])
        self.assertEqual(result["phase_masked_predictions"],1)
        self.assertAlmostEqual(result["sensitivity"],1/3)
        self.assertEqual(result["specificity"],.5)


if __name__=="__main__":unittest.main()

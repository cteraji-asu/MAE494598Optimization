import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
import torch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'code'))
import optimizer_control as control
import switched_surrogate as original

class OptimizerSafeguards(unittest.TestCase):
    def setUp(self):
        torch.set_num_threads(1);torch.manual_seed(0)
        self.model=original.FieldNet(5)
        self.grid=control.training_grid([dict(d=.20),dict(d=.25)],3)

    def test_physics_closure_has_no_reference_label_access(self):
        expected=original.losses(self.model,*self.grid,'pinn')[0]
        with patch.object(original,'reference_right',side_effect=AssertionError('Reference accessed')):
            actual=control.physics_objective(self.model,self.grid)
            actual.backward()
        torch.testing.assert_close(actual,expected,rtol=1e-14,atol=1e-14)

    def test_budget_cap_retains_accepted_iterate_not_trial(self):
        # Force interruption before a first line-search trial can be evaluated.
        before=control.vector(self.model)
        result,_=control.continue_model(self.model,self.grid,'lbfgs',budget=1)
        self.assertEqual(result['evaluations'],1)
        self.assertTrue(result['cap_interrupted_line_search'])
        self.assertEqual(result['accepted_updates'],0)
        torch.testing.assert_close(control.vector(self.model),before,rtol=0,atol=0)

    def test_two_arms_respect_matching_call_cap(self):
        start=self.model.state_dict()
        a=original.FieldNet(5);a.load_state_dict(start)
        b=original.FieldNet(5);b.load_state_dict(start)
        ra,_=control.continue_model(a,self.grid,'lbfgs',budget=7)
        rb,_=control.continue_model(b,self.grid,'adam',budget=ra['evaluations'])
        self.assertEqual(ra['evaluations'],7)
        self.assertEqual(rb['evaluations'],7)
        self.assertGreater(ra['accepted_updates'],0)
        self.assertTrue(torch.isfinite(control.vector(a)).all())

    def test_frozen_geometry_only_separation(self):
        plan=json.loads((control.OUT/'frozen-protocol.json').read_text())
        allrows=[r for r in plan['designs'] if r['split']!='train']
        blocked=[r for r in allrows if .195<=r['d']<=.222]
        self.assertEqual(sum(r['split']=='validation' for r in blocked),64)
        self.assertEqual(sum(r['split']=='test_blocked' for r in blocked),128)
        ds=sorted(r['d'] for r in allrows)
        self.assertGreaterEqual(min(b-a for a,b in zip(ds,ds[1:])),2e-5)
        self.assertGreaterEqual(plan['split_amendment']['minimum_separation_from_prior'],2e-5)

if __name__=='__main__':unittest.main()

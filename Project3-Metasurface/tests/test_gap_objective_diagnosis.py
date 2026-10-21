from pathlib import Path
import sys,unittest
from unittest.mock import patch
import torch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'code'))
import gap_objective_diagnosis as study
import switched_surrogate as original

class GapDiagnosisSafeguards(unittest.TestCase):
    def setUp(self):
        torch.set_default_dtype(torch.float64);torch.manual_seed(0)
        self.model=original.FieldNet(5);self.grid=study.budget_control.training_grid([dict(d=.20),dict(d=.25)],3)
    def test_physics_terms_do_not_read_reference_labels(self):
        with patch.object(study,'reference_right',side_effect=AssertionError('Label access')):
            terms=study.components(self.model,self.grid);terms['physics'].backward()
        self.assertNotIn('data',terms)
    def test_separate_terms_match_original_physics_objective(self):
        expected=study.budget_control.physics_objective(self.model,self.grid)
        torch.testing.assert_close(study.components(self.model,self.grid)['physics'],expected,rtol=1e-14,atol=1e-14)
    def test_supervised_objective_uses_same_field_and_explicit_labels(self):
        target=study.reference_right(*self.grid).detach();terms=study.components(self.model,self.grid,target)
        expected=(self.model.values(*self.grid)-target).square().sum(1).mean()
        torch.testing.assert_close(terms['data'],expected,rtol=1e-14,atol=1e-14)
if __name__=='__main__':unittest.main()

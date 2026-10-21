from pathlib import Path
import sys,unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'code'))
from residual_error_budget import check_known_fields,polynomial_case

class ResidualIdentityTests(unittest.TestCase):
    def test_manufactured_fields_and_independent_wave_reference(self):
        rows=check_known_fields()
        self.assertEqual(len(rows),32)
        self.assertLess(max(r['maximum_identity_error'] for r in rows),1e-11)
    def test_isolated_boundary_and_interior_terms_have_correct_sign(self):
        for state in (0,1):
            for kind in ('port','short','interior'):
                result,direct=polynomial_case(.208395,.151605,state,128,kind)
                self.assertLess(abs(result[kind]-direct),1e-12)
                for other in {'port','short','interior'}-{kind}:
                    self.assertLess(abs(result[other]),1e-12)
                self.assertLessEqual(abs(direct),result['error_bound']+1e-12)
if __name__=='__main__':unittest.main()

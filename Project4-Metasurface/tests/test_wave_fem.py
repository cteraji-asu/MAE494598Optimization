import sys,unittest
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'code'))
from wave_fem import WaveFEM,Config
from verify_fem import verify
class ScientificTests(unittest.TestCase):
    def test_verification_ladder(self):
        report=verify()
        for check in report['checks']:
            with self.subTest(check=check['name']):self.assertTrue(check['passed'],check)
    def test_split_mesh_has_no_bridge(self):
        m=WaveFEM();self.assertEqual(m.x[m.left],m.x[m.right])
        self.assertFalse(any(a==m.left and b==m.right for a,b in m.edges))
        self.assertEqual(len(m.edges),80)
    def test_real_parameter_shape_and_finiteness(self):
        m=WaveFEM();v=m.evaluate(np.ones(20));self.assertEqual(v['constraint_jacobian'].shape,(4,20))
        self.assertTrue(np.isfinite(v['gradient']).all())
    def test_short_is_exact(self):
        m=WaveFEM();u,_,_=m.solve(np.ones(20),1);self.assertEqual(m.unpack(u)[-1],0j)
if __name__=='__main__':unittest.main()

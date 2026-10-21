import cmath
import math
from pathlib import Path
import sys
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/"code"))
from switched_line import Config, field, pair, phase_metrics, response, wave_reference


class SwitchedLineTests(unittest.TestCase):
    def test_independent_wave_solve_and_physical_conditions(self):
        for length, fraction in ((.30,.15),(.36,.3055555556),(.42,.90),(.36,.42)):
            for state in (0,1):
                config = Config()
                r = response(length, fraction, state)[0]
                self.assertLess(abs(r-wave_reference(length,fraction,state)[0]),1e-12)
                v, i = field(0,0,length,fraction,state)
                self.assertLess(abs(v+i-2),1e-12)
                self.assertLess(abs(field(1,1,length,fraction,state)[0]),1e-12)
                vl, il = field(1,0,length,fraction,state)
                vr, ir = field(0,1,length,fraction,state)
                self.assertLess(abs(il-ir),1e-12)
                self.assertLess(abs(vl-vr-config.impedance(state)*il),1e-12)
                self.assertLessEqual(abs(r),1+1e-12)

    def test_telegrapher_differential_equations(self):
        length, fraction, h = .36,.43,1e-6
        for segment in (0,1):
            ell = length*(fraction if segment==0 else 1-fraction)
            for state in (0,1):
                v,i=field(.37,segment,length,fraction,state)
                vp,ip=field(.37+h,segment,length,fraction,state)
                vm,im=field(.37-h,segment,length,fraction,state)
                self.assertLess(abs((vp-vm)/(2*h*ell)+Config().gamma*i),1e-8)
                self.assertLess(abs((ip-im)/(2*h*ell)+Config().gamma*v),1e-8)

    def test_discretized_baseline_converges_second_order(self):
        for state in (0,1):
            exact=response(.36,.43,state)[0]
            errors=[abs(response(.36,.43,state,intervals=n)[0]-exact) for n in (16,32,64)]
            self.assertGreater(errors[0]/errors[1],3.9)
            self.assertGreater(errors[1]/errors[2],3.9)

    def test_switch_loses_influence_at_current_node(self):
        row=pair(.36,1-.25/.36,Config(alpha=0))
        self.assertLess(row["separation_degrees"],1e-10)
        self.assertLess(row["on_switch_current"],1e-12)
        self.assertLess(row["off_switch_current"],1e-12)
        # The same two finite impedances can produce a large phase change elsewhere.
        rows=[pair(.36,.15+.75*j/1000) for j in range(1001)]
        self.assertLess(min(r["target_error_degrees"] for r in rows),1)
        self.assertLess(pair(.36,1-.25/.36)["separation_degrees"],1)

    def test_phase_metrics_and_mask(self):
        row=phase_metrics(cmath.exp(1j*math.radians(179)),cmath.exp(1j*math.radians(-179)))
        self.assertAlmostEqual(row["separation_degrees"],2)
        self.assertFalse(phase_metrics(.001,1)["phase_valid"])
        self.assertIsNone(phase_metrics(.001,1)["target_error_degrees"])


if __name__ == "__main__":
    unittest.main()

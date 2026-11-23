"""Checks the 23 Nov supplemental evidence against its own claims and the solver.

Core (NumPy/SciPy) environment. Re-solves one exact-solution rung so the saved
file cannot drift from the code, and checks that every multiplier and gradient
claim in the report is backed by the saved numbers.
"""
from pathlib import Path
import hashlib, json, sys, unittest
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'code'))


class Evidence(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.s = json.loads((ROOT/'assets/rubric-studies.json').read_text(encoding='utf-8'))
        cls.sl = json.loads((ROOT/'assets/surrogate-optimizer-loop.json').read_text(encoding='utf-8'))
        cls.d = json.loads((ROOT/'assets/results.json').read_text(encoding='utf-8'))

    def test_sources_match_current_code(self):
        for name in ['wave_fem.py', 'run_design.py']:
            self.assertEqual(hashlib.sha256((ROOT/'code'/name).read_bytes()).hexdigest(), self.s['provenance']['source_sha256'][name], name)

    def test_nonuniform_exact_rung_reproduces(self):
        from rubric_studies import abcd_reflection
        from wave_fem import WaveFEM, Config
        row = next(x for x in self.s['ladder']['nonuniform_abcd'] if x['design'] == 'random_2026')
        c = np.array(row['c']); cfg = Config(chi=0); m = WaveFEM(cfg, 16)
        for st in (0, 1):
            exact = abcd_reflection(cfg, c, st); fe = m.unpack(m.solve(c, st)[0])[0]-1
            self.assertLess(abs(fe-exact)/abs(exact), 5e-5)
            self.assertAlmostEqual(exact.real, row['exact'][st][0], 12)
        self.assertTrue(all(abs(r-2) < .02 for r in row['rates']))

    def test_ladder_and_gradients(self):
        self.assertLess(max(x['relative_error'] for x in self.s['ladder']['lossless']), 1e-8)
        self.assertLess(max(max(x['relative_errors']) for x in self.s['gradients']['coordinate']), 1e-4)
        self.assertGreater(min(o for x in self.s['gradients']['step_sweep'] for o in x['order_first_decade']), 1.6)

    def test_cost_scaling(self):
        rows = sorted(self.s['cost'], key=lambda r: r['design_variables'])
        self.assertTrue(all(r['finite_difference_forward_solves'] == 4*r['design_variables'] for r in rows))
        self.assertTrue(all(r['adjoint_forward_solves'] == 2 for r in rows))
        self.assertGreater(rows[-1]['ratio'], rows[0]['ratio'])

    def test_multipliers_predict_resolves(self):
        k = self.s['kkt_relaxation']
        for r in k['single_bounds']:
            self.assertTrue(r['success'])
            self.assertLess(abs(r['actual_change']-r['predicted_change']), .05*abs(r['predicted_change'])+1e-6, r['bound'])
        for r in self.s['limit_sweep']:
            chk = r.get('multiplier_check')
            if chk:
                self.assertLess(abs(chk['finite_difference']-chk['predicted']), .01*abs(chk['predicted']), (r['chi'], r['energy_limit']))

    def test_frozen_design_recovered(self):
        frozen = next(r for r in self.s['limit_sweep'] if r['chi'] == .05 and r['energy_limit'] == 1.6)['best']
        self.assertLess(max(abs(a-b) for a, b in zip(frozen['c'], self.d['nonlinear']['final']['c'])), 1e-8)
        self.assertAlmostEqual(frozen['objective'], self.d['nonlinear']['final']['objective'], 10)

    def test_surrogate_loop_claims(self):
        ref = self.sl['reference']['selected']
        self.assertAlmostEqual(ref['d'], .2084, 3)
        models = self.sl['models']; self.assertEqual(len(models), 12)
        self.assertFalse(any(abs(r['d']-ref['d']) < 5e-3 for m in models for r in m['runs']), 'no surrogate reaches the interior optimum')
        self.assertTrue(all(.8 < m['grid_gradient_relative_L2'] < 1.6 for m in models))
        for m in models:
            self.assertGreater(m['selected']['surrogate_objective'], 10*m['selected']['fe_objective'])


    def test_scaling_and_newton_diagnosis(self):
        cf = np.array(self.d['nonlinear']['final']['c'])
        ok = [r for r in self.s['scaled_constraints']['runs'] if r['success']]
        self.assertGreaterEqual(len(ok), 4)
        for r in ok:
            self.assertLess(np.max(abs(np.array(r['c'])-cf)), 1e-8)
        off = next(x for x in self.s['newton_failure']['states'] if x['state'] == 'off')
        self.assertEqual(off['direct_newton'], 'Newton line search failed')
        self.assertFalse(off['continuation_converged'])

    def test_fd_at_good_step(self):
        self.assertLess(max(max(x['relative_errors']) for x in self.s['gradients']['coordinate_h1e3']), 1e-5)

    def test_surrogate_band_claims(self):
        for m in self.sl['models']:
            inside, low = m['band']['inside'], m['band']['outside_low']
            self.assertGreater(inside['objective_mae'], 2*low['objective_mae'])
            self.assertGreater(abs(inside['surrogate_argmin']-inside['fe_argmin']), 2e-3)


if __name__ == '__main__':
    unittest.main()

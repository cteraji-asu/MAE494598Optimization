"""Independent equation, convergence and analytic-gradient checks."""
import cmath
import math
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "code"))
from helmholtz import Network, exact, finite_difference, loss_gradient, relative_l2, spectrum, train


class HelmholtzTests(unittest.TestCase):
    def test_exact_manual_points_and_boundary(self):
        self.assertAlmostEqual(abs(exact(0, 7) - 1), 0)
        self.assertAlmostEqual(abs(exact(1, math.pi) + 1), 0)
        self.assertAlmostEqual(abs(exact(0.5, math.pi) - 1j), 0)
        for k in (1, 5, 20):
            h, x = 1e-5, 0.37
            center = exact(x, k)
            residual = (exact(x+h, k)-2*center+exact(x-h, k))/h**2+k*k*center
            self.assertLess(abs(residual), 1e-4)
            derivative = (exact(1+h, k)-exact(1-h, k))/(2*h)
            self.assertLess(abs(derivative-1j*k*exact(1, k)), 1e-6)

    def test_fd_equations_and_refinement(self):
        for k in (1, 5, 10, 20):
            errors = []
            for n in (128, 256, 512, 1024):
                x, u = finite_difference(k, n)
                errors.append(relative_l2(u, [exact(a, k) for a in x]))
                h = 1/n
                self.assertEqual(u[0], 1)
                for j in range(1, n):
                    self.assertLess(abs(u[j-1]+(-2+(k*h)**2)*u[j]+u[j+1]), 1e-12)
                self.assertLess(abs(2*u[-2]+(-2+(k*h)**2+2j*k*h)*u[-1]), 1e-12)
            for coarse, fine in zip(errors, errors[1:]):
                self.assertGreater(coarse/fine, 3.8)
                self.assertLess(coarse/fine, 4.2)
            self.assertLess(errors[-1], 0.001)

    def test_analytic_spatial_derivatives(self):
        net, x, h = Network(4, 7), 0.37, 1e-4
        u, ux, uxx, _ = net.jet(x)
        a, b, c = net.value(x-h), net.value(x), net.value(x+h)
        self.assertLess(abs(complex(*u)-b), 1e-14)
        self.assertLess(abs(complex(*ux)-(c-a)/(2*h)), 1e-7)
        self.assertLess(abs(complex(*uxx)-(c-2*b+a)/h**2), 1e-6)

    def test_loss_parameter_gradients(self):
        for mode in ("pinn", "supervised"):
            net = Network(3, 3)
            points = [0.1, 0.37, 0.83]
            _, _, gradient = loss_gradient(net, 5, points, mode)
            for j, analytic in enumerate(gradient):
                saved, h = net.p[j], 1e-6
                net.p[j] = saved+h
                plus = loss_gradient(net, 5, points, mode)[0]
                net.p[j] = saved-h
                minus = loss_gradient(net, 5, points, mode)[0]
                net.p[j] = saved
                self.assertAlmostEqual(analytic, (plus-minus)/(2*h), delta=2e-6)

    def test_relative_l2_manual(self):
        # Constant complex reference, prediction exactly half its amplitude.
        self.assertAlmostEqual(relative_l2([0.5j]*5, [1j]*5), 0.5)

    def test_spectrum_known_mode(self):
        errors = [cmath.exp(2j*math.pi*3*j/32) for j in range(32)]
        bins = spectrum(errors)
        peak = max(bins, key=lambda r:r["amplitude"])
        self.assertEqual(peak["cycles_per_domain"], 3)
        self.assertAlmostEqual(peak["amplitude"], 1)

    def test_training_determinism_and_descent(self):
        for mode in ("pinn", "supervised"):
            a, history, _ = train(1, 0, mode, 10, 4, 8, 10)
            b, _, _ = train(1, 0, mode, 10, 4, 8, 10)
            self.assertEqual(a.p, b.p)
            self.assertLess(history[-1]["objective"], history[0]["objective"])

    def test_invalid_configuration(self):
        for k, n in ((0, 64), (-1, 64), (float("nan"), 64), (10, 3), (100, 64)):
            with self.assertRaises(ValueError):
                finite_difference(k, n)


if __name__ == "__main__":
    unittest.main()

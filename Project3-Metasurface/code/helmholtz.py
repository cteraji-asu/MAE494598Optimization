"""Small, dependency-free, complex 1-D Helmholtz diagnostic.

All fields use exp(-i omega t). This synthetic model is not an HFSS replacement.
The one-hidden-layer tanh PINN uses exact analytic derivatives and Adam.
"""
import argparse
import cmath
import csv
import json
import math
import os
import platform
import random
import statistics
import time
from pathlib import Path


def exact(x, k):
    return cmath.exp(1j * k * x)


def finite_difference(k, n):
    """Centered interior scheme; centered outgoing BC with a PDE ghost point.

    x_j=j/n, u_0=1. Last row: 2 u_(n-1) +
    (-2+(kh)^2+2ikh)u_n=0. Elimination is O(n), complex arithmetic.
    """
    if not math.isfinite(k) or k <= 0 or n < 4 or k / n >= 1:
        raise ValueError("Require finite k>0, n>=4 and k/n<1")
    h = 1 / n
    diagonal = [complex(-2 + (k * h) ** 2) for _ in range(n)]
    diagonal[-1] += 2j * k * h
    lower = [1.0] * n
    lower[-1] = 2.0
    rhs = [-1 + 0j] + [0j] * (n - 1)
    for i in range(1, n):
        multiplier = lower[i] / diagonal[i - 1]
        diagonal[i] -= multiplier
        rhs[i] -= multiplier * rhs[i - 1]
    answer = [0j] * n
    answer[-1] = rhs[-1] / diagonal[-1]
    for i in range(n - 2, -1, -1):
        answer[i] = (rhs[i] - answer[i + 1]) / diagonal[i]
    return [j / n for j in range(n + 1)], [1 + 0j] + answer


def relative_l2(prediction, reference):
    if len(prediction) != len(reference) or len(reference) < 2:
        raise ValueError("Require matching nonempty uniform grids")
    # Composite trapezoidal weights, shared spacing cancels in the ratio.
    weights = [0.5] + [1.0] * (len(reference) - 2) + [0.5]
    denominator = sum(w * abs(v) ** 2 for w, v in zip(weights, reference))
    if denominator == 0:
        raise ValueError("Reference norm is zero")
    return math.sqrt(sum(w * abs(a - b) ** 2 for w, a, b in
                         zip(weights, prediction, reference)) / denominator)


class Network:
    """1 -> width tanh -> 2, shared hidden units, float64 Python floats."""
    def __init__(self, width=24, seed=0):
        rng = random.Random(seed)
        self.width = width
        # Frequency-independent initialization, identical in paired controls.
        self.p = ([rng.uniform(-2, 2) for _ in range(width)] +
                  [rng.uniform(-1, 1) for _ in range(width)] +
                  [rng.gauss(0, 1 / math.sqrt(width)) for _ in range(2 * width)] +
                  [0.0, 0.0])

    def jet(self, x):
        m, p = self.width, self.p
        value = p[4 * m:4 * m + 2].copy()
        first, second, cache = [0.0, 0.0], [0.0, 0.0], []
        for j in range(m):
            w = p[j]
            t = math.tanh(w * x + p[m + j])
            t1 = 1 - t * t
            t2 = -2 * t * t1
            t3 = -2 + 8 * t * t - 6 * t ** 4
            cache.append((t, t1, t2, t3))
            for c in range(2):
                a = p[(2 + c) * m + j]
                value[c] += a * t
                first[c] += a * w * t1
                second[c] += a * w * w * t2
        return value, first, second, (x, cache)

    def accumulate(self, gradient, cache, lv, ld=(0, 0), ldd=(0, 0)):
        """Add dL/dparameters given sensitivities to u, u', u''."""
        x, neurons = cache
        m, p = self.width, self.p
        for j, (t, t1, t2, t3) in enumerate(neurons):
            w = p[j]
            for c in range(2):
                index = (2 + c) * m + j
                a = p[index]
                gradient[j] += a * (lv[c] * t1 * x +
                    ld[c] * (t1 + w * t2 * x) +
                    ldd[c] * (2 * w * t2 + w * w * t3 * x))
                gradient[m + j] += a * (lv[c] * t1 +
                    ld[c] * w * t2 + ldd[c] * w * w * t3)
                gradient[index] += (lv[c] * t + ld[c] * w * t1 +
                                    ldd[c] * w * w * t2)
        gradient[4 * m] += lv[0]
        gradient[4 * m + 1] += lv[1]

    def value(self, x):
        # Inference excludes derivative computation, as a deployed forward pass would.
        m, p = self.width, self.p
        real, imag = p[4 * m:4 * m + 2]
        for j in range(m):
            t = math.tanh(p[j] * x + p[m + j])
            real += p[2 * m + j] * t
            imag += p[3 * m + j] * t
        return complex(real, imag)


def loss_gradient(net, k, points, mode):
    """Equal weights on scaled PDE, Dirichlet, outgoing losses, or data only.

    PDE divided by max(1,k^2), outgoing residual divided by max(1,k).
    These are declared experimental choices, not researcher tolerances.
    """
    gradient = [0.0] * len(net.p)
    components = dict(pde=0.0, dirichlet=0.0, outgoing=0.0, data=0.0)
    n, scale = len(points), max(1.0, k * k)
    if mode not in ("pinn", "supervised") or not points or k <= 0:
        raise ValueError("Invalid loss configuration")
    for x in points:
        u, _, uxx, cache = net.jet(x)
        if mode == "supervised":
            ref = exact(x, k)
            r = [u[0] - ref.real, u[1] - ref.imag]
            components["data"] += sum(v * v for v in r) / n
            net.accumulate(gradient, cache, [2 * v / n for v in r])
        else:
            r = [(uxx[c] + k * k * u[c]) / scale for c in range(2)]
            components["pde"] += sum(v * v for v in r) / n
            multiplier = [2 * v / (n * scale) for v in r]
            net.accumulate(gradient, cache,
                           [k * k * v for v in multiplier], ldd=multiplier)
    if mode == "pinn":
        u, _, _, cache = net.jet(0)
        r = [u[0] - 1, u[1]]
        components["dirichlet"] = sum(v * v for v in r)
        net.accumulate(gradient, cache, [2 * v for v in r])
        u, ux, _, cache = net.jet(1)
        s = max(1.0, k)
        r = [(ux[0] + k * u[1]) / s, (ux[1] - k * u[0]) / s]
        components["outgoing"] = sum(v * v for v in r)
        a, b = [2 * v / s for v in r]
        net.accumulate(gradient, cache, [-k * b, k * a], [a, b])
    return sum(components.values()), components, gradient


def train(k, seed, mode, steps, width, count, log_every=100):
    net = Network(width, seed)
    rng = random.Random(seed + 91001)
    points = sorted(rng.random() for _ in range(count))
    first, second = [0.0] * len(net.p), [0.0] * len(net.p)
    history = []
    started = time.perf_counter()
    for step in range(steps + 1):
        total, components, gradient = loss_gradient(net, k, points, mode)
        if step % log_every == 0 or step == steps:
            physics = components if mode == "pinn" else loss_gradient(net, k, points, "pinn")[1]
            history.append(dict(step=step, objective=total,
                                data=components["data"], **{x: physics[x] for x in
                                ("pde", "dirichlet", "outgoing")}))
        if step == steps:
            break
        for i, g in enumerate(gradient):
            first[i] = 0.9 * first[i] + 0.1 * g
            second[i] = 0.999 * second[i] + 0.001 * g * g
            corrected_first = first[i] / (1 - 0.9 ** (step + 1))
            corrected_second = second[i] / (1 - 0.999 ** (step + 1))
            net.p[i] -= 0.003 * corrected_first / (math.sqrt(corrected_second) + 1e-8)
    return net, history, time.perf_counter() - started


def write_csv(path, rows):
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def spectrum(error):
    # Full complex DFT. O(n^2), n=256 only; signed bins retained.
    n = len(error)
    return [dict(cycles_per_domain=j if j < (n + 1) // 2 else j - n,
                 amplitude=abs(sum(v * cmath.exp(-2j * math.pi * j * q / n)
                                   for q, v in enumerate(error))) / n)
            for j in range(n)]


def run(args):
    out = Path(args.output)
    out.mkdir(parents=True, exist_ok=True)
    summary, baselines = [], []
    for k in args.k:
        for n in (128, 256, 512, 1024):
            durations = []
            for _ in range(7):
                started = time.perf_counter()
                x, values = finite_difference(k, n)
                durations.append(time.perf_counter() - started)
            baselines.append(dict(k=k, intervals=n, relative_l2=relative_l2(
                values, [exact(a, k) for a in x]), median_solve_seconds=statistics.median(durations)))
        x, fd = finite_difference(k, 1024)
        reference = [exact(a, k) for a in x]
        for seed in args.seeds:
            for mode in ("pinn", "supervised"):
                net, history, seconds = train(k, seed, mode, args.steps, args.width, args.points)
                prefix = f"k-{k:g}_seed-{seed}_{mode}"
                prediction = [net.value(a) for a in x]
                # Median of 11 identical full field evaluations, no startup or disk IO.
                inference_times = []
                for _ in range(11):
                    started = time.perf_counter()
                    [net.value(a) for a in x]
                    inference_times.append(time.perf_counter() - started)
                row = dict(k=k, seed=seed, mode=mode,
                    relative_l2_exact=relative_l2(prediction, reference),
                    relative_l2_fd=relative_l2(prediction, fd),
                    training_seconds=seconds,
                    inference_1025_points_seconds=statistics.median(inference_times),
                    **{f"final_{key}": value for key, value in history[-1].items() if key != "step"})
                summary.append(row)
                write_csv(out / f"{prefix}_loss.csv", history)
                write_csv(out / f"{prefix}_field.csv", [dict(x=a, exact_real=b.real,
                    exact_imag=b.imag, fd_real=c.real, fd_imag=c.imag,
                    predicted_real=d.real, predicted_imag=d.imag, abs_error=abs(d-b))
                    for a, b, c, d in zip(x, reference, fd, prediction)])
                # No duplicate endpoint in DFT. Error need not be periodic; leakage is possible.
                error = [net.value(j / 256) - exact(j / 256, k) for j in range(256)]
                write_csv(out / f"{prefix}_spectrum.csv", spectrum(error))
                (out / f"{prefix}_parameters.json").write_text(
                    json.dumps(dict(width=net.width, parameters=net.p)), encoding="utf-8")
                print(json.dumps(row), flush=True)
    write_csv(out / "summary.csv", summary)
    write_csv(out / "baseline-refinement.csv", baselines)
    hardware = dict(python=platform.python_version(), platform=platform.platform(),
                    processor=platform.processor(), processor_identifier=os.getenv("PROCESSOR_IDENTIFIER"),
                    logical_processors=os.cpu_count(), gpu_used=False,
                    execution="single Python process, standard library, Python float64")
    (out / "run-config.json").write_text(json.dumps(dict(
        k=args.k, seeds=args.seeds, steps=args.steps, width=args.width,
        points=args.points, learning_rate=0.003, hardware=hardware,
        timing="training includes loss diagnostics; excludes startup/disk IO; median inference=11 repeats; FD=7 repeats",
        status="pilot; no researcher accuracy threshold; retrained for each k"), indent=2), encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="outputs/pilot")
    parser.add_argument("--k", nargs="+", type=float, default=[1, 5, 10, 20])
    parser.add_argument("--seeds", nargs="+", type=int, default=[0, 1, 2])
    parser.add_argument("--steps", type=int, default=3000)
    parser.add_argument("--width", type=int, default=24)
    parser.add_argument("--points", type=int, default=64)
    options = parser.parse_args()
    if options.steps < 1 or options.width < 1 or options.points < 2:
        parser.error("Require steps>=1, width>=1, points>=2")
    run(options)

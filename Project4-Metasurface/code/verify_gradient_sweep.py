"""Supplemental central-FD audit; never replaces historical verification/results.

Run with --output NEW_PATH. Uses fixed interior designs and directions and records
every step, including roundoff deterioration. No optimizer or neural training.
"""
import argparse
import hashlib
import json
from pathlib import Path
import platform
import time
import numpy as np
import scipy
from wave_fem import Config, WaveFEM


def verify():
    rng = np.random.default_rng(4942026)
    steps = np.array([.64, .32, .16, .08, .04, .02, .01, .005, .0025, .00125,
                      1e-4, 1e-5, 1e-6, 1e-7, 1e-8])
    names = ['objective', 'amplitude_on', 'amplitude_off', 'energy_on', 'energy_off']
    cases = []
    start = time.perf_counter()
    for design_id in range(3):
        c = rng.uniform(.85, 1.15, 20)
        model = WaveFEM(Config(), 8)
        base = model.evaluate(c)
        jac = np.vstack([base['gradient'], base['constraint_jacobian']])
        for direction_id in range(3):
            direction = rng.normal(size=20)
            direction /= np.linalg.norm(direction)
            assert np.all(c - steps[0]*np.abs(direction) > .5)
            assert np.all(c + steps[0]*np.abs(direction) < 2.5)
            exact = jac @ direction
            estimates = []
            for h in steps:
                plus = model.evaluate(c + h * direction, False)
                minus = model.evaluate(c - h * direction, False)
                estimates.append((np.r_[plus['objective'], plus['constraints']] -
                                  np.r_[minus['objective'], minus['constraints']]) / (2*h))
            errors = np.abs(np.array(estimates) - exact)
            # Fixed within this run. Earlier retained runs started at .04/.32;
            # their windows hit the numerical floor, so the range was extended.
            orders = np.log2(np.maximum(errors[:5], 1e-300) /
                             np.maximum(errors[1:6], 1e-300))
            scaled = errors / np.maximum(np.abs(exact), 1e-4)
            checks = []
            for i, name in enumerate(names):
                # Require three consecutive near-second-order reductions among
                # five fixed halvings, plus an accurate central-FD estimate.
                good = (orders[:, i] > 1.75) & (orders[:, i] < 2.25)
                convergence = any(bool(np.all(good[j:j+3])) for j in range(3))
                accurate = bool(np.min(scaled[:, i]) < 2e-5)
                checks.append(dict(metric=name, second_order=convergence,
                                   accurate=accurate, passed=convergence and accurate))
            cases.append(dict(design_id=design_id, direction_id=direction_id,
                              design=c.tolist(), direction=direction.tolist(),
                              adjoint_directional_derivatives=exact.tolist(),
                              central_difference_estimates=np.array(estimates).tolist(),
                              absolute_errors=errors.tolist(), scaled_errors=scaled.tolist(),
                              early_halving_orders=orders.tolist(), checks=checks))
    source = Path(__file__)
    return dict(passed=all(x['passed'] for c in cases for x in c['checks']),
                seed=4942026, metric_names=names, steps=steps.tolist(),
                design_count=3, directions_per_design=3, per_cell=8,
                model='default nonlinear chi=.05, ON and OFF states',
                criteria='At least 3 consecutive orders in (1.75,2.25) within first 5 fixed halvings; minimum scaled error <2e-5 for every metric/direction. Scale=max(abs(adjoint directional derivative),1e-4).',
                limits='Interior synthetic designs; no global sensitivity certificate, fresh optimization, PINN training, or physical validation.',
                python=platform.python_version(), numpy=np.__version__, scipy=scipy.__version__,
                source_sha256={p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                               for p in [source, source.with_name('wave_fem.py')]},
                seconds=time.perf_counter()-start, cases=cases)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error('Output exists; refusing to overwrite retained evidence')
    result = verify()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('x', encoding='utf-8') as stream:
        json.dump(result, stream, indent=2, allow_nan=False)
        stream.write('\n')
    print(json.dumps(dict(passed=result['passed'], cases=len(result['cases']),
                          metric_checks=sum(len(c['checks']) for c in result['cases']),
                          seconds=result['seconds'], output=str(args.output))))
    raise SystemExit(0 if result['passed'] else 1)

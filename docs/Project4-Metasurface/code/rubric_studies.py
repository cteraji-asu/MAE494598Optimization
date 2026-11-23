"""Supplemental FE studies added on 23 Nov 2026 for the rubric polish.

These are NEW runs on the unchanged solver (wave_fem.py) and frozen design
protocol (run_design.py). They do not overwrite assets/results.json. Every
study is labelled with its role:

  * ladder    - extra verification rungs (exact nonuniform-loading solution,
                lossless conservation, central-difference step sweep)
  * cost      - adjoint versus finite-difference timing and its scaling with n
  * kkt       - bound-relaxation re-solves that test the reported multipliers
  * post_hoc  - sensitivity studies run after the frozen design was known
                (voltage-limit sweep, nonlinearity-strength sweep). They do
                not replace the frozen formulation or its selected design.

Usage: python code/rubric_studies.py [--output PATH]
"""
from pathlib import Path
from dataclasses import asdict, replace
import argparse, hashlib, json, platform, sys, time
import numpy as np
import scipy
from scipy.optimize import minimize

sys.path.insert(0, str(Path(__file__).resolve().parent))
from wave_fem import WaveFEM, Config  # noqa: E402
from run_design import kkt  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
METRICS = ['objective', 'amplitude_on', 'amplitude_off', 'energy_on', 'energy_off']


def metrics(v):
    return np.r_[v['objective'], v['constraints']]


# ---------------------------------------------------------------- ladder
def abcd_reflection(cfg, c, state):
    """Exact transfer-matrix cascade for piecewise-constant loading (chi=0).

    V' = -z I, I' = -y_j V on each cell; switch V(a-) = V(a+) + Zs I(a).
    Independent of the FE code: no mesh, no quadrature, no assembly.
    """
    z = cfg.alpha + 1j*cfg.beta
    zs = (cfg.z_on, cfg.z_off)[state]
    ell = cfg.length/cfg.cells
    T = np.eye(2, dtype=complex)
    for j in range(cfg.cells):
        if j == cfg.switch_cell:
            T = T @ np.array([[1, zs], [0, 1]])
        y = cfg.alpha + 1j*cfg.beta*c[j]
        g = np.sqrt(z*y); Zc = np.sqrt(z/y)
        T = T @ np.array([[np.cosh(g*ell), Zc*np.sinh(g*ell)],
                          [np.sinh(g*ell)/Zc, np.cosh(g*ell)]])
    V0, I0 = T @ np.array([0, 1])  # short: V(L)=0, I(L)=1 then rescale
    k = 2/(V0+I0)
    return k*V0-1


def ladder_nonuniform(designs):
    out = []
    for name, c in designs:
        cfg = Config(chi=0)
        exact = [abcd_reflection(cfg, c, s) for s in (0, 1)]
        levels = []
        for p in [1, 2, 4, 8, 16, 32]:
            m = WaveFEM(cfg, p)
            fe = [m.unpack(m.solve(c, s)[0])[0]-1 for s in (0, 1)]
            levels.append(dict(per_cell=p, elements=20*p,
                               fe=[[float(r.real), float(r.imag)] for r in fe],
                               relative_error=float(max(abs(a-b)/abs(b) for a, b in zip(fe, exact)))))
        err = np.array([x['relative_error'] for x in levels])
        out.append(dict(design=name, c=list(map(float, c)),
                        exact=[[float(r.real), float(r.imag)] for r in exact],
                        levels=levels, rates=np.log2(err[:-1]/err[1:]).tolist()))
    return out


def ladder_lossless(designs):
    """alpha=0 and purely reactive switches: all incident power returns, |R|=1.

    Holds for the cubic model too because i*beta*chi*|V|^2 V is reactive.
    Catches sign errors in the loss, switch or nonlinear terms.
    """
    out = []
    for chi in [0.0, 0.05]:
        cfg = Config(alpha=0.0, z_on=0.04j, z_off=-4j, chi=chi)
        m = WaveFEM(cfg, 8)
        for name, c in designs:
            for s in (0, 1):
                u, _, hist = m.solve(c, s)
                R = m.unpack(u)[0]-1
                out.append(dict(chi=chi, design=name, state=['on', 'off'][s], computed=float(abs(R)),
                                exact=1.0, relative_error=float(abs(abs(R)-1)), newton_iterations=len(hist)-1))
    return out


def step_sweep(c, seed, label):
    """Central-difference error versus step for every metric (Taylor test)."""
    m = WaveFEM(Config(), 8)
    v = m.evaluate(c)
    G = np.vstack([v['gradient'], v['constraint_jacobian']])
    rng = np.random.default_rng(seed)
    d = rng.normal(size=20); d /= np.linalg.norm(d)
    exact = G @ d
    steps = (10.0**-np.arange(1, 9.01, .5)).tolist()
    errs = []
    for h in steps:
        fd = (metrics(m.evaluate(c+h*d, False))-metrics(m.evaluate(c-h*d, False)))/(2*h)
        errs.append((abs(fd-exact)/np.maximum(abs(exact), 1e-12)).tolist())
    E = np.array(errs)
    best = E.min(axis=0)
    # observed order over the first decade, before round-off dominates
    order = (np.log10(E[0]/E[2])/1.0).tolist()
    return dict(design=label, direction_seed=seed, adjoint_directional=exact.tolist(),
                steps=steps, relative_errors=errs, best_relative_error=best.tolist(),
                order_first_decade=order, metric_names=METRICS)


def coordinate_check(c, label, h=1e-5):
    """All 20 coordinates, central difference with step h, every metric."""
    m = WaveFEM(Config(), 8)
    v = m.evaluate(c)
    G = np.vstack([v['gradient'], v['constraint_jacobian']])
    F = np.zeros_like(G)
    for j in range(20):
        e = np.eye(20)[j]*h
        F[:, j] = (metrics(m.evaluate(c+e, False))-metrics(m.evaluate(c-e, False)))/(2*h)
    rel = np.linalg.norm(G-F, axis=1)/np.maximum(np.linalg.norm(F, axis=1), 1e-14)
    return dict(design=label, step=h, relative_errors=rel.tolist(),
                adjoint_norm=np.linalg.norm(G, axis=1).tolist(), metric_names=METRICS)


# ---------------------------------------------------------------- cost
def cost_scaling(repeats=7):
    rows = []
    for cells, per in [(10, 16), (20, 8), (40, 4), (80, 2)]:
        cfg = Config(cells=cells, switch_cell=int(round(.3*cells)))
        m = WaveFEM(cfg, per)
        c = 1+.2*np.sin(np.arange(cells))
        ta, tf = [], []
        for _ in range(repeats):
            m.solve_count = 0; t = time.perf_counter(); m.evaluate(c); ta.append(time.perf_counter()-t)
            adj_solves = m.solve_count
            m.solve_count = 0; t = time.perf_counter()
            for j in range(cells):
                e = np.eye(cells)[j]*1e-5
                m.evaluate(c+e, False); m.evaluate(c-e, False)
            tf.append(time.perf_counter()-t); fd_solves = m.solve_count
        rows.append(dict(design_variables=cells, elements=cells*per,
                         adjoint_seconds_median=float(np.median(ta)), finite_difference_seconds_median=float(np.median(tf)),
                         adjoint_forward_solves=adj_solves, adjoint_transposed_solves=2, adjoint_rhs=10,
                         finite_difference_forward_solves=fd_solves, repeats=repeats,
                         ratio=float(np.median(tf)/np.median(ta))))
    return rows


# ---------------------------------------------------------------- optimizer helpers
def run_slsqp(m, c0, lower=None, upper=None, maxiter=500):
    n = m.cfg.cells
    lower = np.full(n, .5) if lower is None else lower
    upper = np.full(n, 2.5) if upper is None else upper
    cache = {}

    def ev(c):
        if 'x' not in cache or not np.array_equal(cache['x'], c):
            cache.update(x=c.copy(), v=m.evaluate(c))
        return cache['v']
    r = minimize(lambda c: ev(c)['objective'], c0, jac=lambda c: ev(c)['gradient'], method='SLSQP',
                 bounds=list(zip(lower, upper)),
                 constraints=[dict(type='ineq', fun=lambda c: ev(c)['constraints'], jac=lambda c: ev(c)['constraint_jacobian'])],
                 options=dict(maxiter=maxiter, ftol=1e-11))
    v = ev(r.x)
    return r, v


def summarize(m, c, v, r=None):
    R = v['R']
    return dict(c=np.asarray(c).tolist(), objective=float(v['objective']), constraints=v['constraints'].tolist(),
                phase_separation_degrees=float(abs(np.angle(R[0]/R[1], deg=True))),
                reflection_magnitude=[float(abs(x)) for x in R], energy=[float(e) for e in v['energy']],
                feasible=bool(min(v['constraints']) >= -1e-7),
                success=None if r is None else bool(r.success), message=None if r is None else str(r.message),
                iterations=None if r is None else int(r.nit))


def starts():
    rng = np.random.default_rng(494)
    return [('uniform', np.ones(20)), ('low_high', np.r_[np.full(6, .5), np.full(14, 2.5)]),
            ('high_low', np.r_[np.full(6, 2.5), np.full(14, .5)]),
            ('random_494_a', rng.uniform(.5, 2.5, 20)), ('random_494_b', rng.uniform(.5, 2.5, 20))]


def best_of(cfg, start_list):
    m = WaveFEM(cfg, 8); runs = []; best = None
    for name, c0 in start_list:
        try:
            r, v = run_slsqp(m, np.array(c0, float))
            s = summarize(m, r.x, v, r); k = kkt(r.x, v)
            s.update(start=name, kkt_accepted=k['accepted'], stationarity_inf=k['stationarity_inf'],
                     multipliers={a: b for a, b in k['multipliers'].items()})
            if r.success and s['feasible'] and k['accepted'] and (best is None or s['objective'] < best['objective']):
                best = s
        except RuntimeError as e:
            s = dict(start=name, success=False, message=str(e))
        runs.append(s)
    return best, runs


# ---------------------------------------------------------------- KKT check
def kkt_relaxation(base_c, multipliers, delta=0.02):
    """Relax one active bound at a time by delta and re-solve from the optimum.

    Convention: L = f - sum(mu g), g >= 0. Relaxing bound j by delta should
    change the optimum by approximately -mu_j*delta.
    """
    m = WaveFEM(Config(), 8)
    f0 = m.evaluate(base_c)['objective']
    rows = []
    for name, mu in multipliers.items():
        kind, j = name.split('_'); j = int(j)
        lo = np.full(20, .5); hi = np.full(20, 2.5)
        if kind == 'lower':
            lo[j] -= delta; c0 = base_c.copy()
        else:
            hi[j] += delta; c0 = base_c.copy()
        r, v = run_slsqp(m, c0, lo, hi)
        rows.append(dict(bound=name, cell=j+1, multiplier=mu, delta=delta, predicted_change=-mu*delta,
                         actual_change=float(v['objective']-f0), success=bool(r.success),
                         moved_to=float(r.x[j]), feasible=bool(min(v['constraints']) >= -1e-7)))
    # all bounds widened together
    lo = np.full(20, .5-delta); hi = np.full(20, 2.5+delta)
    r, v = run_slsqp(m, base_c.copy(), lo, hi)
    total = dict(delta=delta, predicted_change=-sum(multipliers.values())*delta,
                 actual_change=float(v['objective']-f0), success=bool(r.success))
    return dict(base_objective=float(f0), single_bounds=rows, all_bounds=total)


# ---------------------------------------------------------------- post hoc studies
def limit_sweep(frozen):
    """Tighten the mean-square-voltage limit until it becomes active.

    For each limit and each physics model: best of the five frozen starts plus
    a warm start from the frozen-limit optimum. The energy multiplier is checked
    against a finite difference of re-solved optima.
    """
    out = []
    for chi in [0.0, 0.05]:
        for E in [1.6, 1.05, 1.0, 0.95, 0.9]:
            cfg = Config(chi=chi, energy_limit=E)
            best, runs = best_of(cfg, starts()+[('warm_frozen_optimum', frozen)])
            row = dict(chi=chi, energy_limit=E, best=best, runs=[{k: v for k, v in r.items() if k != 'c'} for r in runs])
            if best is not None:
                mu = {k: v for k, v in best['multipliers'].items() if k.startswith('energy')}
                row['energy_multipliers'] = mu
                if mu:
                    eps = .005
                    m2 = WaveFEM(Config(chi=chi, energy_limit=E+eps), 8)
                    r2, v2 = run_slsqp(m2, np.array(best['c']))
                    row['multiplier_check'] = dict(step=eps, finite_difference=float((v2['objective']-best['objective'])/eps),
                                                   predicted=-float(sum(mu.values())), success=bool(r2.success))
            out.append(row)
    # with / without: optimize with the linear model, evaluate in the nonlinear model
    cross = []
    for E in [1.6, 1.05, 1.0, 0.95, 0.9]:
        lin = next(r for r in out if r['chi'] == 0 and r['energy_limit'] == E)['best']
        nl = next(r for r in out if r['chi'] == .05 and r['energy_limit'] == E)['best']
        if lin is None or nl is None:
            cross.append(dict(energy_limit=E, available=False)); continue
        m = WaveFEM(Config(chi=.05, energy_limit=E), 8)
        v = m.evaluate(np.array(lin['c']), False)
        cross.append(dict(energy_limit=E, available=True,
                          max_design_difference=float(np.max(abs(np.array(lin['c'])-np.array(nl['c'])))),
                          linear_design_in_nonlinear_model=summarize(m, lin['c'], v),
                          nonlinear_design=dict(objective=nl['objective'], constraints=nl['constraints'],
                                                phase_separation_degrees=nl['phase_separation_degrees'])))
    return out, cross


def nonlinearity_strength(c, chi):
    m = WaveFEM(Config(chi=chi), 8)
    v = m.evaluate(c, False)
    rows = []
    for s, (u, _, _) in enumerate(v['solutions']):
        V = m.unpack(u)
        q = V[m.edges]@m.N.T
        ratio = chi*abs(q)**2/np.asarray(c)[m.cell][:, None]
        rows.append(dict(state=['on', 'off'][s], max_ratio=float(ratio.max()), mean_ratio=float(ratio.mean()),
                         max_voltage=float(abs(V).max())))
    return rows


def chi_sweep():
    out = []
    for chi in [0.0, 0.05, 0.1, 0.2, 0.3]:
        best, runs = best_of(Config(chi=chi), starts())
        out.append(dict(chi=chi, best=best, failed_starts=[r['start'] for r in runs if not r.get('success')],
                        runs=[{k: v for k, v in r.items() if k != 'c'} for r in runs],
                        strength=None if best is None else nonlinearity_strength(np.array(best['c']), chi)))
    ref = out[0]['best']['c']
    for row in out:
        if row['best'] is not None:
            row['max_design_difference_from_linear'] = float(np.max(abs(np.array(row['best']['c'])-np.array(ref))))
    return out


# ---------------------------------------------------------------- scaled constraints
def scaled_design():
    """Rerun the frozen problem with constraints written g/g_limit - 1 >= 0.

    |R|^2/0.64 - 1 >= 0 and 1 - E/1.6 >= 0. Same feasible set, so the KKT
    point must not move; multipliers rescale by the constraint scale factors.
    """
    m = WaveFEM(Config(), 8); out = []
    scale = np.array([1/.64, 1/.64, 1/1.6, 1/1.6])
    for name, c0 in starts():
        cache = {}
        def ev(c):
            if 'x' not in cache or not np.array_equal(cache['x'], c):
                cache.update(x=c.copy(), v=m.evaluate(c))
            return cache['v']
        try:
            r = minimize(lambda c: ev(c)['objective'], c0, jac=lambda c: ev(c)['gradient'], method='SLSQP', bounds=[(.5, 2.5)]*20,
                         constraints=[dict(type='ineq', fun=lambda c: ev(c)['constraints']*scale, jac=lambda c: ev(c)['constraint_jacobian']*scale[:, None])],
                         options=dict(maxiter=500, ftol=1e-11))
            v = ev(r.x)
            out.append(dict(start=name, success=bool(r.success), message=str(r.message), iterations=int(r.nit), objective=float(v['objective']),
                            scaled_constraints=(v['constraints']*scale).tolist(), c=r.x.tolist()))
        except RuntimeError as e:
            out.append(dict(start=name, success=False, message=str(e)))
    return dict(scale=scale.tolist(), runs=out)


# ---------------------------------------------------------------- Newton failure diagnosis
def newton_from(m, c, state, u0, maxit=60):
    u = u0.copy(); hist = []
    for _ in range(maxit):
        f, J = m.residual_jacobian(u, c, state); r = np.linalg.norm(f, np.inf); hist.append(float(r))
        if r < 2e-11:
            return u, hist, True
        from scipy.sparse.linalg import spsolve
        d = spsolve(J, -f); step = 1.
        for _ in range(30):
            un = u+step*d
            if np.linalg.norm(m.residual_jacobian(un, c, state)[0]) < (1-1e-4*step)*np.linalg.norm(f):
                break
            step *= .5
        else:
            return u, hist, False
        u = un
    return u, hist, False


def newton_failure():
    """Why the nonlinear high-low start fails, and whether a solution exists there."""
    c = np.r_[np.full(6, 2.5), np.full(14, .5)]
    rows = []
    for s in (0, 1):
        lin = WaveFEM(Config(chi=0), 8); u0 = lin.solve(c, s)[0]; V0 = lin.unpack(u0)
        q = V0[lin.edges]@lin.N.T
        direct = dict(state=['on', 'off'][s], linear_max_voltage=float(abs(V0).max()),
                      linear_max_ratio=float((.05*abs(q)**2/c[lin.cell][:, None]).max()))
        m = WaveFEM(Config(), 8)
        try:
            m.solve(c, s); direct['direct_newton'] = 'converged'
        except RuntimeError as e:
            direct['direct_newton'] = str(e)
        # continuation in chi from the linear state
        u = u0.copy(); path = []; ok = True
        for chi in np.linspace(0, .05, 11)[1:]:
            mm = WaveFEM(Config(chi=float(chi)), 8)
            u, hist, conv = newton_from(mm, c, s, u)
            path.append(dict(chi=float(chi), converged=conv, iterations=len(hist)-1, residual=hist[-1]))
            if not conv:
                ok = False; break
        direct['continuation_converged'] = ok; direct['continuation'] = path
        if ok:
            V = m.unpack(u); direct['continuation_max_voltage'] = float(abs(V).max())
            direct['continuation_reflection_magnitude'] = float(abs(V[0]-1))
        rows.append(direct)
    return dict(design='high_low (c=2.5 on cells 1-6, 0.5 on cells 7-20)', states=rows)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output', type=Path, default=ROOT/'assets'/'rubric-studies.json')
    a = p.parse_args()
    t0 = time.perf_counter()
    base = json.loads((ROOT/'assets'/'results.json').read_text(encoding='utf-8'))
    c_opt = np.array(base['nonlinear']['final']['c'])
    c_rand = np.random.default_rng(2026).uniform(.5, 2.5, 20)
    designs = [('initial_uniform', np.ones(20)), ('random_2026', c_rand), ('nonlinear_optimum', c_opt)]
    print('ladder', flush=True)
    ladder = dict(nonuniform_abcd=ladder_nonuniform(designs[1:]), lossless=ladder_lossless(designs))
    print('gradients', flush=True)
    grads = dict(coordinate=[coordinate_check(c, n) for n, c in designs],
                 coordinate_h1e3=[coordinate_check(c, n, 1e-3) for n, c in designs],
                 step_sweep=[step_sweep(c, 11, n) for n, c in designs])
    print('cost', flush=True)
    cost = cost_scaling()
    print('kkt', flush=True)
    kk = kkt_relaxation(c_opt, base['nonlinear']['kkt']['multipliers'])
    print('limit sweep', flush=True)
    sweep, cross = limit_sweep(c_opt)
    print('chi sweep', flush=True)
    chis = chi_sweep()
    print('scaled constraints / newton diagnosis', flush=True)
    scaled = scaled_design(); nfail = newton_failure()
    src = [Path(__file__), ROOT/'code'/'wave_fem.py', ROOT/'code'/'run_design.py', ROOT/'assets'/'results.json']
    data = dict(
        schema_version='1.0',
        run_date_utc=time.strftime('%Y-%m-%d', time.gmtime()),
        status='New supplemental runs on the unchanged solver. results.json is not modified.',
        provenance=dict(python=platform.python_version(), numpy=np.__version__, scipy=scipy.__version__,
                        command='python Project4-Metasurface/code/rubric_studies.py',
                        source_sha256={q.name: hashlib.sha256(q.read_bytes()).hexdigest() for q in src},
                        seconds=None),
        roles=dict(ladder='verification rung', gradients='verification rung', cost='timing, machine dependent',
                   kkt_relaxation='tests reported multipliers', limit_sweep='post hoc sensitivity, not the frozen design',
                   chi_sweep='post hoc sensitivity, not the frozen design',
                   scaled_constraints='check that g/g_limit-1 scaling leaves the frozen optimum unchanged', newton_failure='diagnosis of the frozen failed start'),
        frozen_config=asdict(Config()),
        ladder=ladder, gradients=grads, cost=cost, kkt_relaxation=kk,
        limit_sweep=sweep, with_without=cross, chi_sweep=chis, scaled_constraints=scaled, newton_failure=nfail,
        nonlinearity_strength_at_optimum=nonlinearity_strength(c_opt, .05))
    data['provenance']['seconds'] = time.perf_counter()-t0
    a.output.parent.mkdir(parents=True, exist_ok=True)
    def plain(o):
        if isinstance(o, complex):
            return [o.real, o.imag]
        if isinstance(o, (np.floating, np.integer, np.bool_)):
            return o.item()
        if isinstance(o, np.ndarray):
            return o.tolist()
        raise TypeError(type(o).__name__)
    a.output.write_text(json.dumps(data, separators=(',', ':'), allow_nan=False, default=plain), encoding='utf-8')
    print('WROTE', a.output, f"{data['provenance']['seconds']:.1f}s", flush=True)


if __name__ == '__main__':
    main()

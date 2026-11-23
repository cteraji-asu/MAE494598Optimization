"""Saved PINN surrogates driving a gradient-based optimizer (new run, 23 Nov 2026).

Restricted Project 3 family only: L=0.36, uniform loading c=1, chi=0, one design
variable d (switch-to-short length) in [0.036, 0.306]. This is NOT the
20-variable nonlinear core problem.

Both arms use SciPy SLSQP with the same starts, bounds and constraints:
  objective  q(d) = 1 + cos(phase(R_OFF) - phase(R_ON))   (0 at 180 degrees)
  constraints |R_ON|^2 - 0.64 >= 0,  |R_OFF|^2 - 0.64 >= 0
* surrogate arm: values and design gradients from the saved network (autodiff)
* reference arm: values from the own two-segment P1 FE model (128 elements per
  segment) and gradients from its shape adjoint (restricted_fe_bridge.py)

No network is trained, selected or modified. Each surrogate endpoint is
re-evaluated with FE and with the exact analytic response.
"""
from pathlib import Path
import argparse, hashlib, json, sys, time
import numpy as np
import torch
from scipy.optimize import minimize

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import restricted_fe_bridge as fe  # noqa: E402
import smooth_pinn_study as smooth  # noqa: E402
import two_pinn_study as hard  # noqa: E402

ROOT = HERE.parent
LO, HI, N = .036, .306, 128
STARTS = [.06, .12, .18, .24, .30]


def fe_metrics(d, grad=False):
    if grad:
        r, g = fe.evaluate(d, N, True)
        return fe.metrics(r), np.asarray(g).reshape(3)
    return fe.metrics(fe.evaluate(d, N))


def surrogate_fn(module, model):
    def f(d):
        t = torch.tensor([float(d)], requires_grad=True)
        r = module.predict(model, t, .36-t)[0]
        vals = torch.stack([1+(r[1]*r[0].conj()).real/(abs(r[0])*abs(r[1])),
                            abs(r[0])**2-.64, abs(r[1])**2-.64])
        grads = [torch.autograd.grad(vals[i], t, retain_graph=i < 2)[0].item() for i in range(3)]
        return vals.detach().numpy(), np.array(grads)
    return f


def slsqp(fn, d0):
    cache, path = {}, []

    def ev(x):
        d = float(np.clip(x[0], LO, HI))
        if cache.get('d') != d:
            v, g = fn(d); cache.update(d=d, v=v, g=g)
        return cache['v'], cache['g']
    path.append(float(d0))
    r = minimize(lambda x: ev(x)[0][0], [d0], jac=lambda x: np.array([ev(x)[1][0]]), method='SLSQP',
                 bounds=[(LO, HI)], callback=lambda x: path.append(float(x[0])),
                 constraints=[dict(type='ineq', fun=lambda x: ev(x)[0][1:], jac=lambda x: ev(x)[1][1:, None])],
                 options=dict(maxiter=200, ftol=1e-12))
    d = float(np.clip(r.x[0], LO, HI))
    return dict(start=d0, d=d, success=bool(r.success), message=str(r.message), iterations=int(r.nit),
                at_bound=bool(min(d-LO, HI-d) < 1e-6), path=path)


def check(d):
    m = fe_metrics(d); ex = fe.metrics(fe.exact(d))
    phase = lambda r: float(abs(np.angle(r[1]*np.conj(r[0]), deg=True)))
    return dict(fe_metrics=m.tolist(), fe_feasible=bool(min(m[1:]) >= 0), exact_metrics=ex.tolist(),
                exact_phase_degrees=phase(fe.exact(d)))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output', type=Path, default=ROOT/'assets'/'surrogate-optimizer-loop.json')
    a = p.parse_args()
    t0 = time.perf_counter()
    reference = []
    for d0 in STARTS:
        run = slsqp(lambda d: fe_metrics(d, True), d0); run.update(check(run['d'])); reference.append(run)
    feasible_ref = [r for r in reference if r['success'] and r['fe_feasible']]
    best_ref = min(feasible_ref, key=lambda r: r['fe_metrics'][0])
    models = []
    for module, stem in [(hard, 'two-pinn'), (smooth, 'smooth-pinn')]:
        saved = json.loads((ROOT/'assets'/f'{stem}-results.json').read_text(encoding='utf-8'))
        for run in saved['runs']:
            model = module.Model(run['mode'])
            model.load_state_dict({k: torch.tensor(v) for k, v in run['weights'].items()})
            model.eval(); fn = surrogate_fn(module, model)
            runs = []
            for d0 in STARTS:
                r = slsqp(fn, d0)
                sv, sg = fn(r['d']); fv, fg = fe_metrics(r['d'], True)
                r.update(check(r['d']), surrogate_metrics=sv.tolist(), surrogate_gradient=sg.tolist(), fe_gradient=fg.tolist())
                # gradient agreement along the surrogate's own optimization path
                pg = [(fn(d)[1][0], fe_metrics(d, True)[1][0]) for d in r['path']]
                r['path_objective_gradients'] = [[float(s), float(f)] for s, f in pg]
                r['path_sign_agreement'] = float(np.mean([np.sign(s) == np.sign(f) for s, f in pg]))
                runs.append(r)
            ok = [r for r in runs if r['success'] and min(r['surrogate_metrics'][1:]) >= 0]
            best = min(ok, key=lambda r: r['surrogate_metrics'][0]) if ok else None
            # gradient comparison on a fixed grid of designs
            grid = np.linspace(LO, HI, 55)
            sval = [fn(d) for d in grid]; fval = [fe_metrics(d, True) for d in grid]
            sgrid = np.array([g[0] for _, g in sval]); fgrid = np.array([g[0] for _, g in fval])
            # dense check inside and outside the difficult interval [0.195, 0.222]
            band = {}
            for name, lo_, hi_ in [('inside', .195, .222), ('outside_low', .036, .195), ('outside_high', .222, .306)]:
                dd = np.linspace(lo_, hi_, 121)[1:-1]
                sv_ = [fn(x) for x in dd]; fv_ = [fe_metrics(x, True) for x in dd]
                sq = np.array([v[0] for v, _ in sv_]); fq = np.array([v[0] for v, _ in fv_])
                sg = np.array([g[0] for _, g in sv_]); fg = np.array([g[0] for _, g in fv_])
                band[name] = dict(objective_mae=float(np.mean(abs(sq-fq))), fe_objective_min=float(fq.min()), fe_argmin=float(dd[int(np.argmin(fq))]),
                                  surrogate_objective_min=float(sq.min()), surrogate_argmin=float(dd[int(np.argmin(sq))]),
                                  gradient_relative_L2=float(np.linalg.norm(sg-fg)/np.linalg.norm(fg)), wrong_sign=float(np.mean(np.sign(sg) != np.sign(fg))))
            models.append(dict(study=stem, mode=run['mode'], seed=run['seed'], runs=runs, band=band,
                               continuous=not (stem == 'two-pinn' and run['mode'] != 'monolithic'),
                               grid_d=grid.tolist(), grid_surrogate_objective=[float(v[0]) for v, _ in sval],
                               grid_fe_objective=[float(v[0]) for v, _ in fval],
                               grid_surrogate_gradient=sgrid.tolist(), grid_fe_gradient=fgrid.tolist(),
                               selected=None if best is None else dict(d=best['d'], start=best['start'],
                                    surrogate_objective=best['surrogate_metrics'][0], fe_objective=best['fe_metrics'][0],
                                    fe_feasible=best['fe_feasible'], exact_phase_degrees=best['exact_phase_degrees'],
                                    at_bound=best['at_bound']),
                               grid_gradient_relative_L2=float(np.linalg.norm(sgrid-fgrid)/np.linalg.norm(fgrid)),
                               grid_sign_agreement=float(np.mean(np.sign(sgrid) == np.sign(fgrid)))))
            print(stem, run['mode'], run['seed'], models[-1]['selected'], flush=True)
    src = [Path(__file__), HERE/'restricted_fe_bridge.py', HERE/'smooth_pinn_study.py', HERE/'two_pinn_study.py',
           ROOT/'assets'/'smooth-pinn-results.json', ROOT/'assets'/'two-pinn-results.json']
    out = dict(run_date_utc=time.strftime('%Y-%m-%d', time.gmtime()),
               status='New run. Saved networks only; no training, retraining or model selection.',
               scope='Restricted linear Project 3 family (one variable d). Not the 20-variable nonlinear core.',
               objective='q(d)=1+cos(phase difference); constraints |R_s|^2-0.64>=0', bounds=[LO, HI], starts=STARTS,
               fe_elements_per_segment=N, reference=dict(runs=reference, selected=dict(d=best_ref['d'], objective=best_ref['fe_metrics'][0],
                    exact_phase_degrees=best_ref['exact_phase_degrees'], start=best_ref['start'])),
               models=models, seconds=time.perf_counter()-t0,
               source_sha256={q.name: hashlib.sha256(q.read_bytes()).hexdigest() for q in src})
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(out, separators=(',', ':'), allow_nan=False), encoding='utf-8')
    print('WROTE', a.output, f"{out['seconds']:.1f}s", 'reference d', out['reference']['selected'])


if __name__ == '__main__':
    main()

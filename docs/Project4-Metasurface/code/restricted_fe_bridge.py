"""Post-fit, restricted P3 linear-family FE comparison; no training/core edits."""
import argparse
import hashlib
import json
from pathlib import Path
import time
import numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.linalg import splu

ROOT = Path(__file__).resolve().parents[1]
GAMMA = .03 + 2j*np.pi
ZS = [.02+.04j, .02-4j]


def state(d, state_id, n, derivative=False):
    # n P1 elements on each segment. Duplicate interface, eliminate end short.
    edges = np.array([(i, i+1) for i in range(n)] +
                     [(n+1+i, n+2+i) for i in range(n)])
    h = np.r_[np.full(n, (.36-d)/n), np.full(n, d/n)]
    dh = np.r_[np.full(n, -1/n), np.full(n, 1/n)]
    K = np.array([[1., -1.], [-1., 1.]])
    M = np.array([[2., 1.], [1., 2.]])/6
    local = K[None]/(GAMMA*h[:, None, None]) + GAMMA*h[:, None, None]*M
    rows = np.repeat(edges, 2, axis=1).ravel()
    cols = np.tile(edges, (1, 2)).ravel()
    size = 2*n+2
    rr = np.r_[rows, [0, n, n+1, n, n+1]]
    cc = np.r_[cols, [0, n, n+1, n+1, n]]
    vals = np.r_[local.ravel(), [1, 1/ZS[state_id], 1/ZS[state_id], -1/ZS[state_id], -1/ZS[state_id]]]
    A = coo_matrix((vals, (rr, cc)), shape=(size, size)).tocsc()[:-1, :-1]
    lu = splu(A)
    rhs = np.zeros(size-1, complex); rhs[0] = 2
    u = lu.solve(rhs)
    if not derivative:
        return u[0]-1
    da = dh[:, None, None]*(-K[None]/(GAMMA*h[:, None, None]**2) + GAMMA*M)
    Ad = coo_matrix((da.ravel(), (rows, cols)), shape=(size, size)).tocsc()[:-1, :-1]
    # Complex linear output adjoint, transpose (not Hermitian): dR/dd=-lambda^T A_d u.
    e = np.zeros(size-1, complex); e[0] = 1
    lam = lu.solve(e, trans='T')
    return u[0]-1, -lam @ (Ad @ u)


def exact(d):
    d = np.asarray(d)
    sh, ch = np.sinh(GAMMA*d), np.cosh(GAMMA*d)
    return np.stack([np.exp(-2*GAMMA*(.36-d))*(sh+(z-1)*ch)/(sh+(z+1)*ch) for z in ZS], axis=-1)


def metrics(r):
    q = 1 + (r[..., 1]*r[..., 0].conj()).real/(abs(r[..., 0])*abs(r[..., 1]))
    return np.stack([q, abs(r[..., 0])**2-.64, abs(r[..., 1])**2-.64], axis=-1)


def evaluate(d, n, derivative=False):
    if not derivative:
        return np.array([state(d, s, n) for s in (0, 1)])
    a = [state(d, s, n, True) for s in (0, 1)]
    r, dr = np.array([x[0] for x in a]), np.array([x[1] for x in a])
    mag = abs(r); unit = r/mag
    du = dr/mag-r*(r.conj()*dr).real/mag**3
    grad = np.r_[(du[1]*unit[0].conj()+unit[1]*du[0].conj()).real,
                  2*(r.conj()*dr).real]
    return r, grad


def run():
    start = time.perf_counter()
    points = [.036, .1, .195, .208422, .222, .27, .306]
    refinement = []
    for n in [16, 32, 64, 128, 256]:
        err = max(float(np.max(abs(evaluate(d, n)-exact(d)))) for d in points)
        refinement.append(dict(elements_per_segment=n, max_reflection_error=err))
    rates = np.log2(np.array([x['max_reflection_error'] for x in refinement[:-1]]) /
                     np.array([x['max_reflection_error'] for x in refinement[1:]]))
    probes = []
    for d in points:
        r, grad = evaluate(d, 128, True)
        hs = [1e-4, 1e-5, 1e-6, 1e-7]
        fd = np.array([(metrics(evaluate(d+h, 128))-metrics(evaluate(d-h, 128)))/(2*h) for h in hs])
        err = abs(fd-grad)/np.maximum(abs(grad), 1e-4)
        probes.append(dict(d=d, adjoint=grad.tolist(), steps=hs, central_fd=fd.tolist(),
                           scaled_errors=err.tolist(), passed=bool(np.all(np.min(err, axis=0)<2e-4))))
    ds = np.linspace(.036, .306, 10001)
    n = 128
    rr = np.array([evaluate(d, n) for d in ds])
    ref = exact(ds)
    def pick(r):
        vals = metrics(r); scores = vals[:, 0].copy()
        scores[np.min(vals[:, 1:], axis=1)<0] = np.inf
        i = int(np.argmin(scores))
        return dict(index=i, d=float(ds[i]), metrics=vals[i].tolist(),
                    exact_metrics=metrics(ref[i]).tolist(),
                    phase_degrees=float(abs(np.angle(r[i, 1]*r[i, 0].conj(), deg=True))))
    fe_choice, exact_choice = pick(rr), pick(ref)
    comparisons = []; cohorts = []
    for stem in ['two-pinn', 'smooth-pinn']:
        saved = json.loads((ROOT/'assets'/f'{stem}-results.json').read_text())
        for row in saved['runs']:
            chosen = row['restricted_design']['surrogate']
            if chosen is None:
                comparisons.append(dict(study=stem, mode=row['mode'], seed=row['seed'], surrogate=None)); continue
            d = chosen['d']; r, grad = evaluate(d, n, True)
            comparisons.append(dict(study=stem, mode=row['mode'], seed=row['seed'],
                surrogate=chosen, fe_metrics=metrics(r).tolist(), fe_gradient=grad.tolist(),
                fine_fe_metrics=metrics(evaluate(d, 256)).tolist(),
                fe_phase_degrees=float(abs(np.angle(r[1]*r[0].conj(), deg=True)))))
        plan = json.loads((ROOT/'assets'/f'{stem}-protocol.json').read_text())
        samples=[]
        for row in plan['designs']:
            if row['split']=='final' and row['d']<=.306:
                d=row['d']; r, grad=evaluate(d,n,True)
                samples.append(dict(d=d, metrics=metrics(r).tolist(), adjoint=grad.tolist()))
        cohorts.append(dict(study=stem, samples=samples))
    files = [Path(__file__)] + [ROOT/'assets'/f'{stem}-{suffix}.json' for stem in ['two-pinn','smooth-pinn'] for suffix in ['results','protocol']]
    return dict(passed=bool(min(rates)>1.9 and refinement[-1]['max_reflection_error']<1e-4 and all(p['passed'] for p in probes)),
        scope='Post-fit linear P3 restricted study only: L=.36, c=1, chi=0, moving split d. Not the 20-variable nonlinear optimization.',
        objective='1+Re(Roff*conj(Ron))/(abs(Roff)*abs(Ron))',
        constraints=['abs(Ron)^2-.64>=0','abs(Roff)^2-.64>=0'],
        phase_note='165 degrees is a screening diagnostic, not an optimization constraint.',
        mesh=dict(elements_per_segment=n,total_elements=2*n),
        grid=dict(count=len(ds), spacing=float(ds[1]-ds[0]),bounds=[.036,.306],fe=fe_choice,analytic=exact_choice,
                  max_reflection_error=float(np.max(abs(rr-ref))),fine_fe_at_fe_choice=metrics(evaluate(fe_choice['d'],256)).tolist(),
                  limit='Discrete constrained exhaustive search, not continuous/global or iterative-gradient convergence proof.'),
        refinement=refinement,refinement_rates=rates.tolist(),gradient_checks=probes,
        surrogate_choices=comparisons,gradient_cohorts=cohorts,
        source_sha256={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files},
        seconds=time.perf_counter()-start)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);args=p.parse_args()
    if args.output.exists():p.error('Refusing to overwrite retained evidence')
    out=run();args.output.parent.mkdir(parents=True,exist_ok=True)
    with args.output.open('x',encoding='utf-8') as f:json.dump(out,f,indent=2,allow_nan=False)
    print(json.dumps({k:out[k] for k in ['passed','seconds','grid']}))
    raise SystemExit(0 if out['passed'] else 1)

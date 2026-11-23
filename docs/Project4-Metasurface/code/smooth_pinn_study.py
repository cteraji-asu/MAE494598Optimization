"""Frozen follow-on smooth-blended PINN experiment. Prior hard-routing results retained."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import time
from datetime import datetime, timezone
import numpy as np
import torch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT.parent / 'Project3-Metasurface' / 'code'))
from switched_line import Config, response, wave_reference
CFG = Config()
LO, HI = .03, .357
BAND = (.195, .222)
torch.set_default_dtype(torch.float64)

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def inside(d):
    return (d >= BAND[0]) & (d <= BAND[1])

class Net(torch.nn.Module):
    def __init__(self, width, bounds=(LO, HI)):
        super().__init__()
        self.bounds = bounds
        self.a = torch.nn.Linear(3, width)
        self.b = torch.nn.Linear(width, width)
        self.c = torch.nn.Linear(width, 4)
    def jets(self, x, d, s):
        lo, hi = self.bounds
        h = torch.tanh(self.a(torch.stack((2*x-1, 2*(d-lo)/(hi-lo)-1, 2*s-1), 1)))
        hx = (1-h*h)*(2*self.a.weight[:, 0])
        q = torch.tanh(self.b(h))
        qx = (1-q*q)*(hx @ self.b.weight.T)
        return self.c(q), qx @ self.c.weight.T
    def values(self, x, d, s):
        lo, hi = self.bounds
        return self.c(torch.tanh(self.b(torch.tanh(self.a(torch.stack((2*x-1, 2*(d-lo)/(hi-lo)-1, 2*s-1), 1))))))

class Model(torch.nn.Module):
    def __init__(self, mode):
        super().__init__()
        self.mode = mode
        self.nets = torch.nn.ModuleList([Net(64)] if mode == 'monolithic' else [Net(44), Net(44, BAND)])
    def evaluate(self, x, d, s, jets=False):
        fn = 'jets' if jets else 'values'
        if len(self.nets) == 1:
            return getattr(self.nets[0], fn)(x, d, s)
        # C-infinity gate; d derivatives include both network and gate derivatives.
        gate = (torch.sigmoid((d-BAND[0])/.002)*torch.sigmoid((BAND[1]-d)/.002))[:,None]
        outside = getattr(self.nets[0], fn)(x, d, s)
        narrow = getattr(self.nets[1], fn)(x, d, s)
        if jets:
            # Gate depends on d, not xi. This is the spatial derivative of the blend.
            return tuple((1-gate)*o+gate*n for o,n in zip(outside,narrow))
        return (1-gate)*outside+gate*narrow

def complex_pair(y):
    return torch.complex(y[:,0], y[:,1]), torch.complex(y[:,2], y[:,3])

def loss(model, x, d, s):
    y, dx = model.evaluate(x, d, s, True)
    v, i = complex_pair(y)
    vx, ix = complex_pair(dx)
    v0, i0 = complex_pair(model.evaluate(torch.zeros_like(x), d, s))
    v1, _ = complex_pair(model.evaluate(torch.ones_like(x), d, s))
    z = CFG.z_on*(1-s) + CFG.z_off*s
    return (abs(vx+CFG.gamma*d*i)**2 + abs(ix+CFG.gamma*d*v)**2 + abs(v0+(1+z)*i0-2)**2/4 + abs(v1)**2).mean()

def exact(d, a):
    """Vectorized nonsingular conventional baseline, two states per design."""
    d, a = np.asarray(d)[:,None], np.asarray(a)[:,None]
    z = np.array([CFG.z_on, CFG.z_off])[None,:]
    sh, ch = np.sinh(CFG.gamma*d), np.cosh(CFG.gamma*d)
    return np.exp(-2*CFG.gamma*a)*(sh+(z-1)*ch)/(sh+(z+1)*ch)

def predict(model, d, a):
    d = torch.as_tensor(d).repeat_interleave(2)
    a = torch.as_tensor(a).repeat_interleave(2)
    s = torch.tensor([0.,1.]).repeat(len(d)//2)
    _, i = complex_pair(model.evaluate(torch.zeros_like(d), d, s))
    return ((1-i)*torch.exp(-2*CFG.gamma*a)).reshape(-1,2)

def feasible(r):
    phase = np.abs(np.angle(r[:,1]*r[:,0].conj(), deg=True))
    return (phase >= 165) & (np.min(abs(r),axis=1) >= .8)

def objective(r):
    """Smooth phase-antialignment error, 0 at 180 degrees."""
    return 1 + (r[:,1]*r[:,0].conj()).real/(abs(r[:,0])*abs(r[:,1]))

def freeze(folder):
    folder.mkdir(parents=True, exist_ok=True)
    path = folder/'smooth-pinn-protocol.json'
    if path.exists():
        plan = json.loads(path.read_text())
        if plan['source_sha256'] != digest(Path(__file__)):
            raise RuntimeError('Code changed after freeze. Use a new output directory; do not silently refreeze.')
        return plan
    historical = []
    for p in (ROOT.parent/'Project3-Metasurface/outputs').rglob('frozen-protocol.json'):
        for row in json.loads(p.read_text()).get('designs', []):
            if 'd' in row:
                historical.append(float(row['d']))
    prior = json.loads((ROOT/'assets/two-pinn-protocol.json').read_text())
    historical.extend(float(r['d']) for r in prior['designs'])
    rng = np.random.default_rng(49420261111)
    used = historical.copy()
    rows = []
    for split, n in [('train',256), ('validation',128), ('final',320)]:
        for j in range(n):
            band = j < n//2
            while True:
                d = float(rng.uniform(*(BAND if band else (LO, HI))))
                if not band and BAND[0] <= d <= BAND[1]:
                    continue
                if used and min(abs(d-u) for u in used) < 1e-8:
                    continue
                lmin, lmax = max(.30,d/.85), min(.42,d/.1)
                if lmin < lmax:
                    break
            length = float(rng.uniform(lmin,lmax))
            rows.append(dict(id=f'{split}-{j}', split=split, band=band, d=d, a=length-d))
            used.append(d)
    plan = dict(created_utc=datetime.now(timezone.utc).isoformat(), source_sha256=digest(Path(__file__)),
        status='Follow-on chosen after hard-routing failure; frozen before new fitting or new validation/final reference access', gate_formula='sigmoid((d-.195)/.002)*sigmoid((.222-d)/.002); V/I and spatial derivatives blended before residual; design autodiff includes gate', gate_width=.002, prior_protocol_sha256=digest(ROOT/'assets/two-pinn-protocol.json'), seeds=[0,1,2], steps=4000,
        modes=['monolithic','smooth_specialists'], parameter_counts=[4676,4672],
        bands=[LO, *BAND, HI], batch_geometries=32, points_per_geometry=4, both_states=True,
        optimizer='Adam cosine 0.002 to 0.0002; terminal iterate; no early stopping or tuning',
        selection='No validation selection. All terminal models evaluated; no final-set fitting.',
        sampling='16 band and 16 complement geometries per update; same stream for both arms',
        capacity='Total parameters matched within 0.086%; both specialists evaluated at every point. Affine multiply count 4488 vs 4544 per point, excluding nonlinearities, gates and derivatives; equal updates/points, not identical FLOPs or walltime.',
        physical_thresholds={'phase_degrees':165,'minimum_magnitude':.8},
        gate={'reflection_p95':.03,'voltage_median':.05,'sensitivity':.9,'specificity':.9,'both_classes_required':True},
        gradient='d derivative at fixed total L=.36, final geometries with d<=.306; compare smooth antialignment objective',
        optimization='Restricted 1D L=.36, dense grid 10001 d in [.036,.306], choose minimum phase objective among predicted magnitude>=.8. Diagnostic audit after fitting; never used in training.',
        boundary_audit='Value and derivative continuity at d=.195 and .222; sigmoid blend is smooth. No interface loss and no supervised labels.',
        historical_unique_d=len(set(historical)), minimum_d_separation=1e-8,
        history='P3 cohorts, prior hard-routing final and its failure already inspected; prior experiment geometries excluded. New draws only are final evidence; close-neighbor interpolation, not blocked extrapolation.',
        designs=rows)
    path.write_text(json.dumps(plan,indent=2))
    (folder/'smooth-pinn-freeze-receipt.json').write_text(json.dumps(dict(created_utc=plan['created_utc'], protocol_sha256=digest(path), source_sha256=plan['source_sha256']),indent=2))
    return plan

def train(plan, mode, seed):
    torch.manual_seed(seed)
    model=Model(mode)
    rng=torch.Generator().manual_seed(seed+99100)
    trainrows=[r for r in plan['designs'] if r['split']=='train']
    pools=[torch.tensor([r['d'] for r in trainrows if r['band']==band]) for band in (False,True)]
    opt=torch.optim.Adam(model.parameters(),lr=.002)
    schedule=torch.optim.lr_scheduler.CosineAnnealingLR(opt, plan['steps'], eta_min=.0002)
    history=[]
    start=time.perf_counter()
    for step in range(plan['steps']):
        base=torch.cat([p[torch.randint(len(p),(16,),generator=rng)] for p in pools]).repeat_interleave(4)
        x=torch.rand(len(base),generator=rng).repeat(2)
        d=base.repeat(2)
        s=torch.cat((torch.zeros_like(base),torch.ones_like(base)))
        opt.zero_grad()
        value=loss(model,x,d,s)
        value.backward()
        opt.step(); schedule.step()
        if step%1000==0 or step==plan['steps']-1:
            history.append([step+1,float(value.detach())])
    seconds=time.perf_counter()-start
    print(mode, seed, seconds, history[-1], flush=True)
    return model, dict(mode=mode,seed=seed,training_seconds=seconds,loss_history=history,
        parameter_count=sum(p.numel() for p in model.parameters()), updates=plan['steps'],
        interior_point_state_evaluations=plan['steps']*256, endpoint_point_state_evaluations=plan['steps']*512,
        weights={k:v.detach().tolist() for k,v in model.state_dict().items()})

def evaluate(model, rows):
    d=np.array([r['d'] for r in rows]); a=np.array([r['a'] for r in rows])
    with torch.no_grad():
        pred=predict(model,d,a).numpy()
    ref=exact(d,a)
    errors=abs(pred-ref).max(axis=1)
    truth, guess=feasible(ref),feasible(pred)
    tp=int(sum(truth&guess)); tn=int(sum(~truth&~guess)); fp=int(sum(~truth&guess)); fn=int(sum(truth&~guess))
    fields=[]
    grid=np.linspace(0,1,129)
    for j in range(len(d)):
        for s in (0,1):
            with torch.no_grad():
                v,_=complex_pair(model.evaluate(torch.tensor(grid),torch.full((129,),d[j]),torch.full((129,),float(s))))
            pr=np.exp(-CFG.gamma*a[j])*v.numpy()
            terminal=2/(np.sinh(CFG.gamma*d[j])+(1+[CFG.z_on,CFG.z_off][s])*np.cosh(CFG.gamma*d[j]))
            er=np.exp(-CFG.gamma*a[j])*terminal*np.sinh(CFG.gamma*d[j]*(1-grid))
            xl=grid*a[j]
            el=np.exp(-CFG.gamma*xl)+ref[j,s]*np.exp(CFG.gamma*xl)
            pl=np.exp(-CFG.gamma*xl)+pred[j,s]*np.exp(CFG.gamma*xl)
            err=np.trapezoid(abs(pl-el)**2,grid)*a[j]+np.trapezoid(abs(pr-er)**2,grid)*d[j]
            norm=np.trapezoid(abs(el)**2,grid)*a[j]+np.trapezoid(abs(er)**2,grid)*d[j]
            fields.append(float(np.sqrt(err/norm)))
    sensitivity=tp/(tp+fn) if tp+fn else None
    specificity=tn/(tn+fp) if tn+fp else None
    out=dict(count=len(d),reflection_p95=float(np.quantile(errors,.95)),reflection_max=float(max(errors)),
        voltage_relative_L2_median=float(np.median(fields)),voltage_relative_L2_p95=float(np.quantile(fields,.95)),
        tp=tp,tn=tn,fp=fp,fn=fn,sensitivity=sensitivity,specificity=specificity,
        max_predicted_reflection_magnitude=float(abs(pred).max()),
        per_design=[dict(id=r['id'],reflection_max_error=float(e),truth=bool(t),prediction=bool(p)) for r,e,t,p in zip(rows,errors,truth,guess)])
    out['gate_pass']=bool(out['reflection_p95']<=.03 and out['voltage_relative_L2_median']<=.05 and sensitivity is not None and sensitivity>=.9 and specificity is not None and specificity>=.9)
    return out

def gradient_audit(model, rows):
    ds=np.array([r['d'] for r in rows if r['d']<=.306])
    d=torch.tensor(ds,requires_grad=True)
    r=predict(model,d,.36-d)
    j=1+(r[:,1]*r[:,0].conj()).real/(abs(r[:,0])*abs(r[:,1]))
    grad=torch.autograd.grad(j.sum(),d)[0].detach().numpy()
    h=1e-6
    exact_grad=(objective(exact(ds+h,.36-ds-h))-objective(exact(ds-h,.36-ds+h)))/(2*h)
    # Model finite differences check implementation; reference difference checks usefulness.
    with torch.no_grad():
        plus=predict(model,ds+h,.36-ds-h).numpy(); minus=predict(model,ds-h,.36-ds+h).numpy()
    fd=(objective(plus)-objective(minus))/(2*h)
    return dict(count=len(ds),autodiff_vs_model_fd_max=float(max(abs(grad-fd))),reference_gradient_rmse=float(np.sqrt(np.mean((grad-exact_grad)**2))),reference_gradient_relative_L2=float(np.linalg.norm(grad-exact_grad)/np.linalg.norm(exact_grad)))

def optimize_audit(model):
    ds=np.linspace(.036,.306,10001)
    ref=exact(ds,.36-ds)
    with torch.no_grad():
        pred=predict(model,ds,.36-ds).numpy()
    def pick(r):
        score=objective(r); score[np.min(abs(r),axis=1)<.8]=np.inf
        idx=int(np.argmin(score))
        if not np.isfinite(score[idx]): return None
        return dict(d=float(ds[idx]),objective=float(score[idx]),reference_objective=float(objective(ref[[idx]])[0]),reference_feasible=bool(feasible(ref[[idx]])[0]),reference_min_magnitude=float(min(abs(ref[idx]))),reference_phase_degrees=float(abs(np.angle(ref[idx,1]*ref[idx,0].conj(),deg=True))))
    return dict(grid_count=len(ds),spacing=float(ds[1]-ds[0]),conventional=pick(ref),surrogate=pick(pred),global_optimality='Grid optimum only, not a continuous global certificate')

def timed(fn, repeats=21):
    for _ in range(3): fn()
    samples=[]
    for _ in range(repeats):
        start=time.perf_counter(); fn(); samples.append(time.perf_counter()-start)
    return dict(median_seconds=float(np.median(samples)),minimum_seconds=min(samples),maximum_seconds=max(samples))

def main():
    parser=argparse.ArgumentParser(); parser.add_argument('--output',type=Path,default=ROOT/'assets'); parser.add_argument('--freeze-only',action='store_true')
    args=parser.parse_args(); torch.set_num_threads(1)
    plan=freeze(args.output)
    if args.freeze_only: return
    result_path=args.output/'smooth-pinn-results.json'
    if result_path.exists(): raise RuntimeError('Refusing to overwrite results. Use a fresh output directory for a reproduction.')
    models=[]; runs=[]
    for seed in plan['seeds']:
        for mode in plan['modes']:
            model, record=train(plan,mode,seed); models.append(model); runs.append(record)
    # Seal all terminal weights before any new validation/final references are accessed.
    seal=json.dumps([r['weights'] for r in runs],sort_keys=True).encode()
    (args.output/'smooth-pinn-checkpoint-seal.json').write_text(json.dumps(dict(created_utc=datetime.now(timezone.utc).isoformat(),weights_sha256=hashlib.sha256(seal).hexdigest()),indent=2))
    for model,record in zip(models,runs):
        for split in ('validation','final'):
            rows=[r for r in plan['designs'] if r['split']==split]
            record[split]=evaluate(model,rows)
        final=[r for r in plan['designs'] if r['split']=='final']
        record['gradients']=gradient_audit(model,final)
        record['restricted_design']=optimize_audit(model)
        record['routing_boundaries']=[]
        for boundary in BAND:
            with torch.no_grad():
                rr=predict(model,np.array([boundary-1e-9,boundary+1e-9]),np.array([.36-boundary]*2)).numpy()
            dd=torch.tensor([boundary-1e-8,boundary+1e-8],requires_grad=True)
            rb=predict(model,dd,.36-dd)
            derivatives=[]
            for state in (0,1):
                re=torch.autograd.grad(rb[:,state].real.sum(),dd,retain_graph=True)[0]
                im=torch.autograd.grad(rb[:,state].imag.sum(),dd,retain_graph=True)[0]
                derivatives.append(torch.complex(re,im).detach().numpy())
            derivatives=np.array(derivatives).T
            record['routing_boundaries'].append(dict(d=boundary,reflection_jump=float(max(abs(rr[0]-rr[1]))),max_state_derivative_difference=float(max(abs(derivatives[0]-derivatives[1])))))
        record['inference']={}
        for n in (1,320,10001):
            ds=np.linspace(.036,.306,n); aa=.36-ds
            with torch.no_grad(): record['inference'][str(n)]=timed(lambda:predict(model,ds,aa))
    conventional={}
    for n in (1,320,10001):
        ds=np.linspace(.036,.306,n); aa=.36-ds
        conventional[str(n)]=timed(lambda:exact(ds,aa))
    audit_rows=[r for r in plan['designs'] if r['split']=='final']
    disagreement=max(abs(exact([r['d']],[r['a']])[0,s]-wave_reference(r['a']+r['d'],r['a']/(r['a']+r['d']),s)[0]) for r in audit_rows for s in (0,1))
    result=dict(protocol_sha256=digest(args.output/'smooth-pinn-protocol.json'),source_sha256=digest(Path(__file__)),torch_version=torch.__version__,numpy_version=np.__version__,threads=1,dtype='float64',runs=runs,conventional_timing=conventional,independent_wave_reference_max_error=float(disagreement),limitations=['Synthetic one-frequency P3 analogue; no hardware claim','Smooth specialization plus local rescaling, not an isolated spatial split intervention; follow-on motivated by prior hard-routing results','Same updates and points, approximate total capacity and affine work; not identical total FLOPs, initialization or runtime','Final set is fresh stratified interpolation, not an untouched problem or blocked extrapolation','Restricted 1D design audit is not the >=20-variable FE adjoint optimizer','No full-wave speedup or bonus-credit claim'])
    result_path.write_text(json.dumps(result,indent=2))
    print(json.dumps([{k:r[k] for k in ('mode','seed','training_seconds','gradients','restricted_design')} | {'final':{k:v for k,v in r['final'].items() if k!='per_design'}} for r in runs],indent=2))

if __name__=='__main__': main()

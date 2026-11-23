"""Reproducible scientific verification; all tolerances are declared here."""
import sys, time
from pathlib import Path
from dataclasses import replace
import numpy as np
from wave_fem import WaveFEM, Config
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'Project3-Metasurface'/'code'))
from switched_line import response

def manufactured(m,c,state,details=False):
    cfg=m.cfg;z=cfg.alpha+1j*cfg.beta;zs=(cfg.z_on,cfg.z_off)[state]
    L=cfg.length;a=L*cfg.switch_cell/cfg.cells;D=2+1j
    B=(2-D*(L**3+3*L**2/z+zs*3*(L-a)**2/z))/(L+(1+zs)/z)
    def exact(x,left):return B*(L-x)+D*(L-x)**3+left*zs*(B+3*D*(L-a)**2)/z
    t,w=np.polynomial.legendre.leggauss(8);N=np.column_stack(((1-t)/2,(1+t)/2));w=w*m.h/2
    x=m.x[m.edges]@N.T;left=(np.arange(len(m.edges))<cfg.switch_cell*m.per_cell)[:,None]
    v=exact(x,left);f=-6*D*(L-x)/z+(cfg.alpha+1j*cfg.beta*c[m.cell,None])*v+1j*cfg.beta*cfg.chi*abs(v)**2*v
    local=np.einsum('q,qi,eq->ei',w,N,f);load=np.zeros(m.n+1,complex);np.add.at(load,m.edges.ravel(),local.ravel())
    u,J,hist=m.solve(c,state,load[:-1]);vh=m.unpack(u)[m.edges]@N.T
    error=float(np.sqrt(np.sum(w*abs(vh-v)**2)))
    if details:
        norm=float(np.sqrt(np.sum(w*abs(v)**2)))
        return dict(L2_error=error,exact_L2_norm=norm,relative_L2_error=error/norm,computed_sample=[[float(x.real),float(x.imag)] for x in vh[[0,len(vh)//2,-1],0]],exact_sample=[[float(x.real),float(x.imag)] for x in v[[0,len(v)//2,-1],0]],sample_x=x[[0,len(x)//2,-1],0].tolist(),exact_expected_error=0.)
    return error,hist

def verify():
    checks=[]
    def add(name,value,tolerance,passed=None,**extra):checks.append(dict(name=name,value=value,tolerance=tolerance,passed=bool(value<tolerance) if passed is None else bool(passed),**extra))
    # Independent Project 3 ABCD reference, c=1, chi=0.
    errors=[]
    for p in [1,2,4,8,16]:
        m=WaveFEM(Config(chi=0),p)
        errors.append(max(abs(m.unpack(m.solve(np.ones(20),s)[0])[0]-1-response(.36,.3,s)[0]) for s in (0,1)))
    rates=np.log2(np.array(errors[:-1])/errors[1:])
    add('Uniform linear ABCD and mesh convergence',errors[-1],2e-5,errors[-1]<2e-5 and min(rates)>1.9,errors=errors,rates=rates.tolist(),per_cell=[1,2,4,8,16],comparisons=[dict(state=['on','off'][s],computed=[float(a.real),float(a.imag)],exact=[float(b.real),float(b.imag)],relative_error=float(abs(a-b)/abs(b))) for s in (0,1) for a,b in [(m.unpack(m.solve(np.ones(20),s)[0])[0]-1,response(.36,.3,s)[0])]])
    errs=[]
    for p in [1,2,4,8]:errs.append(manufactured(WaveFEM(Config(),p),np.ones(20),1)[0])
    rates=np.log2(np.array(errs[:-1])/errs[1:])
    add('Manufactured cubic nonlinear solution',errs[-1],1e-4,errs[-1]<1e-4 and min(rates)>1.9,errors=errs,rates=rates.tolist(),per_cell=[1,2,4,8],comparison=manufactured(WaveFEM(Config(),8),np.ones(20),1,True),forcing='f=-V_exact_second/z+y V_exact+i beta chi |V_exact|^2 V_exact; exact cubic on both sides plus switch jump')
    m=WaveFEM(Config(),4);c=1+.2*np.sin(np.arange(20));v=m.evaluate(c)
    defects=[m.power_balance(t[0],s)['defect'] for s,t in enumerate(v['solutions'])]
    add('Global passive power balance',max(abs(np.array(defects))),1e-9,defects=defects,exact_expected_defect=0.,relative_error=None,relative_error_note='Exact expected defect is zero; absolute tolerance applies.')
    add('Newton residual',max(t[2][-1] for t in v['solutions']),2e-10,histories=[t[2] for t in v['solutions']])
    u,J,_=v['solutions'][0];rng=np.random.default_rng(494);d=rng.normal(size=len(u));d/=np.linalg.norm(d)
    h=1e-6;fp=m.residual_jacobian(u+h*d,c,0)[0];fm=m.residual_jacobian(u-h*d,c,0)[0]
    add('Real Newton Jacobian directional difference',float(np.linalg.norm((fp-fm)/(2*h)-J@d)/np.linalg.norm(J@d)),1e-7)
    # Phase-equivariance of the cubic constitutive law and port excitation.
    phi=.73;incident=np.exp(1j*phi);load=np.zeros(m.n,complex);load[0]=2*(incident-1)
    ur,_,_=m.solve(c,0,load);Vr=m.unpack(ur);V=m.unpack(u)
    phase_error=float(np.max(abs(Vr-incident*V)))
    normalized_R=Vr[0]/incident-1
    add('Global source-phase equivariance',phase_error,1e-8,exact_expected_error=0.,relative_error=None,energy_difference=abs(m.energy(ur)[0]-m.energy(u)[0]),normalized_reflection_difference=float(abs(normalized_R-v['R'][0])))
    # Quadratic Newton behavior measured before the residual roundoff floor.
    h=np.array(v['solutions'][1][2]);orders=[]
    for i in range(2,len(h)):
        if h[i]>1e-12:orders.append(float(np.log(h[i]/h[i-1])/np.log(h[i-1]/h[i-2])))
    add('Quadratic Newton convergence',min(orders),1.8,passed=min(orders)>1.8,orders=orders,criterion='pre-roundoff residual orders > 1.8')
    # Zero nonlinearity must reduce to one direct complex linear solve.
    m0=WaveFEM(Config(chi=0),4);u0,_,hist=m0.solve(c,0)
    add('Linear limit Newton invariant',hist[-1],1e-10,iterations=len(hist)-1)
    analytic=np.vstack([v['gradient'],v['constraint_jacobian']]);fd=np.zeros_like(analytic)
    t0=time.perf_counter()
    def metrics(v):return np.r_[v['objective'],v['constraints']]
    for j in range(20):
        d=np.eye(20)[j]*1e-5;fd[:,j]=(metrics(m.evaluate(c+d,False))-metrics(m.evaluate(c-d,False)))/(2e-5)
    fdtime=time.perf_counter()-t0;t0=time.perf_counter();m.evaluate(c);adjtime=time.perf_counter()-t0
    rel=np.linalg.norm(analytic-fd,axis=1)/np.maximum(np.linalg.norm(fd,axis=1),1e-12)
    add('All five implicit-adjoint gradients',float(max(rel)),2e-5,relative_errors=rel.tolist(),metric_names=['objective','amplitude_on','amplitude_off','energy_on','energy_off'],finite_difference_seconds=fdtime,adjoint_seconds=adjtime,finite_difference_forward_solves=80,adjoint_forward_solves=2,adjoint_rhs=10)
    d=rng.normal(size=20);d/=np.linalg.norm(d);hs=[.04,.02,.01,.005,.0025];rem=[];base=metrics(v)
    for h in hs:rem.append(abs(metrics(m.evaluate(c+h*d,False))-base-h*analytic@d).tolist())
    arr=np.array(rem);rates=np.log2(arr[:-1]/arr[1:]);add('Taylor remainder second order',float(np.min(rates)),1.9,passed=np.min(rates)>1.9,steps=hs,remainders=rem,rates=rates.tolist(),criterion='minimum rate > 1.9')
    return dict(passed=all(x['passed'] for x in checks),checks=checks)
if __name__=='__main__':
    import json
    print(json.dumps(verify(),indent=2))

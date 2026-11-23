"""Frozen multistart protocol. Run from any directory; writes assets/results.json."""
from pathlib import Path
from dataclasses import asdict,replace
import json,time,platform,hashlib,sys
import numpy as np
import scipy
from scipy.optimize import minimize,nnls
from wave_fem import WaveFEM,Config
from verify_fem import verify
ROOT=Path(__file__).resolve().parents[1]

def clean(o):
    if isinstance(o,np.ndarray):return o.tolist()
    if isinstance(o,(np.floating,np.integer)):return o.item()
    if isinstance(o,complex):return [o.real,o.imag]
    raise TypeError(type(o).__name__)

def snapshot(m,c,v):
    fields=[]
    for s,(u,J,hist) in enumerate(v['solutions']):
        V=m.unpack(u);zs=(m.cfg.z_on,m.cfg.z_off)[s]
        fields.append(dict(state=['on','off'][s],voltage=np.column_stack((V.real,V.imag)).tolist(),voltage_magnitude=abs(V).tolist(),reflection=clean(v['R'][s]),reflection_magnitude=float(abs(v['R'][s])),phase_degrees=float(np.angle(v['R'][s],deg=True)),energy=v['energy'][s],switch_current=clean((V[m.left]-V[m.right])/zs),power_balance=m.power_balance(u,s),newton_residuals=hist))
    phase=float(abs(np.angle(v['R'][0]/v['R'][1],deg=True)))
    return dict(c=np.asarray(c).tolist(),objective=v['objective'],phase_objective=v['phase_objective'],phase_separation_degrees=phase,amplitude_mismatch=float(abs(abs(v['R'][0])-abs(v['R'][1]))),constraints=v['constraints'].tolist(),feasible=bool(min(v['constraints'])>=-1e-7),fields=fields)

def kkt(c,v):
    g=v['constraints'];rows=[];names=[];slacks=[]
    for i in range(4):
        if g[i]<2e-5:rows.append(v['constraint_jacobian'][i]);names.append(['amplitude_on','amplitude_off','energy_on','energy_off'][i]);slacks.append(g[i])
    for j in range(20):
        if c[j]-.5<2e-5:rows.append(np.eye(20)[j]);names.append('lower_'+str(j));slacks.append(c[j]-.5)
        if 2.5-c[j]<2e-5:rows.append(-np.eye(20)[j]);names.append('upper_'+str(j));slacks.append(2.5-c[j])
    if rows:
        mu,_=nnls(np.array(rows).T,v['gradient'],maxiter=2000);res=v['gradient']-np.array(rows).T@mu
    else:mu=np.array([]);res=v['gradient']
    return dict(convention='L=f-sum(mu*g), g>=0; active slacks < 2e-5; nonnegative least-squares multiplier reconstruction',multipliers=dict(zip(names,mu.tolist())),stationarity_inf=float(max(abs(res))),primal_violation=float(max(0,-min(g),.5-min(c),max(c)-2.5)),complementarity_inf=float(max(abs(mu*np.array(slacks)),default=0)),dual_violation=0.,accepted=bool(max(abs(res))<2e-5 and min(g)>-1e-7 and min(c)>=.5-1e-7 and max(c)<=2.5+1e-7 and max(abs(mu*np.array(slacks)),default=0)<1e-7))

def optimize(chi,starts):
    m=WaveFEM(Config(chi=chi),8);runs=[];best=None
    for name,c0 in starts:
        cache={};history=[];t=time.perf_counter()
        def ev(c):
            if 'x' not in cache or not np.array_equal(cache['x'],c):cache.update(x=c.copy(),v=m.evaluate(c))
            return cache['v']
        def callback(c):
            snap=snapshot(m,c,ev(c));snap['iteration']=len(history);history.append(snap)
        try:
            callback(c0)
            r=minimize(lambda c:ev(c)['objective'],c0,jac=lambda c:ev(c)['gradient'],method='SLSQP',bounds=[(.5,2.5)]*20,constraints=[dict(type='ineq',fun=lambda c:ev(c)['constraints'],jac=lambda c:ev(c)['constraint_jacobian'])],callback=callback,options=dict(maxiter=500,ftol=1e-11))
            v=ev(r.x);snap=snapshot(m,r.x,v);kk=kkt(r.x,v)
            run=dict(start=name,success=bool(r.success),message=str(r.message),iterations=int(r.nit),seconds=time.perf_counter()-t,final=snap,kkt=kk,history=history)
            if r.success and snap['feasible'] and kk['accepted'] and (best is None or snap['objective']<best['final']['objective']):best=run
        except RuntimeError as e:run=dict(start=name,success=False,message=str(e),seconds=time.perf_counter()-t,history=history)
        runs.append(run);print('RUN',chi,name,run['success'],run.get('final',{}).get('objective'),run.get('kkt',{}).get('stationarity_inf'),flush=True)
    if best is None:raise RuntimeError('No feasible converged run')
    selected_history=best['history']
    compact_runs=[]
    for run in runs:
        entry=dict(run)
        entry['history']=[{key:value for key,value in item.items() if key!='fields'} for item in run['history']]
        compact_runs.append(entry)
    return dict(chi=chi,best_start=best['start'],final=best['final'],kkt=best['kkt'],history=selected_history,runs=compact_runs)

def main():
    start=time.perf_counter();rng=np.random.default_rng(494)
    starts=[('uniform',np.ones(20)),('low_high',np.r_[np.full(6,.5),np.full(14,2.5)]),('high_low',np.r_[np.full(6,2.5),np.full(14,.5)]),('random_494_a',rng.uniform(.5,2.5,20)),('random_494_b',rng.uniform(.5,2.5,20))]
    verification=verify();assert verification['passed'],'Verification failed; refusing final claims'
    linear=optimize(0,starts);nonlinear=optimize(.05,starts)
    m=WaveFEM(Config(),8);initial=snapshot(m,np.ones(20),m.evaluate(np.ones(20)))
    cross={}
    for label,design in [('linear_design',linear),('nonlinear_design',nonlinear)]:
        cross[label]={}
        for chi in [0,.05]:
            mm=WaveFEM(Config(chi=chi),8);c=np.array(design['final']['c']);cross[label][str(chi)]=snapshot(mm,c,mm.evaluate(c))
    refinement=[]
    for chi,design in [(0,linear),(.05,nonlinear)]:
        c=np.array(design['final']['c']);a=[]
        for p in [4,8,16,32]:
            mm=WaveFEM(Config(chi=chi),p);vv=mm.evaluate(c);a.append(dict(per_cell=p,objective=vv['objective'],constraints=vv['constraints'].tolist(),phase_separation_degrees=float(abs(np.angle(vv['R'][0]/vv['R'][1],deg=True)))))
        refinement.append(dict(chi=chi,levels=a,all_levels_feasible=bool(min(min(t['constraints']) for t in a)>=-1e-7),finest_objective_change=abs(a[-1]['objective']-a[-2]['objective'])))
    data=dict(schema_version='1.0',title='A split-domain nonlinear wave design study',provenance=dict(date_utc='2026-11-10',python=platform.python_version(),numpy=np.__version__,scipy=scipy.__version__,seed=494,base_commit='be3a2f60f84360b73186364dee0d4e17b8d51770',seconds=time.perf_counter()-start,command='python Project4-Metasurface/code/run_design.py',source_sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in [Path(__file__).parent/n for n in ['wave_fem.py','verify_fem.py','run_design.py']]}),config=asdict(Config()),mesh=dict(per_cell=8,elements=len(m.edges),complex_unknowns=m.n,real_unknowns=2*m.n,x=m.x.tolist(),edges=m.edges.tolist(),cell=m.cell.tolist(),interface_nodes=[m.left,m.right]),formulation=dict(energy_key_note='Internal energy keys denote normalized mean-square voltage, not stored physical capacitive energy.',units='Normalized Z0=1, incident voltage=1, x in reference wavelengths; all values dimensionless',design='20 independently piecewise-constant capacitance multipliers c_j',bounds=[.5,2.5],pde='-(Vprime/z)prime+(alpha+i beta c)V+i beta chi |V|^2 V=0',port='V(0)+I(0)=2',termination='V(L)=0',interface='V_left-V_right=Zs I; I_left=I_right; I=-Vprime/z',weak_form='int(Vprime wprime/z + (alpha+i beta c)Vw + i beta chi |V|^2 Vw)dx + (Vleft-Vright)(wleft-wright)/Zs + V(0)w(0)=2w(0)',objective='|R_on+R_off|^2 + .002 mean((c-1)^2)',constraints=['|R_on|^2-.64 >= 0','|R_off|^2-.64 >= 0','1.6 - integral |V_on|^2 / L >= 0','1.6 - integral |V_off|^2 / L >= 0'],adjoint='J^T lambda=f_u; df/dc=f_c-lambda^T F_c; separate real/imaginary unknowns',nonlinearity='Fundamental-harmonic projection of synthetic cubic capacitive charge; 3/4 factor absorbed in chi. No higher-harmonic propagation, calibrated varactor model, or transient stability claim.'),protocol=dict(optimizer='SLSQP with analytic implicit adjoint',starts=[n for n,c in starts],ftol=1e-11,maxiter=500,final_mesh_per_cell=8,development_findings=['Initial harness placed the first Newton evaluation outside exception capture; the high-low nonlinear failure aborted serialization. Evaluation moved inside capture and all starts rerun. No numerical failure was suppressed.','Generic unittest discover in the SciPy-only environment failed importing the separate PyTorch test. The core scientific suite passed using -p test_wave_fem.py.'],pilot='Three elements/cell, uniform start: energy cap 1.6; chi 0 and .05. No constants were tuned after pilot. Pilot exposed competing basins; five fixed starts used for both final models.',history_note='Accepted SLSQP callback iterates, including initial point; fields solved at each stored iterate. Repeated terminal iterate may occur.'),initial=initial,linear=linear,nonlinear=nonlinear,cross_evaluation=cross,verification=verification,mesh_refinement=refinement,limitations=['Synthetic reduced-order analogue, not a calibrated metasurface or experimental result.','Local minima only; multistart is not a global optimum certificate.','Mean-square-voltage limit and amplitude floor are illustrative engineering requirements. The mean-square-voltage cap limits normalized squared field amplitude; .002 regularization mildly discourages loading far from unity. These choices were frozen after the pilot.','Cubic fundamental-only model excludes harmonics and does not establish dynamic stability.','Nonlinear Newton solve selects branch from linear initialization; no global uniqueness proof.','Agent-produced derivations and verification must be independently checked by the student team before submission.'])
    (ROOT/'assets'/'results.json').write_text(json.dumps(data,default=clean,separators=(',',':')),encoding='utf-8');print('WROTE results.json',flush=True)
if __name__=='__main__':main()

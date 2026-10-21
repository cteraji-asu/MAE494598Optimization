"""Problem-specific residual transport diagnostic. No fitting or test selection."""
import cmath
import hashlib
import json
from pathlib import Path
import numpy as np
import torch
from switched_line import Config,wave_reference,phase_metrics,write_csv
from switched_surrogate import FieldNet,complex_channels

ROOT=Path(__file__).resolve().parents[1]
CFG=Config()

def gauss(order):
    t,w=np.polynomial.legendre.leggauss(order)
    return (t+1)/2,w/2

def terms(d,a,state,xi,weights,v,i,vx,ix,v0,i0,v1):
    """NumPy complex algebra; callers supply fields/derivatives independently."""
    g=CFG.gamma*d;z=CFG.impedance(state)
    c,s=np.cosh(g),np.sinh(g);den=(1+z)*c+s;up=np.exp(-2*CFG.gamma*a)
    fv=vx+g*i;fi=ix+g*v
    kernel_c=np.cosh(g*(1-xi));kernel_s=np.sinh(g*(1-xi))
    q=np.sum(weights*(kernel_c*fv-kernel_s*fi))
    b0=v0+(1+z)*i0-2;b1=v1
    port=-up*c*b0/den;short=up*b1/den;interior=-up*q/den
    eta2=float(np.sum(weights*(abs(fv)**2+abs(fi)**2))+abs(b0)**2/4+abs(b1)**2)
    kernel_norm2=float(np.sum(weights*(abs(kernel_c)**2+abs(kernel_s)**2)))
    gain=abs(up)/abs(den)*np.sqrt(4*abs(c)**2+1+kernel_norm2)
    B=np.array([[1,1+z],[c,-s]],complex)
    Bw=np.array([[.5,.5*(1+z)],[c,-s]],complex)
    return dict(port=port,short=short,interior=interior,total=port+short+interior,b0=b0,b1=b1,q=q,
      denominator=den,inverse_abs_D=1/abs(den),continuous_physics_eta=np.sqrt(eta2),absolute_error_gain=float(gain),
      error_bound=float(gain*np.sqrt(eta2)),boundary_matrix_cond2=float(np.linalg.cond(B)),
      loss_scaled_boundary_matrix_cond2=float(np.linalg.cond(Bw)))

def polynomial_case(d,a,state,order=128,kind='arbitrary'):
    x,w=gauss(order)
    if kind=='arbitrary':
        av=np.array([.7+.2j,-.3+.9j,.4-.2j,.1+.3j])
        ai=np.array([-.1+.5j,.6-.4j,-.2+.1j,.3+.2j])
    else:
        delta=.001*(.7-.4j);g=CFG.gamma*d;z=CFG.impedance(state)
        if kind in ('port','short'):
            B=np.array([[1,1+z],[np.cosh(g),-np.sinh(g)]],complex)
            e0=np.linalg.solve(B,[delta,0] if kind=='port' else [0,delta])
            c,s=np.cosh(g*x),np.sinh(g*x)
            ev=c*e0[0]-s*e0[1];ei=-s*e0[0]+c*e0[1]
            evx=-g*ei;eix=-g*ev
            e1v=np.cosh(g)*e0[0]-np.sinh(g)*e0[1]
        elif kind=='interior':
            ev=-(1+z)*delta*(1-x);ei=np.full_like(x,delta,dtype=complex)
            evx=np.full_like(x,(1+z)*delta,dtype=complex);eix=np.zeros_like(x,dtype=complex)
            e0=np.array([-(1+z)*delta,delta]);e1v=0j
        else:raise ValueError(kind)
        terminal=2/(np.sinh(g)+(1+z)*np.cosh(g))
        ve=terminal*np.sinh(g*(1-x));ie=terminal*np.cosh(g*(1-x))
        v0=terminal*np.sinh(g)+e0[0];i0=terminal*np.cosh(g)+e0[1]
        result=terms(d,a,state,x,w,ve+ev,ie+ei,-g*ie+evx,-g*ve+eix,v0,i0,e1v)
        direct=-np.exp(-2*CFG.gamma*a)*e0[1]
        return result,direct
    v=np.polynomial.polynomial.polyval(x,av);i=np.polynomial.polynomial.polyval(x,ai)
    vx=np.polynomial.polynomial.polyval(x,np.polynomial.polynomial.polyder(av))
    ix=np.polynomial.polynomial.polyval(x,np.polynomial.polynomial.polyder(ai))
    result=terms(d,a,state,x,w,v,i,vx,ix,av[0],ai[0],sum(av))
    predicted=np.exp(-2*CFG.gamma*a)*(1-ai[0])
    exact=wave_reference(a+d,a/(a+d),state,CFG)[0]
    return result,predicted-exact

def model_case(model,d,a,state,order):
    x,w=gauss(order)
    with torch.no_grad():
        value,dx=model.jets(torch.tensor(x),torch.full((len(x),),d),torch.full((len(x),),float(state)))
        v,i=[a.numpy() for a in complex_channels(value)];vx,ix=[a.numpy() for a in complex_channels(dx)]
        endpoints=model.values(torch.tensor([0.,1.]),torch.full((2,),d),torch.full((2,),float(state)))
        vv,ii=[a.numpy() for a in complex_channels(endpoints)]
    return terms(d,a,state,x,w,v,i,vx,ix,vv[0],ii[0],vv[1]),np.exp(-2*CFG.gamma*a)*(1-ii[0])

def load_checkpoint(path):
    payload=json.loads(path.read_text());model=FieldNet(payload['width'])
    model.load_state_dict({k:torch.tensor(v) for k,v in payload['weights'].items()})
    return model

def serial(obj):
    if isinstance(obj,complex):return dict(real=obj.real,imag=obj.imag)
    if isinstance(obj,np.generic):return obj.item()
    if isinstance(obj,dict):return {k:serial(v) for k,v in obj.items()}
    if isinstance(obj,list):return [serial(v) for v in obj]
    return obj

def check_known_fields():
    rows=[]
    for d in (.1,.208395,.25,.30):
        for state in (0,1):
            for kind in ('arbitrary','port','short','interior'):
                values=[]
                for order in (32,64,128):
                    result,direct=polynomial_case(d,.36-d,state,order,kind)
                    values.append(result['total'])
                    error=abs(result['total']-direct)
                    assert error<1e-11,(d,state,kind,order,error)
                    assert abs(direct)<=result['error_bound']+1e-11
                rows.append(dict(d=d,state=state,kind=kind,maximum_identity_error=max(abs(v-direct) for v in values),quadrature_64_to_128=abs(values[-1]-values[-2]),inverse_abs_D=result['inverse_abs_D']))
    return rows

if __name__=='__main__':
    torch.set_num_threads(1)
    rows=check_known_fields()
    dest=ROOT/'outputs/residual-error-budget';dest.mkdir(exist_ok=True)
    (dest/'known-field-verification.json').write_text(json.dumps(dict(status='Implementation validation only; frozen-checkpoint attribution not yet run',cases=rows,maximum_identity_error=max(r['maximum_identity_error'] for r in rows)),indent=2))
    print(json.dumps(dict(known_field_cases=len(rows),maximum_identity_error=max(r['maximum_identity_error'] for r in rows)),indent=2))

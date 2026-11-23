"""Post-fit derivative and routing checks; never changes fitted weights or selection."""
import json
from pathlib import Path
import argparse
import numpy as np
import torch
import two_pinn_study as s

def audit(folder):
    result=json.loads((folder/'two-pinn-results.json').read_text())
    plan=json.loads((folder/'two-pinn-protocol.json').read_text())
    ds=np.array([r['d'] for r in plan['designs'] if r['split']=='final' and r['d']<=.306])
    def fd(h):
        return (s.objective(s.exact(ds+h,.36-ds-h))-s.objective(s.exact(ds-h,.36-ds+h)))/(2*h)
    coarse,fine=fd(1e-6),fd(5e-7)
    rows=[]
    for run in result['runs']:
        model=s.Model(run['mode'])
        model.load_state_dict({k:torch.tensor(v) for k,v in run['weights'].items()})
        bounds=[]
        for boundary in s.BAND:
            dd=torch.tensor([boundary-1e-8,boundary+1e-8],requires_grad=True)
            r=s.predict(model,dd,.36-dd)
            derivatives=[]
            for state in (0,1):
                re=torch.autograd.grad(r[:,state].real.sum(),dd,retain_graph=True)[0]
                im=torch.autograd.grad(r[:,state].imag.sum(),dd,retain_graph=True)[0]
                derivatives.append(torch.complex(re,im).detach().numpy())
            derivatives=np.array(derivatives).T
            bounds.append(dict(d=boundary,left_derivative_real=derivatives[0].real.tolist(),left_derivative_imag=derivatives[0].imag.tolist(),right_derivative_real=derivatives[1].real.tolist(),right_derivative_imag=derivatives[1].imag.tolist(),max_state_derivative_jump=float(max(abs(derivatives[0]-derivatives[1])))))
        rows.append(dict(mode=run['mode'],seed=run['seed'],boundaries=bounds))
    output=dict(results_sha256=s.digest(folder/'two-pinn-results.json'),reference_gradient_fd_halving_max_change=float(max(abs(coarse-fine))),reference_gradient_fd_halving_relative_L2=float(np.linalg.norm(coarse-fine)/np.linalg.norm(fine)),runs=rows,note='Derivative limits evaluated 1e-8 to either side. Hard routing has no classical derivative at a discontinuous interface. This audit does not repair the model.')
    (folder/'two-pinn-derivative-audit.json').write_text(json.dumps(output,indent=2))
    print(json.dumps(output,indent=2))

if __name__=='__main__':
    parser=argparse.ArgumentParser(); parser.add_argument('--output',type=Path,default=s.ROOT/'assets'); audit(parser.parse_args().output)

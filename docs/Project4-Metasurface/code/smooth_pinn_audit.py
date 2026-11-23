"""Post-fit finite-difference convergence audit; no training or selection."""
import argparse
import json
from pathlib import Path
import numpy as np
import torch
import smooth_pinn_study as s

def audit(folder):
    result=json.loads((folder/'smooth-pinn-results.json').read_text())
    plan=json.loads((folder/'smooth-pinn-protocol.json').read_text())
    ds=np.array([r['d'] for r in plan['designs'] if r['split']=='final' and r['d']<=.306])
    rows=[]
    reference=[]
    for h in (1e-6,5e-7,1e-7):
        reference.append((s.objective(s.exact(ds+h,.36-ds-h))-s.objective(s.exact(ds-h,.36-ds+h)))/(2*h))
    for run in result['runs']:
        model=s.Model(run['mode'])
        model.load_state_dict({k:torch.tensor(v) for k,v in run['weights'].items()})
        dd=torch.tensor(ds,requires_grad=True)
        r=s.predict(model,dd,.36-dd)
        j=1+(r[:,1]*r[:,0].conj()).real/(abs(r[:,0])*abs(r[:,1]))
        ad=torch.autograd.grad(j.sum(),dd)[0].detach().numpy()
        checks=[]
        for h in (1e-6,5e-7,1e-7):
            with torch.no_grad():
                plus=s.predict(model,ds+h,.36-ds-h).numpy()
                minus=s.predict(model,ds-h,.36-ds+h).numpy()
            fd=(s.objective(plus)-s.objective(minus))/(2*h)
            checks.append(dict(h=h,autodiff_vs_fd_max=float(max(abs(ad-fd))),autodiff_vs_fd_relative_L2=float(np.linalg.norm(ad-fd)/np.linalg.norm(ad))))
        rows.append(dict(mode=run['mode'],seed=run['seed'],checks=checks))
    out=dict(results_sha256=s.digest(folder/'smooth-pinn-results.json'),reference_fd_1e6_vs_1e7_relative_L2=float(np.linalg.norm(reference[0]-reference[-1])/np.linalg.norm(reference[-1])),runs=rows,note='Post-fit verification of numerical derivatives, not a new training or model-selection decision. All original h=1e-6 results remain unchanged.')
    (folder/'smooth-pinn-gradient-audit.json').write_text(json.dumps(out,indent=2))
    print(json.dumps(out,indent=2))

if __name__=='__main__':
    p=argparse.ArgumentParser(); p.add_argument('--output',type=Path,default=s.ROOT/'assets'); audit(p.parse_args().output)

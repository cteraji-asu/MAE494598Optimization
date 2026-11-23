"""Post-fit export of saved smooth PINN gradients; no training or file overwrite."""
import argparse, json, hashlib
from pathlib import Path
import numpy as np
import torch
import smooth_pinn_study as s
p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args()
if a.output.exists():raise SystemExit('Refusing overwrite')
folder=s.ROOT/'assets'
plan=json.loads((folder/'smooth-pinn-protocol.json').read_text())
results=json.loads((folder/'smooth-pinn-results.json').read_text())
ds=np.array([r['d'] for r in plan['designs'] if r['split']=='final' and .036<=r['d']<=.306])
runs=[]
for run in results['runs']:
 model=s.Model(run['mode']);model.load_state_dict({k:torch.tensor(v) for k,v in run['weights'].items()})
 d=torch.tensor(ds,requires_grad=True);r=s.predict(model,d,.36-d)
 q=1+(r[:,1]*r[:,0].conj()).real/(abs(r[:,0])*abs(r[:,1]))
 grad=torch.autograd.grad(q.sum(),d)[0].detach().numpy()
 runs.append(dict(mode=run['mode'],seed=run['seed'],gradients=grad.tolist(),grid_search=run['restricted_design']))
out=dict(d=ds.tolist(),runs=runs,source_sha256={str(f.name):s.digest(f) for f in [Path(__file__),folder/'smooth-pinn-results.json',folder/'smooth-pinn-protocol.json',Path(s.__file__)]},note='Saved trained models, in-box subset of prior final cohort, post-fit comparison only; no training or model selection.')
a.output.parent.mkdir(parents=True,exist_ok=True)
with a.output.open('x') as f:json.dump(out,f,indent=2,allow_nan=False)
print(json.dumps(dict(models=len(runs),points=len(ds),output=str(a.output))))

"""Join actual saved-model autodiff with same-design own-FE adjoints."""
import argparse,json,hashlib
from pathlib import Path
import numpy as np
p=argparse.ArgumentParser();p.add_argument('--model',type=Path,required=True);p.add_argument('--fe',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
if a.output.exists():raise SystemExit('Refusing overwrite')
m=json.loads(a.model.read_text());f=json.loads(a.fe.read_text());assert f['passed']
samples=next(x['samples'] for x in f['gradient_cohorts'] if x['study']=='smooth-pinn')
lookup={x['d']:x['adjoint'][0] for x in samples}
g=np.array([lookup[d] for d in m['d']]);assert len(g)==299 and np.all(np.isfinite(g))
rows=[]
for r in m['runs']:
 v=np.array(r['gradients']);assert v.shape==g.shape
 rows.append(dict(mode=r['mode'],seed=r['seed'],count=len(g),fe_gradient_relative_L2=float(np.linalg.norm(v-g)/np.linalg.norm(g)),fe_gradient_rmse=float(np.sqrt(np.mean((v-g)**2))),selected_d=r['grid_search']['surrogate']['d']))
out=dict(comparison_completed=True,fe_qualification_passed=f['passed'],runs=rows,fe_grid_choice=f['grid']['fe'],hashes={str(x.name):hashlib.sha256(x.read_bytes()).hexdigest() for x in [a.model,a.fe,Path(__file__)]},limits='Post-fit restricted linear-family comparison; bad surrogate physical gradients remain failures. No training, continuous optimum,20-variable surrogate or bonus grade claimed.')
with a.output.open('x') as fp:json.dump(out,fp,indent=2,allow_nan=False)
print(json.dumps(out,indent=2))

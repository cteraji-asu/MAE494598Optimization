"""Read-only independent saved-weight/reference checks. Never trains a model."""
from pathlib import Path
import argparse,csv,json
import numpy as np
from switched_line import Config,wave_reference
from verify_switched_results import forward
ROOT=Path(__file__).resolve().parents[1];CFG=Config()
def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path);args=parser.parse_args()
    files=[]
    for base in ('switched-surrogate','neural-coverage-control/reallocated','representability-control/seed-0','optimizer-continuation-control','hard-boundary-control'):
        for p in (ROOT/'outputs'/base).rglob('*_weights.json'):
            q=p.with_name(p.name.replace('_weights.json','_states.csv'))
            if q.exists():files.append((p,q))
    for p in (ROOT/'outputs/gap-objective-diagnosis').glob('gap-*/*/weights.json'):
        if (p.parent/'states.csv').exists():files.append((p,p.parent/'states.csv'))
    checked=0;maximum=0.;field_max=0.;field_cases=0;models=[]
    for weight,states in sorted(files):
        payload=json.loads(weight.read_text());rows=list(csv.DictReader(states.open(newline='')))
        d=np.array([float(r['d']) for r in rows]);a=np.array([float(r['a']) for r in rows]);s=np.array([int(r['state']) for r in rows])
        values=forward(payload,np.zeros(len(rows)),d,s);pred=np.exp(-2*CFG.gamma*a)*(1-values[:,2]-1j*values[:,3]);local=0.
        for n,r in enumerate(rows):
            reference=wave_reference(a[n]+d[n],a[n]/(a[n]+d[n]),int(s[n]))[0]
            recorded=complex(float(r['predicted_real']),float(r['predicted_imag']))
            errors=(abs(pred[n]-recorded),abs(reference-complex(float(r['reference_real']),float(r['reference_imag']))),abs(abs(pred[n]-reference)-float(r['complex_R_error'])))
            local=max(local,*errors);checked+=1
        maximum=max(maximum,local)
        if 'joint_right_relative_L2' in rows[0]:
            # Independent physical wave solution normalized to the right segment.
            for start in range(0,len(rows),16):
                batch=rows[start:start+16];dd=np.array([float(r['d']) for r in batch]);aa=np.array([float(r['a']) for r in batch]);ss=np.array([int(r['state']) for r in batch]);x=np.tile((np.arange(128)+.5)/128,len(batch))
                q=forward(payload,x,np.repeat(dd,128),np.repeat(ss,128));v=(q[:,0]+1j*q[:,1]).reshape(-1,128);i=(q[:,2]+1j*q[:,3]).reshape(-1,128)
                waves=[wave_reference(a+d,a/(a+d),int(s)) for a,d,s in zip(aa,dd,ss)];A=np.array([w[1] for w in waves]);B=np.array([w[2] for w in waves]);phase=CFG.gamma*dd[:,None]*(np.arange(128)+.5)/128
                f=A[:,None]*np.exp(-phase);b=B[:,None]*np.exp(phase);up=np.exp(CFG.gamma*aa[:,None]);ev=(f+b)*up;ei=(f-b)*up
                value=np.sqrt(((abs(v-ev)**2+abs(i-ei)**2).sum(1))/((abs(ev)**2+abs(ei)**2).sum(1)))
                field_max=max(field_max,float(max(abs(value-np.array([float(r['joint_right_relative_L2']) for r in batch])))));field_cases+=len(batch)
        models.append(dict(weights=weight.relative_to(ROOT).as_posix(),states_checked=len(rows),maximum_R_disagreement=local))
    assert files and maximum<1e-10 and field_max<1e-10,(maximum,field_max)
    result=dict(status='pass',models=models,state_cases=checked,maximum_independent_R_or_error_disagreement=maximum,new_joint_field_cases=field_cases,maximum_independent_joint_field_disagreement=field_max,training=False)
    if args.output:
        args.output.parent.mkdir(exist_ok=True,parents=True);args.output.write_text(json.dumps(result,indent=2))
    print(json.dumps(result,indent=2))
if __name__=='__main__':main()

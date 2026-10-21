"""Evaluate the six sealed hard/soft checkpoints, independently checking saved arrays."""
import hashlib,json,statistics,time
import numpy as np
import torch
from hard_boundary_control import ROOT,OUT,CFG,load,port_reflections,sha
from switched_surrogate import evaluate,classification
from switched_line import wave_reference,write_csv
from representability_control import dataset,validation
from optimizer_control import summary
from summarize_switched_surrogate import analytic_factorized
from residual_error_budget import model_case

def numpy_raw(weights,xi,d,state):
    x=np.stack((2*xi-1,2*(d-.03)/(.357-.03)-1,2*state-1),1)
    for layer in ('first','second'):
        x=np.tanh(x@np.array(weights[layer+'.weight']).T+weights[layer+'.bias'])
    return x@np.array(weights['last.weight']).T+weights['last.bias']

def numpy_values(weights,xi,d,state,arm):
    y=numpy_raw(weights,xi,d,state)
    if arm=='hard':
        y0=numpy_raw(weights,np.zeros_like(xi),d,state);y1=numpy_raw(weights,np.ones_like(xi),d,state)
        v0=y0[:,0]+1j*y0[:,1];i0=y0[:,2]+1j*y0[:,3]
        v=y[:,0]+1j*y[:,1];v1=y1[:,0]+1j*y1[:,1]
        z=np.where(state==0,CFG.z_on,CFG.z_off)
        v=v-xi*v1-(1-xi)*(v0+(1+z)*i0-2)
        y[:,0]=v.real;y[:,1]=v.imag
    return y

def independent_check(model,payload,arm,plan,states):
    designs={r['id']:r for r in plan['designs']};field_max=derivative_max=reference_max=reflection_max=0.
    # Every saved state reflection checked with an independent wave-system reference.
    for row in states:
        r=designs[row['id']];s=row['state'];d=np.array([r['d']]);xx=np.array([0.]);st=np.array([float(s)])
        y=numpy_values(payload['weights'],xx,d,st,arm)[0]
        pred=np.exp(-2*CFG.gamma*r['a'])*(1-y[2]-1j*y[3])
        reflection_max=max(reflection_max,abs(pred-complex(row['predicted_real'],row['predicted_imag'])))
        exact=wave_reference(r['length'],r['switch_fraction'],s)[0]
        reference_max=max(reference_max,abs(exact-complex(row['reference_real'],row['reference_imag'])))
    # Fixed untrained probe grid; finite differences independently check spatial derivatives.
    d=np.repeat(np.array([.073,.208395,.25,.341]),2*19);st=np.tile(np.repeat([0.,1.],19),4)
    xx=np.tile(np.linspace(.03,.97,19),8);h=1e-6
    y=numpy_values(payload['weights'],xx,d,st,arm)
    fd=(numpy_values(payload['weights'],xx+h,d,st,arm)-numpy_values(payload['weights'],xx-h,d,st,arm))/(2*h)
    with torch.no_grad():value,derivative=model.jets(torch.tensor(xx),torch.tensor(d),torch.tensor(st))
    field_max=float(np.max(abs(y-value.numpy())));derivative_max=float(np.max(abs(fd-derivative.numpy())))
    assert reflection_max<1e-11 and reference_max<1e-11 and field_max<1e-11 and derivative_max<1e-7
    return dict(state_reflections_checked=len(states),field_vectors_checked=len(xx),maximum_numpy_reflection_disagreement=reflection_max,maximum_wave_reference_disagreement=reference_max,maximum_numpy_field_disagreement=field_max,maximum_finite_difference_derivative_disagreement=derivative_max)

def timings(model,designs):
    result={}
    for kind,items,reps in [('single',designs[:1],100),('batch',designs,5)]:
        for name,fn in [('neural',lambda:port_reflections(model,items)),('factorized',lambda:analytic_factorized(items))]:
            fn();samples=[]
            for _ in range(7):
                start=time.perf_counter()
                for j in range(reps):fn()
                samples.append((time.perf_counter()-start)/(reps*len(items)))
            result[name+'_'+kind+'_seconds_per_two_state_query']=statistics.median(samples)
        result[kind+'_positive_break_even_exists']=result['factorized_'+kind+'_seconds_per_two_state_query']>result['neural_'+kind+'_seconds_per_two_state_query']
    return result

def main():
    torch.set_num_threads(1);plan=json.loads((OUT/'frozen-protocol.json').read_text());seal=json.loads((OUT/'selection-seal.json').read_text())
    assert seal['protocol_sha256']==sha(OUT/'frozen-protocol.json')
    for rec in seal['selected']:assert sha(OUT/rec['path'])==rec['sha256']
    if (OUT/'results.json').exists():raise RuntimeError('Completed evaluation retained, no automatic overwrite.')
    val=[r for r in plan['designs'] if r['split']=='validation'];final=[r for r in plan['designs'] if r['split'].startswith('test')]
    valdata=dataset(val,17);records=[]
    for seed in (0,1,2):
        for arm in ('soft','hard'):
            model,payload=load(arm,seed);folder=OUT/arm;validated=validation(model,val,valdata)
            rates=validated['clear_decisions'];both=rates['actual_feasible']>0 and rates['actual_infeasible']>0
            validated['both_clear_classes_present']=both
            validated['numerical_success']=bool(both and validated['blocked_R_p95']<=.03 and validated['blocked_median_field_relative_L2']<=.05 and rates['sensitivity']>=.9 and rates['specificity']>=.9)
            states,pairs=evaluate(folder,plan,model,payload)
            metrics=summary(folder,pairs,states,validated)
            # Keep a distinct summary for each seed; optimizer helper uses a generic filename.
            (folder/f'pinn_seed-{seed}_summary.json').write_text(json.dumps(metrics,indent=2))
            verify=independent_check(model,payload,arm,plan,states)
            budget=[]
            for design in final:
                for state in (0,1):
                    r,pred=model_case(model,design['d'],design['a'],state,64)
                    exact=wave_reference(design['length'],design['switch_fraction'],state)[0]
                    assert abs(r['total']-(pred-exact))<1e-9
                    budget.append(dict(id=design['id'],split=design['split'],state=state,d=design['d'],error_gain=r['absolute_error_gain'],reflection_error=abs(pred-exact),boundary_abs=abs(r['port']+r['short']),interior_abs=abs(r['interior']),identity_disagreement=abs(r['total']-(pred-exact))))
            write_csv(folder/f'pinn_seed-{seed}_error-budget.csv',budget)
            timing=timings(model,final)
            record=dict(arm=arm,seed=seed,training_seconds=payload['training_seconds'],reference_generation_seconds=payload['reference_generation_seconds'],validation_seconds=payload['validation_seconds'],selected_step=payload['selected_step'],gradient_evaluations=payload['gradient_evaluations'],independent_verification=verify,timing=timing,**metrics)
            records.append(record);print(json.dumps(dict(arm=arm,seed=seed,validation_pass=validated['numerical_success'],blocked=metrics['regions'][-1])),flush=True)
    (OUT/'results.json').write_text(json.dumps(dict(protocol_sha256=sha(OUT/'frozen-protocol.json'),selection_seal_sha256=sha(OUT/'selection-seal.json'),evaluation_source_sha256=sha(__import__('pathlib').Path(__file__)),models=records,interpretation='All six predetermined fits reported. Hard enforcement changes the trial-function representation. Equal gradient-call budget is not equal runtime. No hardware evidence.'),indent=2))
if __name__=='__main__':main()

"""Bounded direct supervised representability diagnostic, not a PINN remedy.

Covered 256-geometry family, exact fixed spatial labels, same architecture.
Select L-BFGS continuation only on a new covered validation set. The fresh
holdout and all numerical criteria are frozen before fitting. Existing test
sets are already diagnostic, not pristine. No architecture or budget search.
"""
import copy
import hashlib
import json
from pathlib import Path
import random
import time
import numpy as np
import torch
from switched_line import Config,phase_metrics,write_csv
from switched_surrogate import evaluate,load,reference_right
from summarize_switched_surrogate import classification,read

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'outputs/representability-control'
PRIMARY=ROOT/'outputs/switched-surrogate'
CFG=Config()


def freeze():
    OUT.mkdir(parents=True,exist_ok=True)
    path=OUT/'frozen-protocol.json'
    if path.exists():return json.loads(path.read_text())
    old=json.loads((ROOT/'outputs/neural-coverage-control/frozen-control.json').read_text())
    plan=copy.deepcopy(old['arms']['reallocated'])
    train=[r for r in plan['designs'] if r['split']=='train']
    prior=json.loads((PRIMARY/'frozen-protocol.json').read_text())['designs']
    prior+=old['arms']['original']['designs']
    used=[r['d'] for r in prior]+[r['d'] for r in train]
    rng=random.Random(49420261022)
    dmin,dmax=min(r['d'] for r in train),max(r['d'] for r in train)
    rows=[]
    for split,number,blocked in (('validation',80,False),('validation',80,True),
                                 ('test_offgrid',256,False),('test_blocked',256,True)):
        made=0
        while made<number:
            d=rng.uniform(*((.195,.222) if blocked else (dmin,dmax)))
            if not blocked and .195<=d<=.222:continue
            if min(abs(d-v) for v in used)<2e-5:continue
            lo,hi=max(.3,d/.85),min(.42,d/.1)
            if lo>=hi:continue
            length=rng.uniform(lo,hi)
            rows.append(dict(id=f'capacity-{split}-{int(blocked)}-{made:04d}',split=split,d=d,
                             length=length,a=length-d,switch_fraction=1-d/length))
            used.append(d);made+=1
    plan['designs']=train+rows
    plan['status']='Supervised representability diagnostic after primary and coverage tests'
    plan['capacity_control']=dict(
        architecture_unchanged='3-64-64-4 tanh, same normalization and physical model',
        initialization='Existing supervised seed weights from primary fixed-budget study',
        spatial_training_grid_points=17,validation_spatial_grid_points=17,
        exact_training_label_vectors=256*2*17,
        maximum_additional_gradient_evaluations=1200,optimizer='L-BFGS, strong Wolfe, history50',
        inner_iterations_per_validation_check=20,inner_max_eval=30,
        learning_rate=1.,tolerance_grad=1e-9,tolerance_change=1e-12,
        minimum_evaluations_before_patience=200,validation_patience_checks=8,
        selection='Lowest covered-validation complex port-R RMS, never holdout labels',
        interpolation_validation_adequacy_R_p95=.05,
        numerical_success_R_p95=.03,numerical_success_median_field_relative_L2=.05,
        clear_decision_minimum_sensitivity=.9,clear_decision_minimum_specificity=.9,
        ambiguity_phase_distance_from_165_degrees=2.,ambiguity_magnitude_distance_from_point8=.01,
        thresholds_are_illustrative=True,
        pilot_seed=0,repeat_rule='Repeat seeds1/2 unchanged only if pilot covered-validation criteria pass; not selected by holdout scores',
        no_more_tuning='No architecture, normalization, label allocation or budget changes after fitting',
        holdout_status='Fresh geometry-only set frozen before fitting; prior tests remain diagnostic',
        evaluation_separation_from_prior_designs=2e-5)
    path.write_text(json.dumps(plan,indent=2),encoding='utf-8')
    return plan


def dataset(designs,n):
    ds=torch.tensor([r['d'] for r in designs]).repeat_interleave(2*n)
    states=torch.tensor([0.]*n+[1.]*n).repeat(len(designs))
    xi=torch.linspace(0,1,n).repeat(2*len(designs))
    target=reference_right(xi,ds,states)
    return xi,ds,states,target


def reflection(model,designs):
    ds=torch.tensor([r['d'] for r in designs]).repeat_interleave(2)
    states=torch.tensor([0.,1.]).repeat(len(designs))
    with torch.no_grad():
        values=model.values(torch.zeros_like(ds),ds,states)
        current=torch.complex(values[:,2],values[:,3])
        a=torch.tensor([r['a'] for r in designs]).repeat_interleave(2)
        return (torch.exp(-2*CFG.gamma*a)*(1-current)).numpy().reshape(-1,2)


def validation(model,designs,data):
    pred=reflection(model,designs)
    exact=[]
    for r in designs:
        t=np.tanh(CFG.gamma*r['d']);up=np.exp(-2*CFG.gamma*r['a'])
        exact.append([up*(z+t-1)/(z+t+1) for z in (CFG.z_on,CFG.z_off)])
    exact=np.array(exact)
    errors=np.max(abs(pred-exact),axis=1)
    blocked=np.array([.195<=r['d']<=.222 for r in designs])
    pairs=[]
    for p,e,r in zip(pred,exact,designs):
        pm,em=phase_metrics(*p),phase_metrics(*e)
        pairs.append(dict(exact_phase_valid=em['phase_valid'],predicted_phase_valid=pm['phase_valid'],
            exact_separation=em['separation_degrees'],predicted_separation=pm['separation_degrees'],
            exact_min_magnitude=em['min_magnitude'],predicted_min_magnitude=pm['min_magnitude'],d=r['d']))
    clear=[r for r in pairs if abs(r['exact_separation']-165)>2 and abs(r['exact_min_magnitude']-.8)>.01]
    rates=classification(clear,15,.8)
    xi,d,state,target=data
    with torch.no_grad():
        values=model.values(xi,d,state)
        shaped=(values-target).reshape(len(designs),-1,4)
        target_shaped=target.reshape(len(designs),-1,4)
        field_error=torch.sqrt(shaped.square().sum((1,2))/target_shaped.square().sum((1,2))).numpy()
    result=dict(R_rms=float(np.sqrt(np.mean(abs(pred-exact)**2))),
        R_p95=float(np.quantile(errors,.95)),blocked_R_p95=float(np.quantile(errors[blocked],.95)),
        median_field_relative_L2=float(np.median(field_error)),blocked_median_field_relative_L2=float(np.median(field_error[blocked])),
        clear_designs=len(clear),ambiguous_designs=len(pairs)-len(clear),clear_decisions=rates)
    result['numerical_success']=bool(result['blocked_R_p95']<=.03 and result['blocked_median_field_relative_L2']<=.05
        and rates['actual_feasible']>0 and rates['sensitivity']>=.9 and rates['specificity']>=.9)
    return result


def interpolation_adequacy(plan):
    train=sorted((r for r in plan['designs'] if r['split']=='train'),key=lambda r:r['d'])
    designs=[r for r in plan['designs'] if r['split']=='validation']
    ds=np.array([r['d'] for r in train]);z=np.array([CFG.z_on,CFG.z_off])[:,None]
    t=np.tanh(CFG.gamma*ds);samples=(z+t-1)/(z+t+1)
    errors=[];pairs=[]
    for r in designs:
        target=np.tanh(CFG.gamma*r['d']);up=np.exp(-2*CFG.gamma*r['a'])
        exact=np.array([up*(zz+target-1)/(zz+target+1) for zz in (CFG.z_on,CFG.z_off)])
        pred=np.array([up*(np.interp(r['d'],ds,v.real)+1j*np.interp(r['d'],ds,v.imag)) for v in samples])
        if .195<=r['d']<=.222:errors.append(max(abs(pred-exact)))
        pm,em=phase_metrics(*pred),phase_metrics(*exact)
        if abs(em['separation_degrees']-165)>2 and abs(em['min_magnitude']-.8)>.01:
            pairs.append(dict(exact_phase_valid=em['phase_valid'],predicted_phase_valid=pm['phase_valid'],
                exact_separation=em['separation_degrees'],predicted_separation=pm['separation_degrees'],
                exact_min_magnitude=em['min_magnitude'],predicted_min_magnitude=pm['min_magnitude']))
    rates=classification(pairs,15,.8)
    p95=float(np.quantile(errors,.95))
    return dict(blocked_R_p95=p95,clear_decisions=rates,
                adequate=bool(p95<=.05 and rates['actual_feasible']>0 and rates['sensitivity']>=.9 and rates['specificity']>=.9))


class BudgetReached(Exception):pass


def fit(plan,seed):
    output=OUT/f'seed-{seed}';output.mkdir(exist_ok=True)
    model,payload=load(PRIMARY,'supervised',seed)
    train_designs=[r for r in plan['designs'] if r['split']=='train']
    val_designs=[r for r in plan['designs'] if r['split']=='validation']
    start=time.perf_counter();train_data=dataset(train_designs,17);val_data=dataset(val_designs,17)
    label_seconds=time.perf_counter()-start
    solver=torch.optim.LBFGS(model.parameters(),lr=1,max_iter=20,max_eval=30,history_size=50,
        tolerance_grad=1e-9,tolerance_change=1e-12,line_search_fn='strong_wolfe')
    evaluations=0;history=[];stale=0
    best=validation(model,val_designs,val_data);best_weights=copy.deepcopy(model.state_dict())
    history.append(dict(evaluations=0,training_data_mse=None,validation_R_rms=best['R_rms'],validation_blocked_R_p95=best['blocked_R_p95']))
    started=time.perf_counter()
    def closure():
        nonlocal evaluations
        if evaluations>=1200:raise BudgetReached()
        solver.zero_grad()
        xi,d,state,labels=train_data
        loss=(model.values(xi,d,state)-labels).square().sum(1).mean()
        loss.backward();evaluations+=1
        return loss
    while evaluations<1200:
        before=evaluations
        try:solver.step(closure)
        except BudgetReached:break
        result=validation(model,val_designs,val_data)
        with torch.no_grad():
            xi,d,state,labels=train_data
            error=float((model.values(xi,d,state)-labels).square().sum(1).mean())
        history.append(dict(evaluations=evaluations,training_data_mse=error,validation_R_rms=result['R_rms'],validation_blocked_R_p95=result['blocked_R_p95']))
        if result['R_rms']<best['R_rms']-1e-8:
            best=result;best_weights=copy.deepcopy(model.state_dict());stale=0
        else:stale+=1
        print(json.dumps(dict(seed=seed,evaluations=evaluations,train_mse=error,val_R_rms=result['R_rms'],val_blocked_R_p95=result['blocked_R_p95'])),flush=True)
        if evaluations==before or (evaluations>=200 and stale>=8):break
    seconds=time.perf_counter()-started
    model.load_state_dict(best_weights)
    result_payload=dict(mode='supervised',seed=seed,width=64,
        training_seconds=payload['training_seconds']+seconds,
        additional_training_seconds=seconds,reference_generation_seconds=label_seconds,
        gradient_evaluations=evaluations,initialization='primary supervised saved weights',
        protocol_sha256=hashlib.sha256((OUT/'frozen-protocol.json').read_bytes()).hexdigest(),
        selected_validation=best,weights={k:v.tolist() for k,v in model.state_dict().items()})
    (output/f'supervised_seed-{seed}_weights.json').write_text(json.dumps(result_payload),encoding='utf-8')
    write_csv(output/'continuation-history.csv',history)
    evaluate(output,plan,model,result_payload)
    pairs=read(output/f'supervised_seed-{seed}_pairs.csv')
    decisions=[]
    for split in ('validation','test_offgrid','test_blocked'):
        rows=[r for r in pairs if r['split']==split]
        clear=[r for r in rows if abs(r['exact_separation']-165)>2 and abs(r['exact_min_magnitude']-.8)>.01]
        decisions.append(dict(split=split,total=len(rows),ambiguous=len(rows)-len(clear),
            all_decisions=classification(rows,15,.8),clear_decisions=classification(clear,15,.8)))
    (output/'result.json').write_text(json.dumps(dict(seed=seed,selected_validation=best,decisions=decisions,
        additional_evaluations=evaluations,additional_seconds=seconds),indent=2))
    return best


def main():
    global OUT
    import argparse
    parser=argparse.ArgumentParser()
    parser.add_argument("--output",type=Path,default=OUT)
    args=parser.parse_args();OUT=args.output
    torch.set_num_threads(1)
    plan=freeze()
    existing=OUT/"seed-0/result.json"
    if existing.exists():
        print(existing.read_text(),flush=True)
        print("Existing pilot retained without fitting. Use --output with a fresh directory to reproduce.",flush=True)
        return
    print(json.dumps(dict(protocol_sha256=hashlib.sha256((OUT/'frozen-protocol.json').read_bytes()).hexdigest())),flush=True)
    adequacy=interpolation_adequacy(plan)
    (OUT/'interpolation-adequacy.json').write_text(json.dumps(adequacy,indent=2))
    print(json.dumps(dict(interpolation_adequacy=adequacy)),flush=True)
    if not adequacy['adequate']:
        print('Stopped before fitting: covered interpolation is not adequate under the frozen validation gate.',flush=True)
        return
    best=fit(plan,0)
    if best['numerical_success']:
        for seed in (1,2):fit(plan,seed)
    else:print('Pilot validation criterion not met. No repeat seeds or tuning.',flush=True)


if __name__=='__main__':main()

"""Prospective, exploratory physics-only optimizer control with a fixed budget.

Geometry-only freeze precedes reference inspection. No reference labels in the
training closure. A capped line search restores the last accepted iterate.
"""
import copy
import hashlib
import json
import math
from pathlib import Path
import random
import time
import numpy as np
import torch
import torch.optim.lbfgs as lbfgs_module
from switched_surrogate import CFG,complex_channels,impedance,load,evaluate,write_csv,classification
from representability_control import dataset,validation
from summarize_switched_surrogate import read

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'outputs/optimizer-continuation-control'
INITIAL=ROOT/'outputs/neural-coverage-control/reallocated'
DELTA=2e-5

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def collect_designs(obj):
    found=[]
    if isinstance(obj,dict):
        if 'd' in obj and 'split' in obj and isinstance(obj['d'],(float,int)):found.append(obj['d'])
        for value in obj.values():found.extend(collect_designs(value))
    elif isinstance(obj,list):
        for value in obj:found.extend(collect_designs(value))
    return found

def freeze():
    OUT.mkdir(exist_ok=True)
    path=OUT/'frozen-protocol.json'
    if path.exists():return json.loads(path.read_text())
    old=json.loads((ROOT/'outputs/neural-coverage-control/frozen-control.json').read_text())
    template=copy.deepcopy(old['arms']['reallocated'])
    train=[r for r in template['designs'] if r['split']=='train']
    prior=[];sources=[]
    for source in sorted((ROOT/'outputs').rglob('frozen-*.json')):
        if OUT in source.parents:continue
        ds=collect_designs(json.loads(source.read_text()))
        if ds:prior.extend(ds);sources.append(dict(path=str(source.relative_to(ROOT)),sha256=sha(source)))
    prior=sorted(set(prior));free=[];left=.195
    for d in prior:
        low,high=max(.195,d-DELTA),min(.222,d+DELTA)
        if high<.195 or low>.222:continue
        if low>left:free.append((left,low))
        left=max(left,high)
    if left<.222:free.append((left,.222))
    # Interior margins protect the specified separation from floating rounding.
    pool=[]
    for low,high in free:
        x=low+1e-12
        while x<=high-1e-12:
            pool.append(x);x+=DELTA+1e-12
    assert len(pool)>=192,(len(pool),'Not enough admissible geometry-only candidates')
    rng=random.Random(49420261023);rng.shuffle(pool)
    chosen=pool[:192];rows=[];used=prior+chosen
    def geometry(d,split,index):
        low,high=max(.30,d/.85),min(.42,d/.1)
        assert low<high
        length=rng.uniform(low,high)
        return dict(id=f'optimizer-{split}-{index:04d}',split=split,d=d,length=length,a=length-d,switch_fraction=1-d/length)
    for j,d in enumerate(chosen):rows.append(geometry(d,'validation' if j<64 else 'test_blocked',j))
    for split,count in [('validation',80),('test_offgrid',256)]:
        made=0;attempts=0
        while made<count:
            attempts+=1
            if attempts>1000000:raise RuntimeError('Off-block geometry pool exhausted before fitting')
            d=rng.uniform(.03,.357)
            if .195<=d<=.222 or min(abs(d-x) for x in used)<DELTA:continue
            rows.append(geometry(d,split,made+192));used.append(d);made+=1
    newds=sorted(r['d'] for r in rows)
    minimum_new=min(b-a for a,b in zip(newds,newds[1:]))
    minimum_prior=min(abs(d-x) for d in newds for x in prior)
    assert minimum_new>=DELTA and minimum_prior>=DELTA
    template['designs']=train+rows
    template.update(status='Exploratory optimizer family control. Frozen geometry-only amendment before reference inspection or fitting.',
      seed=49420261023,variants=['lbfgs','adam'],seeds=[0,1,2],
      source_sha256=sha(Path(__file__)),prior_protocol_sources=sources,
      starting_weights={str(s):dict(path=str((INITIAL/f'pinn_seed-{s}_weights.json').relative_to(ROOT)),sha256=sha(INITIAL/f'pinn_seed-{s}_weights.json')) for s in (0,1,2)},
      split_amendment=dict(reason='Original 336 new blocked geometries exceeded the 257 packing upper bound. Changed counts before fitting, no threshold or separation change.',blocked_validation=64,blocked_holdout=128,offblock_validation=80,offblock_holdout=256,geometry_only_candidate_pool=len(pool),minimum_new_d_separation=minimum_new,minimum_separation_from_prior=minimum_prior,prior_unique=len(prior),prior_blocked=sum(.195<=d<=.222 for d in prior)),
      optimizer_control=dict(objective='mean |V_xi + gamma*d*I|^2 + mean |I_xi + gamma*d*V|^2 + mean |V(0)+(1+z)*I(0)-2|^2/4 + mean |V(1)|^2',
        label_access_in_closure=False,full_batch_geometries=256,paired_states=True,xi_points=17,
        maximum_objective_gradient_evaluations=1200,terminal_checkpoint_only=True,validation_checkpoint_selection=False,
        lbfgs=dict(lr=1.,max_iter=20,max_eval=30,history_size=50,tolerance_grad=1e-9,tolerance_change=1e-12,line_search_fn='strong_wolfe'),
        adam=dict(lr=.0002),fresh_optimizer_state_both_arms=True,
        early_convergence_rule='If L-BFGS terminates early, report an incomplete 1200-call comparison and stop Adam at that attained call count. No successful matched-1200 claim.',
        cap_rule='Count all full closure evaluations. Intercept completed line-search returns to record accepted x+t*d. On budget exception restore last accepted vector.',
        gate=dict(blocked_validation_R_p95=.03,blocked_validation_median_joint_right_field_L2=.05,clear_sensitivity=.9,clear_specificity=.9,both_classes_required=True,phase_boundary=165.,magnitude_boundary=.8,phase_margin=2.,magnitude_margin=.01,phase_mask=.05),
        gate_decision_population='All clear validation designs, matching the retained representability gate; blocked clear decisions also reported separately.',
        repeat_rule='Run seeds 1 and 2 unchanged only if either seed 0 arm passes the combined numerical validation gate. No repeat based on holdout.',
        scope='Optimizer family conditional on shared full-batch continuation, not full-batch versus old minibatch. Equal objective-gradient calls are not equal runtime. Prior inspected tests make this exploratory.',
        dense_residual_midpoints=128,no_new_sweeps=True))
    path.write_text(json.dumps(template,indent=2))
    receipt=dict(protocol_sha256=sha(path),source_sha256=sha(Path(__file__)),frozen_before_reference_inspection=True,split_amendment=template['split_amendment'])
    (OUT/'freeze-receipt.json').write_text(json.dumps(receipt,indent=2))
    print(json.dumps(receipt),flush=True)
    return template

def training_grid(designs,n=17):
    d=torch.tensor([r['d'] for r in designs]).repeat_interleave(2*n)
    state=torch.tensor([0.]*n+[1.]*n).repeat(len(designs))
    xi=torch.linspace(0,1,n).repeat(2*len(designs))
    return xi,d,state

def physics_objective(model,grid):
    """Physics only. No reference generator, labels, validation or tests."""
    xi,d,state=grid
    value,dx=model.jets(xi,d,state)
    voltage,current=complex_channels(value);vx,ix=complex_channels(dx)
    pde_v=abs(vx+CFG.gamma*d*current).square().mean()
    pde_i=abs(ix+CFG.gamma*d*voltage).square().mean()
    zero=torch.zeros_like(xi)
    v0,i0=complex_channels(model.values(zero,d,state))
    v1,_=complex_channels(model.values(zero+1,d,state))
    port=abs(v0+(1+impedance(state))*i0-2).square().mean()/4
    short=abs(v1).square().mean()
    return pde_v+pde_i+port+short

class BudgetReached(Exception):pass

def vector(model):return torch.nn.utils.parameters_to_vector(model.parameters()).detach().clone()
def restore(model,x):torch.nn.utils.vector_to_parameters(x.clone(),model.parameters())

def continue_model(model,grid,arm,budget=1200):
    evaluations=0;accepted_updates=0;last_accepted=vector(model);history=[];interrupted=False;early=False
    solver=(torch.optim.LBFGS(model.parameters(),lr=1,max_iter=20,max_eval=30,history_size=50,
      tolerance_grad=1e-9,tolerance_change=1e-12,line_search_fn='strong_wolfe') if arm=='lbfgs'
      else torch.optim.Adam(model.parameters(),lr=.0002))
    original_search=lbfgs_module._strong_wolfe
    def closure():
        nonlocal evaluations
        if evaluations>=budget:raise BudgetReached()
        solver.zero_grad();loss=physics_objective(model,grid);loss.backward();evaluations+=1
        if evaluations%100==0:print(json.dumps(dict(arm=arm,evaluations=evaluations,loss=float(loss.detach()))),flush=True)
        return loss
    def accepted_search(*args,**kwargs):
        nonlocal last_accepted,accepted_updates
        result=original_search(*args,**kwargs)
        _,base,_,direction=args[:4]
        # _strong_wolfe returns accepted loss, gradient, step, evaluation count.
        last_accepted=torch.cat([p.reshape(-1) for p in base])+result[2]*direction
        last_accepted=last_accepted.detach().clone();accepted_updates+=1
        history.append(dict(evaluations=evaluations,accepted_update=accepted_updates,accepted_loss=float(result[0])))
        return result
    started=time.perf_counter()
    try:
        if arm=='lbfgs':lbfgs_module._strong_wolfe=accepted_search
        while evaluations<budget:
            before=accepted_updates
            if arm=='lbfgs':
                try:solver.step(closure)
                except BudgetReached:interrupted=True;break
                if accepted_updates==before:
                    early=True;break
            else:
                loss=closure();solver.step();accepted_updates+=1;last_accepted=vector(model)
                if evaluations%20==0:history.append(dict(evaluations=evaluations,accepted_update=accepted_updates,accepted_loss=None))
    finally:
        lbfgs_module._strong_wolfe=original_search
        restore(model,last_accepted)
    seconds=time.perf_counter()-started
    # Objective-only endpoint diagnostic is explicitly outside the gradient budget.
    with torch.no_grad():terminal=float(physics_objective(model,grid))
    return dict(arm=arm,evaluations=evaluations,accepted_updates=accepted_updates,seconds=seconds,
      cap_interrupted_line_search=interrupted,early_convergence=early,requested_budget=budget,
      terminal_objective_only=terminal,terminal_vector_sha256=hashlib.sha256(last_accepted.numpy().tobytes()).hexdigest()),history

def summary(output,pairs,states,validated):
    groups=[]
    for region in ('validation_offblock','validation_blocked','test_offgrid','test_blocked'):
        pp=[r for r in pairs if (r['split']=='validation' and (region=='validation_blocked')==(.195<=r['d']<=.222))] if region.startswith('validation') else [r for r in pairs if r['split']==region]
        ids={r['id'] for r in pp};ss=[r for r in states if r['id'] in ids]
        clear=[r for r in pp if r['exact_phase_valid'] and abs(r['exact_separation']-165)>2 and abs(r['exact_min_magnitude']-.8)>.01]
        groups.append(dict(region=region,designs=len(pp),ambiguous=len(pp)-len(clear),all_decisions=classification(pp,15,.8),clear_decisions=classification(clear,15,.8),
          R_max_state_p95=float(np.quantile([r['complex_R_error'] for r in pp],.95)),
          median_voltage_relative_L2=float(np.median([r['voltage_relative_L2'] for r in ss])),
          median_current_relative_L2=float(np.median([r['current_relative_L2'] for r in ss])),
          pde_voltage_rms_median=float(np.median([r['pde_voltage_rms'] for r in ss])),
          pde_current_rms_median=float(np.median([r['pde_current_rms'] for r in ss])),
          maximum_passivity_violation=max(r['predicted_passivity_violation'] for r in ss),
          maximum_extraction_disagreement=max(r['reflection_extraction_disagreement'] for r in ss),
          maximum_power_balance_defect=max(abs(r['power_balance_defect']) for r in ss),
          maximum_driven_interface_abs=max(r['driven_interface_abs'] for r in ss),
          maximum_terminal_voltage_abs=max(r['terminal_voltage_abs'] for r in ss)))
    result=dict(validation=validated,regions=groups)
    (output/'evaluation-summary.json').write_text(json.dumps(result,indent=2))
    return result

def fit_pair(plan,seed):
    train=[r for r in plan['designs'] if r['split']=='train'];val=[r for r in plan['designs'] if r['split']=='validation']
    grid=training_grid(train)
    # References are generated only after geometry/hash freeze, outside training.
    val_data=dataset(val,17)
    results={};budget=1200
    for arm in ('lbfgs','adam'):
        output=OUT/f'seed-{seed}'/arm;output.mkdir(parents=True,exist_ok=True)
        if (output/'result.json').exists():raise RuntimeError('Refusing to overwrite completed continuation')
        model,payload=load(INITIAL,'pinn',seed)
        initial_hash=hashlib.sha256(vector(model).numpy().tobytes()).hexdigest()
        start_val=validation(model,val,val_data)
        diagnostic,history=continue_model(model,grid,arm,budget)
        if arm=='lbfgs':budget=diagnostic['evaluations']
        validated=validation(model,val,val_data)
        # A missing class makes the gate inconclusive, never successful.
        rates=validated['clear_decisions']
        classes=rates['actual_feasible']>0 and rates['actual_infeasible']>0
        validated['numerical_success']=bool(classes and validated['blocked_R_p95']<=.03 and validated['blocked_median_field_relative_L2']<=.05 and rates['sensitivity']>=.9 and rates['specificity']>=.9)
        validated['both_clear_classes_present']=classes
        diagnostic.update(seed=seed,initial_vector_sha256=initial_hash,initial_validation=start_val,terminal_validation=validated,protocol_sha256=sha(OUT/'frozen-protocol.json'))
        # Keep mode='pinn' for the retained independent NumPy verifier.
        payload=dict(mode='pinn',seed=seed,width=64,training_seconds=payload['training_seconds']+diagnostic['seconds'],additional_training_seconds=diagnostic['seconds'],gradient_evaluations=diagnostic['evaluations'],optimizer_arm=arm,protocol_sha256=diagnostic['protocol_sha256'],weights={k:v.detach().tolist() for k,v in model.state_dict().items()})
        (output/f'pinn_seed-{seed}_weights.json').write_text(json.dumps(payload))
        write_csv(output/'accepted-history.csv',history)
        states,pairs=evaluate(output,plan,model,payload)
        summary(output,pairs,states,validated)
        (output/'result.json').write_text(json.dumps(diagnostic,indent=2))
        print(json.dumps(dict(seed=seed,arm=arm,result=diagnostic)),flush=True)
        results[arm]=diagnostic
    assert results['lbfgs']['initial_vector_sha256']==results['adam']['initial_vector_sha256']
    assert results['lbfgs']['evaluations']==results['adam']['evaluations']
    return results

def main():
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('--freeze-only',action='store_true');args=parser.parse_args()
    torch.set_num_threads(1);plan=freeze()
    assert sha(Path(__file__))==plan['source_sha256'],'Source changed after freeze; inspect before fitting'
    if args.freeze_only:return
    if (OUT/'seed-0/lbfgs/result.json').exists():raise RuntimeError('Completed pilot retained. No automatic rerun.')
    pilot=fit_pair(plan,0)
    repeat=any(r['terminal_validation']['numerical_success'] for r in pilot.values())
    results={'0':pilot}
    if repeat:
        for seed in (1,2):results[str(seed)]=fit_pair(plan,seed)
    conclusion=dict(pilot_validation_gate_passed=repeat,seeds_run=list(map(int,results)),maximum_runs=6,results=results,
      interpretation='Exploratory optimizer-family comparison conditional on covered full-batch continuation. No unique cause or hardware validation follows automatically.')
    (OUT/'results.json').write_text(json.dumps(conclusion,indent=2))
    print(json.dumps(dict(repeat_rule_triggered=repeat,seeds_run=list(results))),flush=True)

if __name__=='__main__':main()

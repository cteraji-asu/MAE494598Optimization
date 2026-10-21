"""Paired fresh-initialization hard/soft boundary ablation; no analytic labels in training."""
import copy
import hashlib
import json
from pathlib import Path
import random
import time
import numpy as np
import torch
from switched_surrogate import FieldNet,CFG,complex_channels,impedance,evaluate,classification
from switched_line import response,write_csv
from optimizer_control import collect_designs
from representability_control import dataset,validation,reflection
from summarize_switched_surrogate import read

ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'outputs/hard-boundary-control';DELTA=2e-5
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

class HardFieldNet(FieldNet):
    def values(self,xi,d,state):
        raw=super().values(xi,d,state);zero=torch.zeros_like(xi)
        p0=super().values(zero,d,state);p1=super().values(zero+1,d,state)
        v,i=complex_channels(raw);v0,i0=complex_channels(p0);v1,_=complex_channels(p1)
        b0=v0+(1+impedance(state))*i0-2
        v=v-xi*v1-(1-xi)*b0
        return torch.stack((v.real,v.imag,i.real,i.imag),1)
    def jets(self,xi,d,state):
        raw,dx=super().jets(xi,d,state);zero=torch.zeros_like(xi)
        p0=super().values(zero,d,state);p1=super().values(zero+1,d,state)
        v,i=complex_channels(raw);vx,ix=complex_channels(dx)
        v0,i0=complex_channels(p0);v1,_=complex_channels(p1)
        b0=v0+(1+impedance(state))*i0-2
        v=v-xi*v1-(1-xi)*b0;vx=vx-v1+b0
        return torch.stack((v.real,v.imag,i.real,i.imag),1),torch.stack((vx.real,vx.imag,ix.real,ix.imag),1)
    def port_values(self,xi,d,state):
        # I is unchanged by the transform; R-only inference needs one raw pass.
        return super().values(xi,d,state)

def losses(model,xi,d,state,hard):
    value,dx=model.jets(xi,d,state);v,i=complex_channels(value);vx,ix=complex_channels(dx)
    pv=abs(vx+CFG.gamma*d*i).square().mean();pi=abs(ix+CFG.gamma*d*v).square().mean()
    if hard:
        # Identically zero BC penalties; do not waste six redundant raw passes.
        port=torch.zeros((),dtype=xi.dtype);short=torch.zeros((),dtype=xi.dtype)
    else:
        zero=torch.zeros_like(xi);v0,i0=complex_channels(model.values(zero,d,state));v1,_=complex_channels(model.values(zero+1,d,state))
        port=abs(v0+(1+impedance(state))*i0-2).square().mean()/4;short=abs(v1).square().mean()
    return pv+pi+port+short,dict(pde_voltage=pv,pde_current=pi,driven_interface=port,terminal_short=short)

def raw_vector(model):return torch.nn.utils.parameters_to_vector(model.parameters()).detach().numpy().tobytes()

def fresh_pool(prior):
    free=[];left=.195
    for d in sorted(prior):
        low,high=max(.195,d-DELTA),min(.222,d+DELTA)
        if high<.195 or low>.222:continue
        if low>left:free.append((left,low))
        left=max(left,high)
    if left<.222:free.append((left,.222))
    pool=[]
    for low,high in free:
        n=int((high-low)//DELTA)+1
        offset=((high-low)-(n-1)*DELTA)/2
        for k in range(n):
            value=low+offset+k*DELTA
            if min(abs(value-x) for x in prior)>=DELTA and (not pool or value-pool[-1]>=DELTA):pool.append(value)
    return pool,free

def freeze():
    OUT.mkdir(exist_ok=True);path=OUT/'frozen-protocol.json'
    if path.exists():return json.loads(path.read_text())
    covered=json.loads((ROOT/'outputs/neural-coverage-control/frozen-control.json').read_text())['arms']['reallocated']
    train=[r for r in covered['designs'] if r['split']=='train'];prior=[];sources=[]
    for p in sorted((ROOT/'outputs').rglob('frozen-*.json')):
        if OUT in p.parents:continue
        values=collect_designs(json.loads(p.read_text()))
        if values:prior.extend(values);sources.append(dict(path=str(p.relative_to(ROOT)),sha256=sha(p)))
    prior=sorted(set(prior));pool,intervals=fresh_pool(prior)
    if len(pool)<60:raise RuntimeError(f'Only {len(pool)} geometrically admissible blocked candidates, need60. No distance relaxation or class resampling.')
    rng=random.Random(49420261024);rng.shuffle(pool);chosen=pool[:60];used=prior+chosen;new=[]
    def design(d,split,index):
        lo,hi=max(.3,d/.85),min(.42,d/.1);length=rng.uniform(lo,hi)
        return dict(id=f'hardbc-{split}-{index:04d}',split=split,d=d,length=length,a=length-d,switch_fraction=1-d/length)
    for j,d in enumerate(chosen):new.append(design(d,'validation' if j<30 else 'test_blocked',j))
    for split,count in [('validation',80),('test_offgrid',256)]:
        made=0;attempts=0
        while made<count:
            attempts+=1
            if attempts>1000000:raise RuntimeError('Off-block geometry generation exhausted before fitting.')
            d=rng.uniform(.03,.357)
            if .195<=d<=.222 or min(abs(d-x) for x in used)<DELTA:continue
            new.append(design(d,split,made+60));used.append(d);made+=1
    ds=sorted(r['d'] for r in new)
    min_new=min(b-a for a,b in zip(ds,ds[1:]));min_prior=min(abs(d-x) for d in ds for x in prior)
    assert min_new>=DELTA and min_prior>=DELTA
    plan=copy.deepcopy(covered);plan['designs']=train+new
    plan.update(status='Prospective fresh-initialization hard/soft boundary ablation, chosen after historical signed residual diagnosis. No reference class inspection before freeze.',
      seed=49420261024,seeds=[0,1,2],variants=['soft','hard'],width=64,steps=4000,geometry_batch=32,points_per_geometry=4,
      source_hashes={p.name:sha(p) for p in [Path(__file__),ROOT/'code/switched_surrogate.py',ROOT/'code/switched_line.py']},prior_protocol_sources=sources,
      fresh_counts=dict(validation_offblock=80,validation_blocked=30,final_offblock=256,final_blocked=30,remaining_candidate_pool=len(pool)),
      prefit_geometry_amendment='Initial 32+32 blocked proposal could not freeze: only61 admissible packed candidates remained. Changed to30+30 before any class/reference inspection or fitting; kept minimum distance and all other controls.',
      separation=dict(minimum_new=min_new,minimum_from_prior=min_prior,required=DELTA,scope='All prior neural train/validation/test protocol geometries. Conventional development sweeps are historical problem exploration.'),
      transform='I=i; V=v-xi*v(1)-(1-xi)*(v(0)+(1+zs)*i(0)-2). Raw endpoint evaluations stay differentiable. No analytic solution, reflection target or labels inserted.',
      controls=dict(fresh_paired_raw_initialization=True,raw_parameter_count=4676,optimizer='Adam cosine .002 to .0002',objective_gradient_evaluations_each=4000,
        sampling='Same saved geometry order and generator9000+seed in both arms; paired states share xi; batch32 geometries x4points x2states.',
        objective='PDE(V)+PDE(I)+port/4+short, with BC terms identically zero for hard transform.',
        selection='Minimum overall validation complex port-R RMS among steps0,500,1000,...4000. Full4000 training budget spent in every run. No validation-driven early stop or hyperparameter changes.',
        final_holdout='Geometry-only set frozen before training. No final reference evaluations until all six selected checkpoint hashes are sealed.',
        gate='Unchanged: blocked validation max-state R95<=.03, normalized joint right-field median L2<=.05, clear validation sensitivity/specificity>=.9 with both classes present. Missing class is inconclusive.',
        ambiguity='within2deg of165 or .01 of magnitude.8; phase mask.05',
        causal_limit='Hard enforcement also changes the trial-function representation. Improvement supports an enforcement bottleneck, not unique proof of gradient imbalance. Mixed residuals and cancellation remain possible.',
        no_sweep='Exactly six predetermined fits. No factorial or new tuning unless separate diagnostic evidence and prospective justification.'),
      difficulty_knob='d changes response non-monotonically. Report measured output-residual gain and detuning; do not label a geometry sweep monotonically harder.',
      diagnostic_protocol_sha256=sha(ROOT/'outputs/residual-error-budget/frozen-protocol.json'))
    path.write_text(json.dumps(plan,indent=2))
    print(json.dumps(dict(protocol_sha256=sha(path),fresh_counts=plan['fresh_counts'],separation=plan['separation'])),flush=True)
    return plan

def port_reflections(model,designs):
    ds=torch.tensor([r['d'] for r in designs]).repeat_interleave(2);state=torch.tensor([0.,1.]).repeat(len(designs))
    with torch.no_grad():
        values=model.port_values(torch.zeros_like(ds),ds,state) if isinstance(model,HardFieldNet) else model.values(torch.zeros_like(ds),ds,state)
        current=torch.complex(values[:,2],values[:,3]);a=torch.tensor([r['a'] for r in designs]).repeat_interleave(2)
        return (torch.exp(-2*CFG.gamma*a)*(1-current)).numpy().reshape(-1,2)

def fit(plan,arm,seed):
    output=OUT/arm;output.mkdir(exist_ok=True)
    if (output/f'pinn_seed-{seed}_weights.json').exists():raise RuntimeError('Completed arm retained; no overwrite.')
    torch.manual_seed(seed);model=HardFieldNet(64) if arm=='hard' else FieldNet(64)
    initial_hash=hashlib.sha256(raw_vector(model)).hexdigest();rng=torch.Generator().manual_seed(9000+seed)
    training=[r for r in plan['designs'] if r['split']=='train'];val=[r for r in plan['designs'] if r['split']=='validation']
    ds=torch.tensor([r['d'] for r in training])
    refstart=time.perf_counter();exact=np.array([[response(r['length'],r['switch_fraction'],s)[0] for s in (0,1)] for r in val]);reference_seconds=time.perf_counter()-refstart
    optimizer=torch.optim.Adam(model.parameters(),lr=.002);schedule=torch.optim.lr_scheduler.CosineAnnealingLR(optimizer,4000,eta_min=.0002)
    history=[];selection=[];best=float('inf');selected=None;selected_step=0;stream=hashlib.sha256();validation_seconds=0.
    started=time.perf_counter()
    def select(step):
        nonlocal best,selected,selected_step,validation_seconds
        tick=time.perf_counter();score=float(np.sqrt(np.mean(abs(port_reflections(model,val)-exact)**2)));validation_seconds+=time.perf_counter()-tick
        selection.append(dict(step=step,validation_complex_R_rms=score))
        if score<best:best=score;selected=copy.deepcopy(model.state_dict());selected_step=step
    select(0)
    for step in range(1,4001):
        choices=torch.randint(len(training),(32,),generator=rng);base=ds[choices].repeat_interleave(4);xx=torch.rand(base.numel(),generator=rng)
        d=torch.cat((base,base));xi=torch.cat((xx,xx));state=torch.cat((torch.zeros_like(base),torch.ones_like(base)))
        stream.update(choices.numpy().tobytes());stream.update(xx.numpy().tobytes())
        optimizer.zero_grad();loss,parts=losses(model,xi,d,state,arm=='hard');loss.backward();optimizer.step();schedule.step()
        if step%100==0:history.append(dict(step=step,objective=float(loss.detach()),**{k:float(v.detach()) for k,v in parts.items()}))
        if step%500==0:select(step)
        if step%1000==0:print(json.dumps(dict(arm=arm,seed=seed,step=step,objective=float(loss.detach()),seconds=time.perf_counter()-started)),flush=True)
    seconds=time.perf_counter()-started;terminal_hash=hashlib.sha256(raw_vector(model)).hexdigest();model.load_state_dict(selected)
    payload=dict(mode='pinn',seed=seed,width=64,output_transform=arm,weights={k:v.detach().tolist() for k,v in model.state_dict().items()},
      training_seconds=seconds,reference_generation_seconds=reference_seconds,validation_seconds=validation_seconds,
      gradient_evaluations=4000,selected_step=selected_step,selection_R_rms=best,initial_raw_sha256=initial_hash,terminal_raw_sha256=terminal_hash,sampling_sha256=stream.hexdigest(),protocol_sha256=sha(OUT/'frozen-protocol.json'))
    (output/f'pinn_seed-{seed}_weights.json').write_text(json.dumps(payload))
    write_csv(output/f'pinn_seed-{seed}_loss.csv',history);write_csv(output/f'pinn_seed-{seed}_selection.csv',selection)
    return payload

def load(arm,seed):
    payload=json.loads((OUT/arm/f'pinn_seed-{seed}_weights.json').read_text());model=HardFieldNet(64) if arm=='hard' else FieldNet(64)
    model.load_state_dict({k:torch.tensor(v) for k,v in payload['weights'].items()});return model,payload

def main():
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('--freeze-only',action='store_true');args=parser.parse_args()
    torch.set_num_threads(1);plan=freeze()
    for name,digest in plan['source_hashes'].items():assert sha(ROOT/'code'/name)==digest
    if args.freeze_only:return
    if (OUT/'selection-seal.json').exists():raise RuntimeError('Selected models sealed. Use the evaluation script; no automatic fitting rerun.')
    records={}
    for seed in (0,1,2):
        for arm in ('soft','hard'):records[f'{arm}-{seed}']=fit(plan,arm,seed)
        assert records[f'soft-{seed}']['initial_raw_sha256']==records[f'hard-{seed}']['initial_raw_sha256']
        assert records[f'soft-{seed}']['sampling_sha256']==records[f'hard-{seed}']['sampling_sha256']
    seal=dict(protocol_sha256=sha(OUT/'frozen-protocol.json'),final_holdout_reference_accessed=False,selected=[dict(arm=arm,seed=seed,path=f'{arm}/pinn_seed-{seed}_weights.json',sha256=sha(OUT/arm/f'pinn_seed-{seed}_weights.json'),selected_step=records[f'{arm}-{seed}']['selected_step']) for seed in (0,1,2) for arm in ('soft','hard')])
    (OUT/'selection-seal.json').write_text(json.dumps(seal,indent=2))
    print('All six model selections sealed before final holdout reference access.',flush=True)

if __name__=='__main__':main()

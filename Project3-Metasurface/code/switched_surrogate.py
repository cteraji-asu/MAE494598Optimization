"""Frozen, geometry-held-out comparison for the synthetic finite-switch line.

The model learns the right-segment field family in d and state. Common left
propagation is applied analytically. No neural training at held-out d values.
"""
import argparse
import bisect
import cmath
import csv
import hashlib
import json
import math
from pathlib import Path
import platform
import random
import statistics
import time
import numpy as np
import torch
from switched_line import Config, field, phase_metrics, response, write_csv

torch.set_default_dtype(torch.float64)
CFG = Config()
D_MIN, D_MAX = .03, .357
BLOCK = (.195, .222)
ROOT = Path(__file__).resolve().parents[1]
REFERENCE_SECONDS=0.0


def freeze(out):
    """Geometry-only split and analysis plan, created once before any fitting."""
    out.mkdir(parents=True, exist_ok=True)
    path = out/"frozen-protocol.json"
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    rng = random.Random(49420261020)
    used, rows = [], []
    for split, count in (("train",256),("validation",96),("test_offgrid",224),("test_blocked",160)):
        made = 0
        while made < count:
            d = rng.uniform(*(BLOCK if split=="test_blocked" else (D_MIN,D_MAX)))
            if split!="test_blocked" and BLOCK[0]<=d<=BLOCK[1]:
                continue
            if used and min(abs(d-v) for v in used)<2e-5:
                continue
            low, high = max(.30,d/.85), min(.42,d/.10)
            if low>=high:
                continue
            length = rng.uniform(low, high)
            rows.append(dict(id=f"{split}-{made:04d}",split=split,d=d,
                             length=length,switch_fraction=1-d/length,a=length-d))
            used.append(d)
            made += 1
    plan = dict(status="Frozen before fitting; geometry-only split",
        seed=49420261020, architecture="3-64-64-4 tanh; inputs xi,d,state; V/I real/imag",
        width=64, steps=4000, seeds=[0,1,2], variants=["pinn","supervised"],
        learning_rate=.002, final_learning_rate=.0002, optimizer="Adam, cosine schedule",
        early_stopping=False, hyperparameter_selection="None; fixed budget. Validation diagnostic only.",
        geometry_batch=32, points_per_geometry=4, both_states_every_batch=True,
        dtype="float64",threads=1,d_range=[D_MIN,D_MAX],blocked_d_interval=list(BLOCK),
        minimum_all_design_d_separation=2e-5,
        physics_loss="mean complex squared PDE V + PDE I + driven interface /4 + short",
        data_loss="mean |V-Vref|^2+|I-Iref|^2, same geometry/xi stream and architecture",
        reference_cost="Reference fields generated on demand in both runs for shared diagnostic logging; included in training wall time and timed separately, never added twice",
        primary_reflection="1-Iright(0); compare Vright(0)+z_s*Iright(0)-1 separately",
        illustrative_phase_tolerances=[5,15,30],illustrative_magnitude_floors=[.5,.8,.95],
        phase_mask_floor=.05,decision_primary_tolerance=15,decision_primary_magnitude=.8,
        near_boundary_phase_margin_degrees=5,near_boundary_magnitude_margin=.05,
        field_evaluation_points_per_segment=129,
        no_test_training="No reference labels or residual points from test/validation geometries; blocked d excluded from training",
        analytic_factor="R_s(a,d)=exp(-2 gamma a)*r_s(d); phase separation depends only on d",
        source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        hardware=dict(platform=platform.platform(),processor=platform.processor(),torch=torch.__version__),
        designs=rows)
    path.write_text(json.dumps(plan,indent=2),encoding="utf-8")
    return plan


class FieldNet(torch.nn.Module):
    def __init__(self,width=64):
        super().__init__()
        self.first=torch.nn.Linear(3,width)
        self.second=torch.nn.Linear(width,width)
        self.last=torch.nn.Linear(width,4)

    def values(self,xi,d,state):
        """R-only inference path, with no unused spatial derivative work."""
        features=torch.stack((2*xi-1,2*(d-D_MIN)/(D_MAX-D_MIN)-1,2*state-1),1)
        return self.last(torch.tanh(self.second(torch.tanh(self.first(features)))))

    def jets(self,xi,d,state):
        features=torch.stack((2*xi-1,2*(d-D_MIN)/(D_MAX-D_MIN)-1,2*state-1),1)
        h=torch.tanh(self.first(features))
        hx=(1-h*h)*(2*self.first.weight[:,0])
        q=torch.tanh(self.second(h))
        qx=(1-q*q)*(hx@self.second.weight.T)
        return self.last(q),qx@self.last.weight.T


def complex_channels(values):
    return torch.complex(values[:,0],values[:,1]),torch.complex(values[:,2],values[:,3])


def impedance(state):
    return (1-state)*CFG.z_on+state*CFG.z_off


def reference_right(xi,d,state):
    q=CFG.gamma*d
    terminal=2/(torch.sinh(q)+(1+impedance(state))*torch.cosh(q))
    remaining=q*(1-xi)
    return torch.stack((
        (terminal*torch.sinh(remaining)).real,(terminal*torch.sinh(remaining)).imag,
        (terminal*torch.cosh(remaining)).real,(terminal*torch.cosh(remaining)).imag),1)


def losses(model,xi,d,state,mode):
    global REFERENCE_SECONDS
    value,dx=model.jets(xi,d,state)
    voltage,current=complex_channels(value)
    vx,ix=complex_channels(dx)
    pde_v=abs(vx+CFG.gamma*d*current).square().mean()
    pde_i=abs(ix+CFG.gamma*d*voltage).square().mean()
    zero=torch.zeros_like(xi)
    v0,i0=complex_channels(model.jets(zero,d,state)[0])
    v1,_=complex_channels(model.jets(zero+1,d,state)[0])
    port=abs(v0+(1+impedance(state))*i0-2).square().mean()/4
    short=abs(v1).square().mean()
    started=time.perf_counter()
    reference=reference_right(xi,d,state)
    REFERENCE_SECONDS+=time.perf_counter()-started
    data=(value-reference).square().sum(1).mean()
    physics=pde_v+pde_i+port+short
    return (physics if mode=="pinn" else data),dict(pde_voltage=pde_v,pde_current=pde_i,
        driven_interface=port,terminal_short=short,data=data)


def train(out,plan,mode,seed):
    global REFERENCE_SECONDS
    prefix=f"{mode}_seed-{seed}"
    checkpoint=out/f"{prefix}_weights.json"
    if checkpoint.exists():
        raise RuntimeError(f"Refusing to overwrite completed run {prefix}")
    torch.manual_seed(seed)
    model=FieldNet(plan["width"])
    rng=torch.Generator().manual_seed(9000+seed)
    designs=[r for r in plan["designs"] if r["split"]=="train"]
    d_values=torch.tensor([r["d"] for r in designs])
    optimizer=torch.optim.Adam(model.parameters(),lr=plan["learning_rate"])
    scheduler=torch.optim.lr_scheduler.CosineAnnealingLR(optimizer,plan["steps"],
                                                        eta_min=plan["final_learning_rate"])
    history=[]
    REFERENCE_SECONDS=0.0
    started=time.perf_counter()
    for step in range(plan["steps"]+1):
        choices=torch.randint(len(designs),(plan["geometry_batch"],),generator=rng)
        base=d_values[choices].repeat_interleave(plan["points_per_geometry"])
        xi_base=torch.rand(base.numel(),generator=rng)
        d=torch.cat((base,base))
        xi=torch.cat((xi_base,xi_base))
        state=torch.cat((torch.zeros_like(base),torch.ones_like(base)))
        optimizer.zero_grad()
        loss,terms=losses(model,xi,d,state,mode)
        if step%100==0 or step==plan["steps"]:
            row=dict(step=step,objective=float(loss.detach()),
                     **{k:float(v.detach()) for k,v in terms.items()})
            history.append(row)
        if step%1000==0:
            print(json.dumps(dict(run=prefix,step=step,objective=float(loss.detach()),
                                  elapsed_seconds=time.perf_counter()-started)),flush=True)
        if step==plan["steps"]:
            break
        loss.backward()
        optimizer.step()
        scheduler.step()
    seconds=time.perf_counter()-started
    write_csv(out/f"{prefix}_loss.csv",history)
    payload=dict(mode=mode,seed=seed,width=plan["width"],training_seconds=seconds,
                 included_reference_generation_seconds=REFERENCE_SECONDS,
                 gradient_evaluations=plan["steps"],
                 protocol_sha256=hashlib.sha256((out/"frozen-protocol.json").read_bytes()).hexdigest(),
                 weights={k:v.detach().tolist() for k,v in model.state_dict().items()})
    checkpoint.write_text(json.dumps(payload),encoding="utf-8")
    return model,payload


def load(out,mode,seed):
    payload=json.loads((out/f"{mode}_seed-{seed}_weights.json").read_text())
    model=FieldNet(payload["width"])
    model.load_state_dict({k:torch.tensor(v) for k,v in payload["weights"].items()})
    return model,payload


def predict(model,xi,d,state):
    with torch.no_grad():
        return model.jets(torch.as_tensor(xi),torch.as_tensor(d),torch.as_tensor(state))


def evaluate(out,plan,model,payload):
    prefix=f'{payload["mode"]}_seed-{payload["seed"]}'
    rows,pairs,fields=[],[],[]
    grid=np.linspace(0,1,plan["field_evaluation_points_per_segment"])
    mid=(np.arange(128)+.5)/128
    examples={}
    tests=[r for r in plan["designs"] if r["split"].startswith("test")]
    for name,target in (("near_node",.25),("transition",.2084)):
        examples[min(tests,key=lambda r:abs(r["d"]-target))["id"]]=name
    for design in plan["designs"]:
        if design["split"]=="train":
            continue
        length,a,d,p=design["length"],design["a"],design["d"],design["switch_fraction"]
        predicted,exact=[],[]
        for state in (0,1):
            value,dx=predict(model,grid,np.full_like(grid,d),np.full_like(grid,float(state)))
            vr,ir=[z.numpy() for z in complex_channels(value)]
            v0,i0=vr[0],ir[0]
            r_local=1-i0
            r_alt=v0+CFG.impedance(state)*i0-1
            r=cmath.exp(-2*CFG.gamma*a)*r_local
            reference=response(length,p,state)[0]
            predicted.append(r);exact.append(reference)
            scale=cmath.exp(-CFG.gamma*a)
            xr=grid*d+a
            xl=grid*a
            vp_right,ip_right=scale*vr,scale*ir
            vp_left=np.exp(-CFG.gamma*xl)+r*np.exp(CFG.gamma*xl)
            ip_left=np.exp(-CFG.gamma*xl)-r*np.exp(CFG.gamma*xl)
            ve_left=np.exp(-CFG.gamma*xl)+reference*np.exp(CFG.gamma*xl)
            ie_left=np.exp(-CFG.gamma*xl)-reference*np.exp(CFG.gamma*xl)
            ve_right,ie_right=np.array([field(float(x),1,length,p,state) for x in grid]).T
            def integrate(left,right):
                return np.trapezoid(left,grid)*a+np.trapezoid(right,grid)*d
            error_v=math.sqrt(integrate(abs(vp_left-ve_left)**2,abs(vp_right-ve_right)**2)
                              /integrate(abs(ve_left)**2,abs(ve_right)**2))
            error_i=math.sqrt(integrate(abs(ip_left-ie_left)**2,abs(ip_right-ie_right)**2)
                              /integrate(abs(ie_left)**2,abs(ie_right)**2))
            mv,mdx=predict(model,mid,np.full_like(mid,d),np.full_like(mid,float(state)))
            mvv,mii=[z.numpy() for z in complex_channels(mv)]
            dv,di=[z.numpy() for z in complex_channels(mdx)]
            residual_v=abs(dv+CFG.gamma*d*mii)
            residual_i=abs(di+CFG.gamma*d*mvv)
            loss_line=.5*CFG.alpha*integrate(abs(vp_left)**2+abs(ip_left)**2,
                                            abs(vp_right)**2+abs(ip_right)**2)
            loss_switch=.5*CFG.impedance(state).real*abs(scale*i0)**2
            terminal_power=.5*(vp_right[-1]*ip_right[-1].conjugate()).real
            pin=.5*(1-abs(r)**2)
            rows.append(dict(id=design["id"],split=design["split"],state=state,d=d,a=a,
                length=length,switch_fraction=p,reference_real=reference.real,reference_imag=reference.imag,
                predicted_real=r.real,predicted_imag=r.imag,complex_R_error=abs(r-reference),
                magnitude_error=abs(abs(r)-abs(reference)),voltage_relative_L2=error_v,
                current_relative_L2=error_i,reflection_extraction_disagreement=abs(scale*scale*(r_local-r_alt)),
                predicted_magnitude=abs(r),predicted_passivity_violation=max(0,abs(r)-1),
                pde_voltage_rms=float(np.sqrt(np.mean(residual_v**2))),
                pde_current_rms=float(np.sqrt(np.mean(residual_i**2))),
                driven_interface_abs=abs(v0+(1+CFG.impedance(state))*i0-2),
                terminal_voltage_abs=abs(vr[-1]),power_balance_defect=pin-loss_line-loss_switch-terminal_power,
                terminal_real_power=terminal_power))
            if design["id"] in examples:
                for segment,x,pv,pi,ev,ei in ((0,xl,vp_left,ip_left,ve_left,ie_left),
                                              (1,xr,vp_right,ip_right,ve_right,ie_right)):
                    for j in range(len(grid)):
                        fields.append(dict(example=examples[design["id"]],id=design["id"],state=state,
                            segment=segment,local=grid[j],x=x[j],d=d,a=a,
                            predicted_v_real=pv[j].real,predicted_v_imag=pv[j].imag,
                            reference_v_real=ev[j].real,reference_v_imag=ev[j].imag,
                            predicted_i_real=pi[j].real,predicted_i_imag=pi[j].imag,
                            reference_i_real=ei[j].real,reference_i_imag=ei[j].imag))
        pm,em=phase_metrics(*predicted),phase_metrics(*exact)
        # Local response sensitivity is a conventional property, not a neural error.
        h=1e-5
        slope=max(abs((response(a+d+h,a/(a+d+h),s)[0]-response(a+d-h,a/(a+d-h),s)[0])/(2*h)) for s in (0,1))
        pairs.append(dict(id=design["id"],split=design["split"],d=d,a=a,
            detuning=abs(CFG.beta*d-math.pi/2),reference_response_gradient=slope,
            exact_separation=em["separation_degrees"],predicted_separation=pm["separation_degrees"],
            exact_min_magnitude=em["min_magnitude"],predicted_min_magnitude=pm["min_magnitude"],
            exact_phase_valid=em["phase_valid"],predicted_phase_valid=pm["phase_valid"],
            separation_error=(abs(pm["separation_degrees"]-em["separation_degrees"])
                              if pm["phase_valid"] and em["phase_valid"] else None),
            complex_R_error=max(abs(p-e) for p,e in zip(predicted,exact))))
    write_csv(out/f"{prefix}_states.csv",rows)
    write_csv(out/f"{prefix}_pairs.csv",pairs)
    write_csv(out/f"{prefix}_fields.csv",fields)
    return rows,pairs


def classification(pairs,tolerance,floor):
    counts=dict(tp=0,fn=0,tn=0,fp=0,phase_masked_predictions=0)
    for r in pairs:
        actual=bool(r["exact_phase_valid"]) and 180-r["exact_separation"]<=tolerance and r["exact_min_magnitude"]>=floor
        predicted=bool(r["predicted_phase_valid"]) and 180-r["predicted_separation"]<=tolerance and r["predicted_min_magnitude"]>=floor
        counts[("t" if actual==predicted else "f")+("p" if predicted else "n")]+=1
        counts["phase_masked_predictions"]+=not r["predicted_phase_valid"]
    positive=counts["tp"]+counts["fn"]
    negative=counts["tn"]+counts["fp"]
    return dict(**counts,actual_feasible=positive,actual_infeasible=negative,
        sensitivity=counts["tp"]/positive if positive else None,
        specificity=counts["tn"]/negative if negative else None,
        false_feasible_rate=counts["fp"]/negative if negative else None,
        false_infeasible_rate=counts["fn"]/positive if positive else None)


def interpolation(out,plan):
    train=sorted((r for r in plan["designs"] if r["split"]=="train"),key=lambda r:r["d"])
    d=np.array([r["d"] for r in train])
    reference=np.array([[response(float(v)+.1,.1/(float(v)+.1),s)[0]*cmath.exp(2*CFG.gamma*.1)
                         for v in d] for s in (0,1)])
    def infer(designs):
        target=np.array([r["d"] for r in designs])
        a=np.array([r["a"] for r in designs])
        return np.array([np.interp(target,d,z.real)+1j*np.interp(target,d,z.imag)
                         for z in reference])*np.exp(-2*CFG.gamma*a)
    pairs=[]
    for design in plan["designs"]:
        if design["split"]=="train":continue
        pred=infer([design])[:,0]
        exact=[response(design["length"],design["switch_fraction"],s)[0] for s in (0,1)]
        pm,em=phase_metrics(*pred),phase_metrics(*exact)
        pairs.append(dict(id=design["id"],split=design["split"],d=design["d"],a=design["a"],
            detuning=abs(CFG.beta*design["d"]-math.pi/2),reference_response_gradient=None,
            exact_separation=em["separation_degrees"],predicted_separation=pm["separation_degrees"],
            exact_min_magnitude=em["min_magnitude"],predicted_min_magnitude=pm["min_magnitude"],
            exact_phase_valid=em["phase_valid"],predicted_phase_valid=pm["phase_valid"],
            separation_error=abs(pm["separation_degrees"]-em["separation_degrees"]) if pm["phase_valid"] and em["phase_valid"] else None,
            complex_R_error=max(abs(p-e) for p,e in zip(pred,exact))))
    write_csv(out/"interpolation_pairs.csv",pairs)
    return pairs,infer


def timing(model,plan,interpolator):
    designs=[r for r in plan["designs"] if r["split"].startswith("test")]
    def net_infer(items):
        d=torch.tensor([r["d"] for r in items]*2)
        state=torch.tensor([0.]*len(items)+[1.]*len(items))
        with torch.no_grad():
            value=model.values(torch.zeros_like(d),d,state)
        current=torch.complex(value[:,2],value[:,3])
        a=torch.tensor([r["a"] for r in items]*2)
        return torch.exp(-2*CFG.gamma*a)*(1-current)
    def conventional(items):
        return [[response(r["length"],r["switch_fraction"],s)[0] for s in (0,1)] for r in items]
    result={}
    for label,fn in (("neural",net_infer),("conventional",conventional),("interpolation",interpolator)):
        for kind,items,repetitions in (("single",designs[:1],100),("batch",designs,5)):
            fn(items)
            times=[]
            for _ in range(9):
                start=time.perf_counter()
                for _ in range(repetitions):fn(items)
                times.append((time.perf_counter()-start)/(repetitions*len(items)))
            result[f"{label}_{kind}_seconds_per_two_state_query"]=statistics.median(times)
    return result


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--freeze-only",action="store_true")
    parser.add_argument("--evaluate-only",action="store_true")
    parser.add_argument("--variant",choices=("pinn","supervised"))
    parser.add_argument("--seed",type=int)
    parser.add_argument("--output",type=Path,default=ROOT/"outputs/switched-surrogate")
    args=parser.parse_args()
    torch.set_num_threads(1)
    plan=freeze(args.output)
    print(json.dumps(dict(frozen_protocol_sha256=hashlib.sha256((args.output/"frozen-protocol.json").read_bytes()).hexdigest(),
                          counts={s:sum(r["split"]==s for r in plan["designs"]) for s in ("train","validation","test_offgrid","test_blocked")})),flush=True)
    if args.freeze_only:return
    for mode in ([args.variant] if args.variant else plan["variants"]):
        for seed in ([args.seed] if args.seed is not None else plan["seeds"]):
            model,payload=load(args.output,mode,seed) if args.evaluate_only else train(args.output,plan,mode,seed)
            evaluate(args.output,plan,model,payload)
            print(json.dumps(dict(run=f"{mode}_seed-{seed}",status="completed",training_seconds=payload["training_seconds"])),flush=True)


if __name__=="__main__":main()

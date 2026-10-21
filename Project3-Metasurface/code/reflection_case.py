"""Synthetic two-state reflection check motivated by the interview phase objective.

The terminal states are ideal Dirichlet/Neumann boundaries, not a device model.
Time convention exp(-i omega t); incident wave amplitude is one.
"""
import cmath
import functools
import json
import math
import time
from pathlib import Path
import torch
from controlled_study import jets,train
from helmholtz import Network,relative_l2,write_csv


def exact_field(x,k,state):
    sign={"dirichlet":-1,"neumann":1}[state]
    return cmath.exp(1j*k*x)+sign*cmath.exp(2j*k)*cmath.exp(-1j*k*x)


def finite_difference(k,n,state):
    if k<=0 or n<4 or k/n>=1 or state not in ("dirichlet","neumann"):
        raise ValueError("Invalid reflection case")
    h=1/n
    size=n if state=="dirichlet" else n+1
    diagonal=[complex(-2+(k*h)**2)]*size
    upper=[1.0]*size
    lower=[1.0]*size
    diagonal[0]+=2j*k*h
    upper[0]=2.0
    if state=="neumann":
        lower[-1]=2.0
    rhs=[4j*k*h]+[0j]*(size-1)
    for i in range(1,size):
        factor=lower[i]/diagonal[i-1]
        diagonal[i]-=factor*upper[i-1]
        rhs[i]-=factor*rhs[i-1]
    solution=[0j]*size
    solution[-1]=rhs[-1]/diagonal[-1]
    for i in range(size-2,-1,-1):
        solution[i]=(rhs[i]-upper[i]*solution[i+1])/diagonal[i]
    if state=="dirichlet":
        solution.append(0j)
    return [j/n for j in range(n+1)],solution


def losses(p,k,x,mode="pinn",pde_weight=1,state="dirichlet"):
    u,_,uxx=jets(p,x)
    pde=((uxx+k*k*u)/max(1,k*k)).square().sum(1).mean()
    left,dx,_=jets(p,torch.tensor([0.0]))
    # u'(0)+ik u(0)=2ik, real/imag components.
    incoming=torch.stack((dx[0,0]-k*left[0,1],dx[0,1]+k*left[0,0]-2*k))
    incoming=(incoming/max(1,k)).square().sum()
    right,derivative,_=jets(p,torch.tensor([1.0]))
    boundary=right.square().sum() if state=="dirichlet" else (derivative/max(1,k)).square().sum()
    sign=-1 if state=="dirichlet" else 1
    ref_real=torch.cos(k*x)+sign*torch.cos(2*k-k*x)
    ref_imag=torch.sin(k*x)+sign*torch.sin(2*k-k*x)
    data=(u-torch.stack((ref_real,ref_imag),1)).square().sum(1).mean()
    terms=dict(pde=pde,dirichlet=incoming,outgoing=boundary,data=data)
    objective=data if mode=="supervised" else pde_weight*pde+incoming+boundary
    return objective,terms


def phase_error(predicted,reference):
    if abs(predicted)<1e-8:
        return None
    return math.degrees(cmath.phase(predicted/reference))


def run(output=None):
    torch.set_num_threads(1)
    out=Path(output) if output else Path(__file__).resolve().parents[1]/"outputs/reflection"
    out.mkdir(parents=True,exist_ok=True)
    baseline=[]
    for k in (1,5,10,20):
        for state in ("dirichlet","neumann"):
            for n in (128,256,512,1024):
                durations=[]
                for _ in range(7):
                    t=time.perf_counter()
                    x,u=finite_difference(k,n,state)
                    durations.append(time.perf_counter()-t)
                reference=[exact_field(a,k,state) for a in x]
                sign=-1 if state=="dirichlet" else 1
                r=u[0]-1
                baseline.append(dict(k=k,state=state,intervals=n,
                    relative_l2=relative_l2(u,reference),reflection_phase_error_degrees=phase_error(r,sign*cmath.exp(2j*k)),
                    median_solve_seconds=sorted(durations)[3]))
    write_csv(out/"baseline-refinement.csv",baseline)
    summary=[]
    if (out/"summary.csv").exists():
        import csv
        with (out/"summary.csv").open(newline="",encoding="utf-8") as file:
            summary=list(csv.DictReader(file))
    k=10.0
    pairs={}
    for variant,mode,lbfgs in (("pinn","pinn",False),("supervised","supervised",False),
                              ("adam_then_lbfgs","pinn",True),("adam_equal_evaluations","pinn",False)):
        for seed in (0,1,2):
            responses={}
            for state in ("dirichlet","neumann"):
                existing=next((r for r in summary if r["variant"]==variant and int(r["seed"])==seed and r["state"]==state),None)
                if existing:
                    responses[state]=complex(float(existing["reflection_real"]),float(existing["reflection_imag"]))
                    continue
                steps=3000
                if variant=="adam_equal_evaluations":
                    previous=next(r for r in summary if r["variant"]=="adam_then_lbfgs" and int(r["seed"])==seed and r["state"]==state)
                    steps=int(previous["gradient_evaluations"])
                loss_fn=functools.partial(losses,state=state)
                p,history,seconds,_,evaluations=train(k,seed,steps,64,mode=mode,
                                                   lbfgs=lbfgs,loss_function=loss_fn)
                grid=torch.linspace(0,1,1025)
                u,_,_=jets(p,grid)
                values=[complex(*a) for a in u.tolist()]
                reference=[exact_field(float(x),k,state) for x in grid]
                r=values[0]-1
                responses[state]=r
                sign=-1 if state=="dirichlet" else 1
                prefix=f"{variant}_seed-{seed}_{state}"
                write_csv(out/f"{prefix}_loss.csv",history)
                write_csv(out/f"{prefix}_field.csv",[dict(x=float(x),exact_real=e.real,
                    exact_imag=e.imag,predicted_real=v.real,predicted_imag=v.imag,abs_error=abs(v-e))
                    for x,e,v in zip(grid,reference,values)])
                (out/f"{prefix}_parameters.json").write_text(json.dumps(dict(width=24,parameters=p.tolist())),encoding="utf-8")
                row=dict(variant=variant,seed=seed,state=state,k=k,relative_l2=relative_l2(values,reference),
                    reflection_real=r.real,reflection_imag=r.imag,
                    reflection_magnitude=abs(r),reflection_phase_error_degrees=phase_error(r,sign*cmath.exp(2j*k)),
                    training_seconds=seconds,gradient_evaluations=evaluations)
                summary.append(row)
                write_csv(out/"summary.csv",summary)
                print(json.dumps(row),flush=True)
            difference=cmath.phase(responses["dirichlet"]/responses["neumann"])
            # Distance on the unit circle from the ideal pi separation.
            flip_error=abs(math.degrees(cmath.phase(cmath.exp(1j*(difference-math.pi)))))
            pairs[f"{variant}_seed-{seed}"]=dict(variant=variant,seed=seed,
                phase_separation_degrees=math.degrees(difference),
                phase_flip_error_degrees=flip_error,
                min_reflection_magnitude=min(map(abs,responses.values())))
    write_csv(out/"phase-flip-summary.csv",list(pairs.values()))
    (out/"run-config.json").write_text(json.dumps(dict(k=10,seeds=[0,1,2],
        states=["ideal Dirichlet reflector","ideal Neumann reflector"],
        architecture="1-24-2 tanh",collocation_points=64,adam_steps=3000,
        extension="same LBFGS settings as controlled_study.py",
        purpose="relevance check for reflection magnitude/phase, no claimed model of the physical unit cell",
        loss_column_mapping="dirichlet means incoming-wave boundary; outgoing means terminal-state boundary; both labels retained for shared trainer compatibility"),indent=2),encoding="utf-8")


if __name__=="__main__":
    import argparse
    parser=argparse.ArgumentParser()
    parser.add_argument("--output")
    args=parser.parse_args()
    run(args.output)

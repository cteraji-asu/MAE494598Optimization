"""Controlled continuation of the verified 98-parameter Helmholtz pilot.

PyTorch vectorizes the exact same tanh model/loss, enabling budget and
sampling controls. All runs retain separate loss components and costs.
"""
import argparse
import csv
import functools
import json
import math
import platform
import random
import time
from pathlib import Path
import torch
from helmholtz import Network, exact, relative_l2, spectrum, write_csv

torch.set_default_dtype(torch.float64)


def jets(p, x, width=24):
    w,b=p[:width],p[width:2*width]
    a=p[2*width:4*width].reshape(2,width)
    t=torch.tanh(x.reshape(-1,1)*w+b)
    t1=1-t*t
    t2=-2*t*t1
    return t@a.T+p[4*width:4*width+2],(t1*w)@a.T,(t2*w*w)@a.T


def losses(p,k,x,mode="pinn",pde_weight=1.0,raw_scaling=False):
    u,_,uxx=jets(p,x)
    physics=((uxx+k*k*u)/(1 if raw_scaling else max(1,k*k))).square().sum(1).mean()
    left=jets(p,torch.tensor([0.0]))[0][0]-torch.tensor([1.0,0.0])
    dirichlet=left.square().sum()
    right,derivative,_=jets(p,torch.tensor([1.0]))
    outgoing=torch.stack((derivative[0,0]+k*right[0,1],derivative[0,1]-k*right[0,0]))
    outgoing=(outgoing/(1 if raw_scaling else max(1,k))).square().sum()
    data=(u-torch.stack((torch.cos(k*x),torch.sin(k*x)),1)).square().sum(1).mean()
    terms=dict(pde=physics,dirichlet=dirichlet,outgoing=outgoing,data=data)
    objective=data if mode=="supervised" else pde_weight*physics+dirichlet+outgoing
    return objective,terms


def train(k,seed,steps,count,mode="pinn",pde_weight=1,lbfgs=False,loss_function=losses,raw_scaling=False):
    if raw_scaling:
        if loss_function is not losses:
            raise ValueError("Raw scaling is defined only for the traveling-wave study")
        loss_function=functools.partial(losses,raw_scaling=True)
    p=torch.nn.Parameter(torch.tensor(Network(24,seed).p))
    rng=random.Random(seed+91001)
    x=torch.tensor(sorted(rng.random() for _ in range(count)))
    opt=torch.optim.Adam([p],lr=0.003)
    history=[]
    started=time.perf_counter()
    evaluations=0
    for step in range(steps+1):
        opt.zero_grad()
        objective,terms=loss_function(p,k,x,mode,pde_weight)
        if step%100==0 or step==steps:
            history.append(dict(evaluation=evaluations,adam_updates=step,
                phase="adam",objective=float(objective.detach()),
                **{a:float(b.detach()) for a,b in terms.items()}))
        if step==steps:
            break
        objective.backward()
        evaluations+=1
        opt.step()
    adam_seconds=time.perf_counter()-started
    if lbfgs:
        solver=torch.optim.LBFGS([p],lr=1,max_iter=1000,max_eval=1500,
            tolerance_grad=1e-9,tolerance_change=1e-12,history_size=50,
            line_search_fn="strong_wolfe")
        def closure():
            nonlocal evaluations
            solver.zero_grad()
            objective,terms=loss_function(p,k,x,mode,pde_weight)
            objective.backward()
            evaluations+=1
            if (evaluations-steps)%10==0:
                history.append(dict(evaluation=evaluations,adam_updates=steps,
                    phase="lbfgs",objective=float(objective.detach()),
                    **{a:float(b.detach()) for a,b in terms.items()}))
            return objective
        solver.step(closure)
        objective,terms=loss_function(p,k,x,mode,pde_weight)
        history.append(dict(evaluation=evaluations,adam_updates=steps,
                    phase="lbfgs_final",objective=float(objective.detach()),
                    **{a:float(b.detach()) for a,b in terms.items()}))
    seconds=time.perf_counter()-started
    return p.detach(),history,seconds,adam_seconds,evaluations


def run(out,only=None):
    out.mkdir(parents=True,exist_ok=True)
    k=10.0
    experiments=[
        dict(name="matched_pinn",steps=3000,count=64),
        dict(name="longer_pinn",steps=12000,count=64),
        dict(name="longer6000_pinn",steps=6000,count=64),
        dict(name="denser_pinn",steps=3000,count=256),
        dict(name="denser128_pinn",steps=3000,count=128),
        dict(name="pde_weight_0.1",steps=3000,count=64,pde_weight=0.1),
        dict(name="pde_weight_10",steps=3000,count=64,pde_weight=10),
        dict(name="raw_residuals",steps=3000,count=64,raw_scaling=True),
        dict(name="longer_supervised",steps=12000,count=64,mode="supervised"),
        dict(name="adam_then_lbfgs",steps=3000,count=64,lbfgs=True),
    ]
    summaries=[]
    if (out/"summary.csv").exists():
        with (out/"summary.csv").open(newline="",encoding="utf-8") as file:
            summaries=list(csv.DictReader(file))
    grid=torch.linspace(0,1,1025)
    reference=[exact(float(x),k) for x in grid]
    for config in experiments:
        if only and config["name"] not in only:
            continue
        for seed in (0,1,2):
            if any(r["experiment"]==config["name"] and int(r["seed"])==seed for r in summaries):
                continue
            options={a:b for a,b in config.items() if a!="name"}
            p,history,seconds,adam_seconds,evaluations=train(k,seed,**options)
            u,_,uxx=jets(p,grid)
            predictions=[complex(*r) for r in u.tolist()]
            residual=uxx+k*k*u
            heldout_pde=float((residual/max(1,k*k)).square().sum(1).mean())
            prefix=f"{config['name']}_seed-{seed}"
            net=Network(24,seed)
            net.p=p.tolist()
            write_csv(out/f"{prefix}_loss.csv",history)
            write_csv(out/f"{prefix}_field.csv",[dict(x=float(x),exact_real=e.real,
                exact_imag=e.imag,predicted_real=v.real,predicted_imag=v.imag,abs_error=abs(v-e))
                for x,e,v in zip(grid,reference,predictions)])
            write_csv(out/f"{prefix}_spectrum.csv",spectrum([
                net.value(j/256)-exact(j/256,k) for j in range(256)]))
            (out/f"{prefix}_parameters.json").write_text(json.dumps(dict(width=24,parameters=net.p)),encoding="utf-8")
            row=dict(experiment=config["name"],seed=seed,k=k,steps=config["steps"],
                collocation_points=config["count"],pde_weight=config.get("pde_weight",1),
                mode=config.get("mode","pinn"),relative_l2=relative_l2(predictions,reference),
                training_seconds=seconds,adam_seconds=adam_seconds,
                gradient_evaluations=evaluations,heldout_pde=heldout_pde,
                **{f"final_{a}":b for a,b in history[-1].items() if a in
                   ("objective","pde","dirichlet","outgoing","data")})
            summaries.append(row)
            write_csv(out/"summary.csv",summaries)
            print(json.dumps(row),flush=True)
    (out/"run-config.json").write_text(json.dumps(dict(
        k=k,seeds=[0,1,2],architecture="1-24-2 tanh, 98 parameters, float64",
        learning_rate=0.003,experiments=experiments,torch=torch.__version__,
        python=platform.python_version(),threads=torch.get_num_threads(),
        inference="not compared across implementations; pilot P5 retained",
        comparison="same seeds and initializations as pilot; objective/scaling match independently checked",
        lbfgs="after 3000 Adam updates; max_iter=1000 max_eval=1500 history=50 strong_wolfe grad_tol=1e-9 change_tol=1e-12"),indent=2),encoding="utf-8")


if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--output",default="outputs/controlled")
    parser.add_argument("--only",nargs="+")
    args=parser.parse_args()
    torch.set_num_threads(1)
    run(Path(args.output),args.only)

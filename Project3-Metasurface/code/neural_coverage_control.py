"""One bounded paired neural coverage intervention after the primary study.

Freeze a fresh geometry-only evaluation set before fitting three new PINNs.
Keep 256 training designs, architecture, seeds, sampler and 4000-update budget.
Replace the same 16 evenly selected nodes as the interpolation control.
Evaluate both the original saved models and new models on the fresh set.
"""
import copy
import hashlib
import json
from pathlib import Path
import random
import numpy as np
import torch
from switched_surrogate import evaluate,load,train
from switched_line import write_csv
from summarize_switched_surrogate import classification,read

ROOT=Path(__file__).resolve().parents[1]
PRIMARY=ROOT/"outputs/switched-surrogate"
OUT=ROOT/"outputs/neural-coverage-control"


def freeze_control():
    OUT.mkdir(parents=True,exist_ok=True)
    path=OUT/"frozen-control.json"
    if path.exists():return json.loads(path.read_text())
    primary=json.loads((PRIMARY/"frozen-protocol.json").read_text())
    training=[r for r in primary["designs"] if r["split"]=="train"]
    revised=copy.deepcopy(training)
    order=np.argsort([r["d"] for r in training])
    selected=[int(order[i]) for i in np.linspace(0,255,16,dtype=int)]
    for index,d in zip(selected,np.linspace(.195,.222,18)[1:-1]):
        d=float(d);low,high=max(.30,d/.85),min(.42,d/.1)
        length=(low+high)/2
        revised[index]=dict(id=training[index]["id"],split="train",d=d,
                            length=length,switch_fraction=1-d/length,a=length-d)
    # Separate from every prior geometry and new training geometry. No use of
    # any response label, predicted error or feasibility status in construction.
    used=[r["d"] for r in primary["designs"]]+[r["d"] for r in revised]
    rng=random.Random(49420261021)
    fresh=[]
    for split,count in (("test_offgrid",224),("test_blocked",256)):
        made=0
        while made<count:
            d=rng.uniform(*((.195,.222) if split=="test_blocked" else (.03,.357)))
            if split=="test_offgrid" and .195<=d<=.222:continue
            if min(abs(d-v) for v in used)<2e-5:continue
            low,high=max(.30,d/.85),min(.42,d/.1)
            if low>=high:continue
            length=rng.uniform(low,high)
            fresh.append(dict(id=f"fresh-{split}-{made:04d}",split=split,d=d,
                              length=length,switch_fraction=1-d/length,a=length-d))
            used.append(d);made+=1
    arms={}
    for name,designs in (("original",training),("reallocated",revised)):
        plan=copy.deepcopy(primary)
        plan["designs"]=designs+fresh
        plan["status"]="Follow-up paired coverage control, fresh geometry-only evaluation frozen before fitting"
        plan["source_sha256"]=hashlib.sha256((ROOT/"code/switched_surrogate.py").read_bytes()).hexdigest()
        arms[name]=plan
        destination=OUT/name
        destination.mkdir(parents=True,exist_ok=True)
        (destination/"frozen-protocol.json").write_text(json.dumps(plan,indent=2),encoding="utf-8")
    control=dict(status="One planned follow-up after primary study, not a replacement of primary scores",
        hypothesis="Covering the blocked response region improves PINN screening and errors under the same training budget",
        no_tuning="Architecture, objective, scaling, optimizer, steps and seeds unchanged; no stopping or further sweep based on fresh scores",
        design_rule="Replace16evenlyindexed sorted training nodes with16equallyspaced interior block nodes",
        primary_protocol_sha256=hashlib.sha256((PRIMARY/"frozen-protocol.json").read_bytes()).hexdigest(),
        primary_source_hash_retained=primary["source_sha256"],
        fresh_seed=49420261021,fresh_counts=dict(test_offgrid=224,test_blocked=256),
        fresh_separation_from_all_prior_and_new_train_d=2e-5,
        scope="Both arms256traininggeometries, pairedstates; originalsavedmodelsreused; three newPINNfits only",
        changed_training_indices=selected,arms=arms)
    path.write_text(json.dumps(control,indent=2),encoding="utf-8")
    return control


def main():
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument("--freeze-only",action="store_true")
    args=parser.parse_args();torch.set_num_threads(1)
    control=freeze_control()
    print(json.dumps(dict(control_sha256=hashlib.sha256((OUT/"frozen-control.json").read_bytes()).hexdigest(),
                          fresh_counts=control["fresh_counts"])),flush=True)
    if args.freeze_only:return
    for seed in (0,1,2):
        checkpoint=OUT/"reallocated"/f"pinn_seed-{seed}_weights.json"
        if checkpoint.exists():
            model,payload=load(OUT/"reallocated","pinn",seed)
            expected=hashlib.sha256((OUT/"reallocated/frozen-protocol.json").read_bytes()).hexdigest()
            assert payload["protocol_sha256"]==expected,"Saved run belongs to a different frozen control"
        else:
            model,payload=train(OUT/"reallocated",control["arms"]["reallocated"],"pinn",seed)
        evaluate(OUT/"reallocated",control["arms"]["reallocated"],model,payload)
        original,original_payload=load(PRIMARY,"pinn",seed)
        evaluate(OUT/"original",control["arms"]["original"],original,original_payload)
    metrics=[];errors=[]
    for arm in ("original","reallocated"):
        for seed in (0,1,2):
            pairs=read(OUT/arm/f"pinn_seed-{seed}_pairs.csv")
            states=read(OUT/arm/f"pinn_seed-{seed}_states.csv")
            for split in ("test_offgrid","test_blocked"):
                rows=[r for r in pairs if r["split"]==split]
                sr=[r for r in states if r["split"]==split]
                metrics.append(dict(arm=arm,seed=seed,split=split,
                                    phase_tolerance=15,magnitude_floor=.8,**classification(rows,15,.8)))
                errors.append(dict(arm=arm,seed=seed,split=split,
                    median_complex_R_error=float(np.median([r["complex_R_error"] for r in rows])),
                    median_separation_error=float(np.median([r["separation_error"] for r in rows if r["separation_error"] is not None])),
                    median_voltage_relative_L2=float(np.median([r["voltage_relative_L2"] for r in sr])),
                    median_current_relative_L2=float(np.median([r["current_relative_L2"] for r in sr])),
                    p95_complex_R_error=float(np.quantile([r["complex_R_error"] for r in rows],.95))))
    write_csv(OUT/"decision-metrics.csv",metrics);write_csv(OUT/"errors.csv",errors)
    (OUT/"overview.json").write_text(json.dumps(dict(decisions=metrics,errors=errors,
        control_sha256=hashlib.sha256((OUT/"frozen-control.json").read_bytes()).hexdigest(),
        note="Fresh follow-up evaluation; primary results retained; no further neural tuning"),indent=2),encoding="utf-8")
    print(json.dumps(dict(decisions=metrics,errors=errors),indent=2),flush=True)


if __name__=="__main__":main()

"""Exploratory, post-test coverage diagnosis for cheap interpolation only.

Same 256 geometry nodes and 512 state responses. Replace 16 evenly selected
training nodes with 16 equally spaced locations inside the withheld interval.
The original neural protocol, models and primary test results remain fixed.
"""
import json
from pathlib import Path
import time
import numpy as np
from switched_line import Config,phase_metrics,write_csv
from switched_surrogate import classification

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"outputs/switched-surrogate"


def main():
    config=Config()
    plan=json.loads((OUT/"frozen-protocol.json").read_text())
    nodes=np.array(sorted(r["d"] for r in plan["designs"] if r["split"]=="train"))
    removed=np.linspace(0,len(nodes)-1,16,dtype=int)
    added=np.linspace(*plan["blocked_d_interval"],18)[1:-1]
    changed=np.sort(np.concatenate((np.delete(nodes,removed),added)))
    assert len(nodes)==len(changed)==256
    z=np.array([config.z_on,config.z_off])[:,None]
    cases={"original_gap":nodes,"redistributed_coverage":changed}
    decisions,comparison=[],{}
    for name,d in cases.items():
        begin=time.perf_counter()
        t=np.tanh(config.gamma*d)
        samples=(z+t-1)/(z+t+1)
        setup=time.perf_counter()-begin
        for split in ("test_offgrid","test_blocked"):
            designs=[r for r in plan["designs"] if r["split"]==split]
            target=np.array([r["d"] for r in designs])
            upstream=np.exp(-2*config.gamma*np.array([r["a"] for r in designs]))
            pred=np.array([np.interp(target,d,row.real)+1j*np.interp(target,d,row.imag) for row in samples])*upstream
            tt=np.tanh(config.gamma*target)
            exact=(z+tt-1)/(z+tt+1)*upstream
            pairs=[]
            for j,r in enumerate(designs):
                pm,em=phase_metrics(*pred[:,j]),phase_metrics(*exact[:,j])
                pairs.append(dict(id=r["id"],split=split,
                    exact_phase_valid=em["phase_valid"],predicted_phase_valid=pm["phase_valid"],
                    exact_separation=em["separation_degrees"],predicted_separation=pm["separation_degrees"],
                    exact_min_magnitude=em["min_magnitude"],predicted_min_magnitude=pm["min_magnitude"]))
            decisions.append(dict(control=name,split=split,nodes=len(d),state_response_labels=2*len(d),
                                  reference_generation_seconds=setup,**classification(pairs,15,.8)))
        comparison[name]=d.tolist()
    write_csv(OUT/"coverage-control.csv",decisions)
    result=dict(status="Exploratory diagnostic designed after primary test inspection",
        scope="Interpolation only; no neural remedy claim, no change to frozen six-run study",
        rule="Replace 16 evenly indexed original nodes with 16 equally spaced interior block nodes; same total node/label counts",
        inference="Tests coverage allocation as a cause of this interpolation failure; does not prove sole PINN root cause",
        thresholds="Illustrative phase tolerance 15 degrees, magnitude floor .8",
        nodes=comparison,results=decisions)
    (OUT/"coverage-control.json").write_text(json.dumps(result,indent=2),encoding="utf-8")
    print(json.dumps(decisions,indent=2))


if __name__=="__main__":main()

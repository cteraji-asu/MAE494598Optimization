"""Summarize the frozen six-run switched-line comparison without retraining."""
import csv
import hashlib
import json
from pathlib import Path
import statistics
import time
import numpy as np
import torch
from switched_surrogate import classification,interpolation,load,timing
from switched_line import Config,response,write_csv

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"outputs/switched-surrogate"


def read(path):
    with path.open(newline="",encoding="utf-8") as f:
        result=list(csv.DictReader(f))
    for row in result:
        for key,value in row.items():
            if value in ("True","False"):row[key]=value=="True"
            elif value=="":row[key]=None
            else:
                try:row[key]=float(value)
                except ValueError:pass
    return result


def analytic_factorized(designs):
    config=Config()
    d=np.array([r["d"] for r in designs])
    a=np.array([r["a"] for r in designs])
    z=np.array([config.z_on,config.z_off])[:,None]
    t=np.tanh(config.gamma*d)
    return np.exp(-2*config.gamma*a)*(z+t-1)/(z+t+1)


def analytic_timing(plan):
    designs=[r for r in plan["designs"] if r["split"].startswith("test")]
    result={}
    for kind,items,repetitions in (("single",designs[:1],100),("batch",designs,5)):
        analytic_factorized(items)
        times=[]
        for _ in range(9):
            begin=time.perf_counter()
            for _ in range(repetitions):analytic_factorized(items)
            times.append((time.perf_counter()-begin)/(repetitions*len(items)))
        result[f"analytic_factorized_{kind}_seconds_per_two_state_query"]=statistics.median(times)
    return result


def main():
    torch.set_num_threads(1)
    plan=json.loads((OUT/"frozen-protocol.json").read_text())
    begin=time.perf_counter()
    interpolation_pairs,interpolator=interpolation(OUT,plan)
    interpolation_setup=time.perf_counter()-begin
    summaries,decisions,costs=[],[],[]
    for mode in ("pinn","supervised","interpolation"):
        for seed in (plan["seeds"] if mode!="interpolation" else [-1]):
            if mode!="interpolation":
                model,payload=load(OUT,mode,seed)
                pairs=read(OUT/f"{mode}_seed-{seed}_pairs.csv")
                states=read(OUT/f"{mode}_seed-{seed}_states.csv")
                measures=timing(model,plan,interpolator)
                measures.update(analytic_timing(plan))
                for query_kind in ("single","batch"):
                    conventional=min(measures[f"conventional_{query_kind}_seconds_per_two_state_query"],
                                     measures[f"analytic_factorized_{query_kind}_seconds_per_two_state_query"])
                    inference=measures[f"neural_{query_kind}_seconds_per_two_state_query"]
                    measures[f"{query_kind}_break_even_queries"]=(payload["training_seconds"]/(conventional-inference)
                                                                  if conventional>inference else None)
                costs.append(dict(mode=mode,seed=seed,training_seconds=payload["training_seconds"],
                    included_reference_generation_seconds=payload["included_reference_generation_seconds"],
                    **measures))
            else:
                pairs=interpolation_pairs;states=[]
            for split in ("validation","test_offgrid","test_blocked"):
                subset=[r for r in pairs if r["split"]==split]
                sr=[r for r in states if r["split"]==split]
                phase=[r["separation_error"] for r in subset if r["separation_error"] is not None]
                summary=dict(mode=mode,seed=seed,split=split,designs=len(subset),
                    median_max_state_complex_R_error=statistics.median(r["complex_R_error"] for r in subset),
                    p95_max_state_complex_R_error=float(np.quantile([r["complex_R_error"] for r in subset],.95)),
                    median_separation_error_degrees=statistics.median(phase) if phase else None,
                    p95_separation_error_degrees=float(np.quantile(phase,.95)) if phase else None,
                    valid_phase_predictions=len(phase),
                    median_voltage_relative_L2=statistics.median(r["voltage_relative_L2"] for r in sr) if sr else None,
                    median_current_relative_L2=statistics.median(r["current_relative_L2"] for r in sr) if sr else None,
                    max_extraction_disagreement=max((r["reflection_extraction_disagreement"] for r in sr),default=None),
                    passivity_violating_states=sum(r["predicted_magnitude"]>1+1e-8 for r in sr) if sr else None,
                    max_predicted_magnitude=max((r["predicted_magnitude"] for r in sr),default=None),
                    median_abs_power_balance_defect=statistics.median(abs(r["power_balance_defect"]) for r in sr) if sr else None,
                    max_abs_power_balance_defect=max((abs(r["power_balance_defect"]) for r in sr),default=None),
                    median_pde_voltage_rms=statistics.median(r["pde_voltage_rms"] for r in sr) if sr else None,
                    median_pde_current_rms=statistics.median(r["pde_current_rms"] for r in sr) if sr else None,
                    median_driven_interface_abs=statistics.median(r["driven_interface_abs"] for r in sr) if sr else None,
                    median_terminal_voltage_abs=statistics.median(r["terminal_voltage_abs"] for r in sr) if sr else None)
                summaries.append(summary)
                for tolerance in plan["illustrative_phase_tolerances"]:
                    for floor in plan["illustrative_magnitude_floors"]:
                        for region in ("all","near_boundary"):
                            selected=subset
                            if region=="near_boundary":
                                selected=[r for r in subset if
                                    abs((180-r["exact_separation"])-tolerance)<=plan["near_boundary_phase_margin_degrees"]
                                    or abs(r["exact_min_magnitude"]-floor)<=plan["near_boundary_magnitude_margin"]]
                            decisions.append(dict(mode=mode,seed=seed,split=split,region=region,
                                phase_tolerance=tolerance,magnitude_floor=floor,designs=len(selected),
                                **classification(selected,tolerance,floor)))
    write_csv(OUT/"summary.csv",summaries)
    write_csv(OUT/"decision-metrics.csv",decisions)
    write_csv(OUT/"costs.csv",costs)
    counts={split:classification([r for r in interpolation_pairs if r["split"]==split],15,.8)
            for split in ("validation","test_offgrid","test_blocked")}
    # Counts are from the exact responses; interpolation classifications are
    # retained separately in decision-metrics.csv.
    exact_counts={k:{key:v for key,v in row.items() if key in ("actual_feasible","actual_infeasible")}
                  for k,row in counts.items()}
    analytic_disagreement=max(abs(analytic_factorized([r])[s,0]-response(r["length"],r["switch_fraction"],s)[0])
                              for r in plan["designs"] for s in (0,1))
    overview=dict(protocol_sha256=hashlib.sha256((OUT/"frozen-protocol.json").read_bytes()).hexdigest(),
        max_factorized_vs_ABCD_disagreement=analytic_disagreement,
        interpolation_reference_setup_and_all_evaluation_seconds=interpolation_setup,
        exact_class_counts=exact_counts,
        primary_decisions=[r for r in decisions if r["phase_tolerance"]==15 and r["magnitude_floor"]==.8 and r["region"]=="all"],
        result_rows=summaries,costs=costs,
        notes=["All thresholds illustrative; phase goal comes from interview",
               "No clipping of reflection or phase before metrics",
               "Phase mask coverage reported; masked prediction counts as infeasible",
               "PINN and supervised budgets fixed before testing; no remedy experiment or post-test tuning",
               "Interpolate complex local R versus d, then exact upstream factor; endpoint extrapolation is constant",
               "Primary family effectively one-dimensional for phase; not full metasurface geometry",
               "Training wall time already includes timed on-demand reference generation",
               "Interpolation setup timing includes references plus evaluation of all 480 non-training designs"])
    (OUT/"overview.json").write_text(json.dumps(overview,indent=2),encoding="utf-8")
    print(json.dumps(dict(exact_class_counts=exact_counts,primary_decisions=overview["primary_decisions"],costs=costs),indent=2))


if __name__=="__main__":main()

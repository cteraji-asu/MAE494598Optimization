"""Verify saved fields, add held-out residual diagnostics and summarize controls."""
import cmath
import csv
import json
import math
import statistics
from pathlib import Path
from helmholtz import Network,spectrum,write_csv

ROOT=Path(__file__).resolve().parents[1]


def read(path):
    with (ROOT/path).open(newline="",encoding="utf-8") as file:
        return list(csv.DictReader(file))


def check_field(path,k,state=None):
    rows=read(path)
    error=[]
    reference=[]
    for j,r in enumerate(rows):
        x=float(r["x"])
        target=cmath.exp(1j*k*x)
        if state:
            target+=(1 if state=="neumann" else -1)*cmath.exp(1j*(2*k-k*x))
        prediction=complex(float(r["predicted_real"]),float(r["predicted_imag"]))
        weight=.5 if j in (0,len(rows)-1) else 1
        error.append(weight*abs(prediction-target)**2)
        reference.append(weight*abs(target)**2)
    return math.sqrt(math.fsum(error)/math.fsum(reference))


def main():
    controls=read("outputs/controlled/summary.csv")
    reflection=read("outputs/reflection/summary.csv")
    assert len(controls)==30 and len(reflection)==24
    residuals=[]
    maximum_discrepancy=0
    for row in controls:
        name,seed=row["experiment"],int(row["seed"])
        prefix=f"outputs/controlled/{name}_seed-{seed}"
        actual=check_field(prefix+"_field.csv",10)
        maximum_discrepancy=max(maximum_discrepancy,abs(actual-float(row["relative_l2"])))
        model=json.loads((ROOT/(prefix+"_parameters.json")).read_text())
        net=Network(model["width"],0)
        net.p=model["parameters"]
        raw=[]
        for j in range(2048):
            u,_,uxx,_=net.jet((j+.5)/2048)
            raw.append(abs(complex(*uxx)+100*complex(*u))**2)
        raw_pde=math.fsum(raw)/2048
        train_normalized=float(row["final_pde"])/(10000 if name=="raw_residuals" else 1)
        train_raw=train_normalized*10000
        outgoing_raw=float(row["final_outgoing"])*(1 if name=="raw_residuals" else 100)
        residuals.append(dict(experiment=name,seed=seed,normalized_train_pde=train_normalized,
            normalized_heldout_pde_midpoint2048=raw_pde/10000,
            heldout_to_train_ratio=(raw_pde/10000)/train_normalized,
            raw_train_pde=train_raw,raw_heldout_pde_midpoint2048=raw_pde,
            raw_train_outgoing=outgoing_raw,dirichlet=float(row["final_dirichlet"])))
    for row in reflection:
        prefix=f"outputs/reflection/{row['variant']}_seed-{int(row['seed'])}_{row['state']}"
        actual=check_field(prefix+"_field.csv",10,row["state"])
        maximum_discrepancy=max(maximum_discrepancy,abs(actual-float(row["relative_l2"])))
    assert maximum_discrepancy<1e-12
    write_csv(ROOT/"outputs/controlled/heldout-residuals.csv",residuals)
    flips=read("outputs/reflection/phase-flip-summary.csv")
    titles={"matched_pinn":"Adam, 3,000 updates, 64 points",
      "longer6000_pinn":"Adam, 6,000 updates, 64 points",
      "longer_pinn":"Adam, 12,000 updates, 64 points",
      "denser128_pinn":"Adam, 3,000 updates, 128 points",
      "denser_pinn":"Adam, 3,000 updates, 256 points",
      "pde_weight_0.1":"Normalized PDE weight 0.1",
      "pde_weight_10":"Normalized PDE weight 10",
      "raw_residuals":"Raw PDE/outgoing residual losses",
      "longer_supervised":"Supervised, 12,000 updates",
      "adam_then_lbfgs":"Adam 3,000, then L-BFGS"}
    lines=["# Controlled study results", "",
      "All traveling-wave controls use k=10, 98 parameters, float64 and seeds 0/1/2. "
      "Each row changes the named factor from the matched baseline. Median and min/max "
      "are summaries of three seeds, not confidence intervals.", "",
      "| Experiment | Median L2 error | Range | Median gradient evaluations |",
      "|---|---:|---:|---:|"]
    for name,title in titles.items():
        group=[r for r in controls if r["experiment"]==name]
        values=[100*float(r["relative_l2"]) for r in group]
        lines.append(f"| {title} | {statistics.median(values):.3f}% | {min(values):.3f}-{max(values):.3f}% | "
                     f"{statistics.median(int(r['gradient_evaluations']) for r in group):g} |")
    lines += ["", "## Held-out physics residual", "",
      "The independent grid has 2,048 midpoint locations. Raw and normalized losses "
      "are both retained in `outputs/controlled/heldout-residuals.csv`. For k=10, "
      "normalization multiplies raw PDE squared residual by 1e-4 and raw outgoing "
      "squared residual by 1e-2. These are consequential optimization weights.", "",
      "| Baseline seed | Train normalized PDE MSE | Held-out normalized PDE MSE | Ratio |",
      "|---:|---:|---:|---:|"]
    for r in residuals:
        if r["experiment"]=="matched_pinn":
            lines.append(f"| {r['seed']} | {r['normalized_train_pde']:.6f} | "
                         f"{r['normalized_heldout_pde_midpoint2048']:.6f} | {r['heldout_to_train_ratio']:.3f} |")
    lines += ["", "Residual generalization is imperfect, particularly for seed 1. Increasing "
      "collocation alone to 128 or 256 points does not repair the large field error "
      "under 3,000 Adam updates. This weakens an explanation based solely on too few "
      "samples; it does not rule out sampling and optimization interactions. Longer "
      "training helps and losses remain in motion, so no convergence claim is made.", "",
      "Supervised fitting demonstrates that the same architecture can represent a "
      "much better field under a different objective. L-BFGS changes the optimization "
      "trajectory without adding frequencies or labels. These observations support a "
      "finite-budget optimization limitation. They do not uniquely distinguish loss "
      "conditioning, implicit spectral preference and nonconvex local geometry.", "",
      "## Reflection-phase extension", "",
      "At k=10, ideal Dirichlet and Neumann terminations define two synthetic states. "
      "Their exact reflection coefficients have unit magnitude and differ by 180 degrees. "
      "These are ideal boundary states, not geometry or switch models of the interviewed device.", "",
      "| Training | Median phase-flip error | Range across three seeds |",
      "|---|---:|---:|"]
    for variant,title in (("pinn","Adam 3,000"),("supervised","Supervised 3,000"),
             ("adam_equal_evaluations","Adam, matched gradient evaluations"),("adam_then_lbfgs","Adam then L-BFGS")):
        values=[float(r["phase_flip_error_degrees"]) for r in flips if r["variant"]==variant]
        lines.append(f"| {title} | {statistics.median(values):.3f} degrees | {min(values):.3f}-{max(values):.3f} degrees |")
    good=[float(r["reflection_magnitude"]) for r in reflection if r["variant"]=="adam_then_lbfgs"]
    lines += ["",f"After continuation, reflected magnitudes range from {min(good):.6f} to {max(good):.6f}, "
      "against the exact value 1. The corresponding Adam-only control uses exactly "
      "the same total gradient evaluation count for each seed/state pair. Its large "
      "phase error shows that extra evaluations alone do not explain this improvement. "
      "Wall-clock costs and optimizer overhead still differ, and neither result meets "
      "a researcher-provided tolerance because none was supplied.", "",
      "## Verification", "",
      f"All {len(controls)+len(reflection)} new saved-field relative errors were recomputed independently "
      f"from closed-form complex fields. Maximum discrepancy: {maximum_discrepancy:.3g}. "
      "The original 24 pilot errors have a separate independent check. All source fields, "
      "parameters and histories remain available.", ""]
    (ROOT/"study-results.md").write_text("\n".join(lines),encoding="utf-8")
    evidence=dict(controlled_runs=len(controls),reflection_runs=len(reflection),
        midpoint_residual_points=2048,maximum_saved_field_l2_discrepancy=maximum_discrepancy,
        gradient_budget_matching="each reflection Adam-only run matches its L-BFGS pair's actual total gradient evaluations",
        claim="finite-budget optimization limitation; no exclusive spectral-bias claim")
    (ROOT/"outputs/study-verification.json").write_text(json.dumps(evidence,indent=2),encoding="utf-8")
    print("\n".join(lines[:18]))


if __name__=="__main__":
    main()

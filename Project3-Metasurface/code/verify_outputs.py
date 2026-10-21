"""Recompute errors from saved fields without calling solver/error helper functions."""
import csv
import json
import math
import statistics
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "outputs" / "pilot"


def rows(name):
    with (DATA / name).open(newline="", encoding="utf-8") as file:
        return list(csv.DictReader(file))


def main():
    summary = rows("summary.csv")
    assert len(summary) == 24
    maximum_discrepancy = 0
    for run in summary:
        k, seed, mode = float(run["k"]), int(run["seed"]), run["mode"]
        field = rows(f"k-{k:g}_seed-{seed}_{mode}_field.csv")
        assert len(field) == 1025
        squared = []
        for j, point in enumerate(field):
            x = float(point["x"])
            real, imag = float(point["predicted_real"]), float(point["predicted_imag"])
            error2 = (real-math.cos(k*x))**2+(imag-math.sin(k*x))**2
            squared.append((0.5 if j in (0,1024) else 1)*error2)
        independent = math.sqrt(math.fsum(squared)/1024)
        discrepancy = abs(independent-float(run["relative_l2_exact"]))
        maximum_discrepancy = max(maximum_discrepancy, discrepancy)
        assert discrepancy < 1e-12
    lines = ["# Measured pilot results", "",
             "Synthetic homogeneous Helmholtz case, 3,000 updates. Errors are percentages.", "",
             "| k | PINN median | PINN range, 3 seeds | Supervised median | Supervised range, 3 seeds |",
             "|---:|---:|---:|---:|---:|"]
    for k in (1,5,10,20):
        modes = [[100*float(r["relative_l2_exact"]) for r in summary
                  if float(r["k"]) == k and r["mode"] == mode]
                 for mode in ("pinn","supervised")]
        a,b = modes
        lines.append(f"| {k} | {statistics.median(a):.4f}% | {min(a):.4f}-{max(a):.4f}% | "
                     f"{statistics.median(b):.4f}% | {min(b):.4f}-{max(b):.4f}% |")
    training = [float(r["training_seconds"]) for r in summary]
    inference = [float(r["inference_1025_points_seconds"])*1000 for r in summary]
    baseline = [r for r in rows("baseline-refinement.csv") if int(r["intervals"]) == 1024]
    lines += ["", f"Neural training took {min(training):.2f}-{max(training):.2f} seconds per run. "
              f"Median full-field inference took {min(inference):.2f}-{max(inference):.2f} ms across runs.", "",
              "The 1,024-interval finite-difference solver took about "
              f"{min(float(r['median_solve_seconds']) for r in baseline)*1000:.3f}-"
              f"{max(float(r['median_solve_seconds']) for r in baseline)*1000:.3f} ms. "
              "It is both more accurate and faster for this tiny synthetic forward problem. "
              "The timings compare these Python implementations, not full-wave lab solvers.", "",
              "At k=10 the supervised control reaches roughly 3-4% error while the PINN is "
              "above 80% in all seeds. This supports an objective/training difficulty at that "
              "accuracy, not a proof of spectral bias. At k=20 both modes have substantial "
              "error, so the same control cannot isolate representation from optimization.", "",
              "## Independent arithmetic check", "",
              "Recomputing all 24 field errors from CSV with cos/sin and an independent "
              f"trapezoidal sum agrees within {maximum_discrepancy:.2g}. No error helper "
              "from the training code is called by this check.", "",
              "For a hand-checkable PINN value, k=1, seed=0, use five equally spaced points:", "",
              "| x | Predicted real | Predicted imag | Squared complex error | Weight |",
              "|---:|---:|---:|---:|---:|"]
    selected = rows("k-1_seed-0_pinn_field.csv")
    terms=[]
    for j in (0,256,512,768,1024):
        r=selected[j]
        x=float(r["x"])
        re,im=float(r["predicted_real"]),float(r["predicted_imag"])
        e2=(re-math.cos(x))**2+(im-math.sin(x))**2
        w=0.5 if j in (0,1024) else 1
        terms.append(w*e2)
        lines.append(f"| {x:.2f} | {re:.10f} | {im:.10f} | {e2:.10g} | {w:g} |")
    manual=math.sqrt(sum(terms)/4)
    lines += ["", f"Because |exp(ix)|=1, the trapezoidal reference norm squared is 1. "
              f"The five-point relative error is sqrt[0.25 times the weighted error sum] "
              f"= {manual:.10g}, or {manual*100:.6f}%. The denser reported 1,025-point error "
              "uses the same norm with a finer quadrature; they need not be identical.", "",
              "Reproduce with `python code/verify_outputs.py`. All runs are preliminary. "
              "A k-dependent network retrained for every solve is not a geometry surrogate.", ""]
    (ROOT/"pilot-results.md").write_text("\n".join(lines),encoding="utf-8")
    (DATA/"output-verification.json").write_text(json.dumps(dict(
        verified_runs=len(summary), maximum_l2_discrepancy=maximum_discrepancy,
        manual_five_point_relative_l2=manual,
        checks="Independent exact cos/sin values and trapezoidal integration of saved fields"),indent=2),encoding="utf-8")
    print("\n".join(lines[:18]))


if __name__ == "__main__":
    main()

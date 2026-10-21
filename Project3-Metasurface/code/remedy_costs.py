"""Summarize measured remedy costs without running any training."""
import csv
import json
import statistics
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]


def main():
    with (ROOT/"outputs/controlled/summary.csv").open(newline="",encoding="utf-8") as file:
        rows=list(csv.DictReader(file))
    summaries={}
    lines=["### Measured before/after remedy cost", "",
        "These two rows use the same vectorized PyTorch implementation and k=10. "
        "They are separate from the original pure-Python pilot timings. All values "
        "summarize the same three seeds.", "",
        "| Training | Median field error | Median training time | Training-time range | Gradient evaluations |",
        "|---|---:|---:|---:|---:|"]
    for key,label in (("matched_pinn","Adam 3,000"),("adam_then_lbfgs","Adam 3,000 then L-BFGS")):
        group=[r for r in rows if r["experiment"]==key]
        assert len(group)==3
        times=[float(r["training_seconds"]) for r in group]
        gradients=[int(r["gradient_evaluations"]) for r in group]
        error=statistics.median(float(r["relative_l2"]) for r in group)
        summaries[key]=dict(median_training_seconds=statistics.median(times),
            training_seconds_range=[min(times),max(times)],median_relative_l2=error,
            gradient_evaluations_range=[min(gradients),max(gradients)])
        grad=str(gradients[0]) if min(gradients)==max(gradients) else f"{min(gradients)}-{max(gradients)}"
        lines.append(f"| {label} | {error*100:.3f}% | {statistics.median(times):.3f} s | "
                     f"{min(times):.3f}-{max(times):.3f} s | {grad} |")
    added=[float(r["training_seconds"])-float(r["adam_seconds"]) for r in rows
           if r["experiment"]=="adam_then_lbfgs"]
    summaries["added_lbfgs_phase_seconds"]=dict(median=statistics.median(added),range=[min(added),max(added)])
    lines += ["",f"Within the continued runs, the L-BFGS phase added a median {statistics.median(added):.3f} s "
        f"with range {min(added):.3f}-{max(added):.3f} s. This is a measured accuracy/cost tradeoff, "
        "not a free improvement. Training includes loss diagnostics and excludes process startup "
        "and file I/O. The controlled runs overlapped local ASR, so these are observed costs "
        "under that load rather than isolated speed benchmarks. Equal gradient counts do not "
        "imply equal wall time. Neither continuation nor the original model produces a "
        "positive full-field break-even against the much faster conventional reference.", ""]
    (ROOT/"outputs/remedy-costs.md").write_text("\n".join(lines),encoding="utf-8")
    (ROOT/"outputs/remedy-costs.json").write_text(json.dumps(summaries,indent=2),encoding="utf-8")
    print("\n".join(lines))


if __name__=="__main__":
    main()

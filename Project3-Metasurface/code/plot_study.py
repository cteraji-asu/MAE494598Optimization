"""Static figures from the completed controlled and reflection studies."""
import cmath
import csv
import json
import math
from pathlib import Path
from helmholtz import Network,spectrum
from plot_results import plot
ROOT=Path(__file__).resolve().parents[1]


def read(path):
    with (ROOT/path).open(newline="",encoding="utf-8") as f:
        return [{k:float(v) if v and _is_number(v) else v for k,v in r.items()}
                for r in csv.DictReader(f)]


def _is_number(value):
    try:
        float(value)
        return True
    except ValueError:
        return False


def main():
    history=read("outputs/controlled/adam_then_lbfgs_seed-0_loss.csv")
    plot("optimizer-loss-k10.png","Optimizer continuation reduces each constraint residual",
         "k=10, seed 0; normalized losses; L-BFGS follows the same 3,000 Adam updates",
         "Gradient evaluations", "Mean squared residual",
         [(key,[(r["evaluation"],r[key]) for r in history]) for key in ("pde","dirichlet","outgoing")],
         True,vlines=[(3000,"L-BFGS begins")])
    fields={name:read(f"outputs/controlled/{name}_seed-0_field.csv")
            for name in ("matched_pinn","adam_then_lbfgs")}
    plot("optimizer-pointwise-k10.png","Pointwise field error before and after continuation",
         "k=10, seed 0; stationary complex-field magnitude error",
         "Dimensionless position x","Absolute field error",
         [(name,[(r["x"],r["abs_error"]) for r in rows]) for name,rows in fields.items()])
    signals=[("Exact field",[cmath.exp(10j*j/256) for j in range(256)])]
    for name in ("matched_pinn","adam_then_lbfgs"):
        model=json.loads((ROOT/f"outputs/controlled/{name}_seed-0_parameters.json").read_text())
        net=Network(model["width"],0)
        net.p=model["parameters"]
        signals.append((name,[net.value(j/256) for j in range(256)]))
    spectra=[(name,sorted([(r["cycles_per_domain"],r["amplitude"]) for r in spectrum(values)]))
             for name,values in signals]
    plot("signal-spectrum-k10.png","Exact and predicted signals both show finite-window leakage",
         "k=10, seed 0; physical frequency k/(2*pi)=1.59 cycles per domain",
         "Cycles per domain","Complex DFT amplitude / 256",spectra,True,(-12,12),
         vlines=[(10/(2*math.pi),"k/(2*pi)")])
    flips=read("outputs/reflection/phase-flip-summary.csv")
    variants=("pinn","adam_equal_evaluations","adam_then_lbfgs")
    plot("reflection-phase-flip.png","Optimizer choice changes the predicted switch-state phase gap",
         "Ideal Dirichlet/Neumann reflectors, k=10; each point is a fixed seed",
         "Seed","Wrapped phase-flip error (degrees)",
         [(name,[(r["seed"],r["phase_flip_error_degrees"]) for r in flips if r["variant"]==name])
          for name in variants],True)
    response=read("outputs/reflection/summary.csv")
    plot("reflection-magnitude.png","Reflected magnitudes after continuation remain near one",
         "Ideal lossless terminations, k=10; model target magnitude is exactly 1",
         "Seed","Magnitude of reflected coefficient R",
         [(state,[(r["seed"],r["reflection_magnitude"]) for r in response
                  if r["variant"]=="adam_then_lbfgs" and r["state"]==state])
          for state in ("dirichlet","neumann")]+[("Exact",[(0,1),(1,1),(2,1)])])
    print("Wrote five controlled-study figures")


if __name__=="__main__":
    main()

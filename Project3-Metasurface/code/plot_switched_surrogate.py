"""Publication figures from retained finite-switch results, no training."""
import cmath
import math
from pathlib import Path
import statistics
import numpy as np
import plot_results
from plot_results import plot
from summarize_switched_surrogate import read
from switched_line import write_csv

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/"outputs/switched-surrogate"
plot_results.OUT=ROOT/"outputs/figures-switch"


def main():
    modes=("pinn","supervised","interpolation")
    pairs={mode:read(DATA/(f"{mode}_seed-0_pairs.csv" if mode!="interpolation" else "interpolation_pairs.csv")) for mode in modes}
    for mode in pairs:pairs[mode]=sorted(pairs[mode],key=lambda r:r["d"])
    true=pairs["pinn"]
    vertical=[(.195,"blocked interval"),(.222,"")]
    plot("switch-phase.png","Finite-switch phase response across geometry",
         "Fresh geometries, seed 0; blocked d=0.195-0.222 excluded from all fitting",
         "Right-segment length d / wavelength","Two-state phase separation (degrees)",
         [("Exact",[(r["d"],r["exact_separation"]) for r in true])]+
         [(mode,[(r["d"],r["predicted_separation"]) for r in pairs[mode] if r["predicted_phase_valid"]]) for mode in modes],
         vlines=vertical)
    plot("switch-magnitude.png","Reflected amplitude remains a separate screening requirement",
         "Fresh geometries, seed 0; minimum over switch states; all values are raw predictions",
         "Right-segment length d / wavelength","Minimum reflection magnitude",
         [("Exact",[(r["d"],r["exact_min_magnitude"]) for r in true])]+
         [(mode,[(r["d"],r["predicted_min_magnitude"]) for r in pairs[mode]]) for mode in modes],vlines=vertical)
    loss=read(DATA/"pinn_seed-0_loss.csv")
    plot("switch-loss.png","The PINN minimizes four physical constraint losses",
         "Seed 0; stochastic paired batches; driven interface loss divided by four",
         "Adam updates","Mean squared residual, logarithmic scale",
         [(name,[(r["step"],r[name]) for r in loss]) for name in
          ("pde_voltage","pde_current","driven_interface","terminal_short")],True)
    plot("switch-R-error.png","Reflection errors rise inside the blocked resonance interval",
         "Fresh held-out geometries, seed 0; maximum complex R error over the two states",
         "Right-segment length d / wavelength","Absolute complex reflection error",
         [(mode,[(r["d"],r["complex_R_error"]) for r in pairs[mode] if str(r["split"]).startswith("test")]) for mode in modes],
         True,vlines=vertical)
    all_pairs={mode:sum([read(DATA/f"{mode}_seed-{s}_pairs.csv") for s in (0,1,2)],[]) for mode in ("pinn","supervised")}
    all_states={mode:sum([read(DATA/f"{mode}_seed-{s}_states.csv") for s in (0,1,2)],[]) for mode in ("pinn","supervised")}
    def binned(rows,xkey,ykey,transform=lambda x:x):
        filtered=[r for r in rows if str(r["split"]).startswith("test")]
        xs=[transform(r[xkey]) for r in filtered]
        edges=np.linspace(min(xs)-1e-10,max(xs)+1e-10,13)
        result=[]
        for low,high in zip(edges,edges[1:]):
            members=[r for r in filtered if low<=transform(r[xkey])<high]
            if members:result.append(((low+high)/2,statistics.median(r[ykey] for r in members)))
        return result
    detuning_rows={mode:[dict(r,detuning=abs(2*math.pi*r["d"]-math.pi/2)) for r in rows]
                   for mode,rows in all_states.items()}
    plot("switch-error-detuning.png","Physical weak coupling does not define neural difficulty",
         "Held-out states, three seeds pooled; 12 equal detuning bins; median relative voltage error",
         "Distance from current node |2*pi*d - pi/2|","Relative complex voltage L2 error",
         [(mode,binned(detuning_rows[mode],"detuning","voltage_relative_L2")) for mode in detuning_rows],True)
    plot("switch-error-gradient.png","Response sensitivity organizes the screening errors",
         "Held-out geometries, three seeds pooled; binned medians; association does not prove root cause",
         "log10 maximum conventional |dR/dd| over states","Absolute complex reflection error",
         [(mode,binned(all_pairs[mode],"reference_response_gradient","complex_R_error",math.log10)) for mode in all_pairs],True)
    fields={mode:read(DATA/f"{mode}_seed-0_fields.csv") for mode in ("pinn","supervised")}
    def error(row):return complex(row["predicted_v_real"]-row["reference_v_real"],row["predicted_v_imag"]-row["reference_v_imag"])
    plot("switch-pointwise-error.png","Voltage errors along each right segment",
         "Seed 0, off state; fixed examples nearest d=0.25 node and d=0.2084 transition",
         "Local right-segment coordinate xi","Absolute complex voltage error",
         [(mode+" "+name,[(r["local"],abs(error(r))) for r in rows if r["example"]==name and r["state"]==1 and r["segment"]==1])
          for mode,rows in fields.items() for name in ("near_node","transition")],True)
    spectra=[];spectrum_rows=[]
    for mode,rows in fields.items():
        for segment in (0,1):
            selected=[r for r in rows if r["example"]=="transition" and r["state"]==1 and r["segment"]==segment][:-1]
            values=np.array([error(r) for r in selected])
            frequencies=np.fft.fftfreq(len(values),1/len(values))
            amplitude=abs(np.fft.fft(values))/len(values)
            order=np.argsort(frequencies)
            spectra.append((mode+" "+("left" if segment==0 else "right"),[(float(frequencies[j]),float(amplitude[j])) for j in order]))
            spectrum_rows.extend(dict(mode=mode,segment=segment,cycles_per_segment=float(frequencies[j]),amplitude=float(amplitude[j])) for j in order)
    write_csv(DATA/"example-error-spectra.csv",spectrum_rows)
    plot("switch-error-spectrum.png","Error spectra retain the physical interface",
         "Seed 0, transition example, off state; separate segment DFTs; finite-window leakage possible",
         "Cycles per segment","Complex voltage error DFT amplitude / 128",spectra,True,(-12,12))
    base=read(ROOT/"outputs/switched-line/baseline-refinement.csv")
    plot("switch-baseline-refinement.png","The discretized circuit baseline converges at second order",
         "Positive-loss examples; trapezoidal spatial discretization versus ABCD reference",
         "Intervals per segment","Absolute complex reflection error",
         [(case+" "+str(state),[(r["intervals_per_segment"],r["absolute_complex_reflection_error"]) for r in base
                               if r["case"]==case and r["state"]==state])
          for case in ("strong","near_current_node") for state in (0,1)],True)
    print("Wrote nine finite-switch figures and retained separate-segment spectra")


if __name__=="__main__":main()

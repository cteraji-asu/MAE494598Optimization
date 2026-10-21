"""Write the hard-boundary findings and label historical comparisons explicitly."""
import json
import numpy as np
import torch
from hard_boundary_control import ROOT,OUT,load,port_reflections,sha
from switched_line import phase_metrics,response
from switched_surrogate import classification

def main():
    torch.set_num_threads(1)
    results=json.loads((OUT/'results.json').read_text())
    historical=json.loads((ROOT/'outputs/switched-surrogate/frozen-protocol.json').read_text())
    designs=[r for r in historical['designs'] if r['split']=='test_blocked'];old=[]
    for item in results['models']:
        model,_=load(item['arm'],item['seed']);pred=port_reflections(model,designs);pairs=[]
        for design,rr in zip(designs,pred):
            em=phase_metrics(*[response(design['length'],design['switch_fraction'],s)[0] for s in (0,1)]);pm=phase_metrics(*rr)
            pairs.append(dict(exact_phase_valid=em['phase_valid'],predicted_phase_valid=pm['phase_valid'],exact_separation=em['separation_degrees'],predicted_separation=pm['separation_degrees'],exact_min_magnitude=em['min_magnitude'],predicted_min_magnitude=pm['min_magnitude']))
        old.append(dict(arm=item['arm'],seed=item['seed'],historical_blocked_decisions=classification(pairs,15,.8)))
    (OUT/'historical-comparison.json').write_text(json.dumps(dict(status='Previously inspected primary blocked cohort, diagnostic only. Not the new final holdout.',models=old),indent=2))
    lines=['# Exact boundary enforcement is insufficient at this budget','',
      'Six fresh, paired fits compared soft penalties with exact endpoint enforcement. All six failed the unchanged validation gate. The hard transform made the driven boundary and short exact but left large interior and reflection error. Exact endpoint enforcement was insufficient to repair this model at the fixed budget. The transform also changes the trial-function representation, so this does not establish the original training-failure cause. It does not identify one remaining optimization cause.','',
      'The synthetic finite-switch line is a frequency-domain boundary-value analogue. These results do not reproduce or validate the researcher\'s hardware.','',
      '## Prospective controls','',
      f"Protocol SHA-256 `{results['protocol_sha256']}`. Selected checkpoints were sealed before final reference access, seal SHA-256 `{results['selection_seal_sha256']}`.",
      'Same raw 3–64–64–4 tanh network, 4,676 parameters, seeds 0/1/2, identical paired initial weights and minibatch streams, covered 256 training geometries, 4,000 Adam gradient calls and cosine schedule per fit. No reference field or reflection label enters the training objective. Validation chooses among checkpoints every 500 steps, while every fit spends all 4,000 calls. Equal calls do not imply equal runtime.','',
      'The transform is $I=i$, $V=v-\\xi v(1)-(1-\\xi)[v(0)+(1+z_s)i(0)-2]$. Endpoint evaluations remain differentiable. This changes the trial-function representation as well as boundary enforcement. It does not isolate gradient imbalance.','',
      'The original 32+32 fresh blocked proposal could not freeze because only 61 separated candidates remained. It became 30 validation plus 30 final before fitting or reference-class inspection. Minimum separation stayed $2\\times10^{-5}$. Off-block counts are 80 validation and 256 final.','',
      '## Final results','',
      '| Arm | Seed | Selected step | Fit seconds | Blocked max-state reflection error, 95th percentile | Blocked voltage relative L2, median | Max driven-boundary residual |',
      '|---|---:|---:|---:|---:|---:|---:|']
    for item in results['models']:
        b=item['regions'][-1]
        lines.append(f"| {item['arm']} | {item['seed']} | {item['selected_step']} | {item['training_seconds']:.3f} | {b['R_max_state_p95']:.6f} | {100*b['median_voltage_relative_L2']:.2f}% | {b['maximum_driven_interface_abs']:.3g} |")
    lines+=['',
      'All 30 new blocked final geometries are reference-infeasible at the illustrative phase≥165° and magnitude≥0.8 thresholds. Both arms classify all 30 as infeasible. Sensitivity is undefined, so the 100% specificity cannot demonstrate successful screening. Five cases are near the declared thresholds. No new class-enriched sample was added after seeing this result.','',
      'On the historical primary blocked cohort, every new arm/seed still misses all 10 feasible cases, with zero false feasible predictions among 150 infeasible cases. This is a previously inspected diagnostic cohort, not new final evidence.','',
      'Hard enforcement reduces terminal voltage to zero and driven-boundary/extraction disagreement to roundoff. It does not fix the final reflection tail or spatial field accuracy. Its maximum blocked power-balance defect is larger than the matched soft arm in every seed, so endpoint correctness does not imply energy consistency.','',
      '## Independent checks and cost','',
      'Saved state reflections were recomputed with standalone NumPy network algebra and an independent complex wave-system reference. Spatial derivatives were compared with NumPy finite differences. The exact residual transport identity was checked for every final state with quadrature. See results.json for maxima and counts.','',
      'Reflection-only hard inference uses the unchanged current output and one raw network pass. The conventional factorized reference remains faster for both single and batch queries. There is no positive break-even query count. Fit wall time includes validation as a subset. Reference generation occurs outside that fit timer. Total timed setup is fit wall time plus reference generation, without adding validation a second time.','',
      '## Decision','',
      'Keep the conventional model for this analogue. Use the verified signed residual budget to guide a separately frozen experiment only if the researcher needs this specific diagnostic. Do not claim Path C success, a unique PINN root cause, a full-wave speedup, or a hardware remedy. The current Path B evidence establishes a failure and shows exact endpoint enforcement was insufficient to repair this model at the fixed budget, while optimization, representation and sampling remain coupled alternatives.','',
      'Sources: [exact boundary trial functions](https://arxiv.org/abs/2104.08426), [derived error identity](residual-error-identity.md), [protocol](outputs/hard-boundary-control/frozen-protocol.json), [all six results](outputs/hard-boundary-control/results.json), [historical comparison](outputs/hard-boundary-control/historical-comparison.json).','']
    (ROOT/'hard-boundary-findings.md').write_text('\n'.join(lines),encoding='utf-8')
    print(json.dumps(dict(historical=old,models=6)))
if __name__=='__main__':main()

import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def main():
    r=json.loads((ROOT/'outputs/residual-error-budget/summary.json').read_text())
    rows=r['models']
    lines=['## Historical signed residual budget','',
      f"The verified identity was evaluated without fitting on {len(rows)} retained models and 10,048 historical state cases. The largest identity discrepancy is {max(x['maximum_identity_disagreement'] for x in rows):.3g}; the largest 64-to-128 quadrature change is {max(x['maximum_64_to_128_disagreement'] for x in rows):.3g}. There are zero bound violations. These cohorts were previously inspected, so this is a historical diagnostic, not a pristine holdout.",'',
      'The table reports medians over blocked state cases. Signed projections are component projections onto the total error, not magnitude shares. They can be negative or exceed one when components cancel. Post-hoc subtraction includes quadrature and is not a trained remedy.','',
      '| Model | Median state reflection error | Boundary signed projection | Interior signed projection | Error after boundary subtraction | Feasible designs retained, original / subtraction |','|---|---:|---:|---:|---:|---:|']
    for item in rows:
        b=item['regions'][-1];before=b['decisions']['original'];after=b['decisions']['remove_boundaries']
        lines.append(f"| {item['model']} | {b['median_R_error']:.5g} | {b['median_boundary_signed_projection']:.3f} | {b['median_interior_signed_projection']:.3f} | {b['median_remove_boundaries_error']:.5g} | {before['tp']}/{before['actual_feasible']} / {after['tp']}/{after['actual_feasible']} |")
    lines+=['',
      'Both boundary and interior contributions matter in the failed PINNs. Removing boundary contributions reduces many reflection errors but recovers no missed feasible designs in those blocked cohorts. For the supervised representability fit, cancellation means boundary subtraction worsens the median state reflection error and discards its retained feasible designs. This explains error propagation and cancellation; it does not diagnose the training mechanism.','',
      '### Measured geometry difficulty and spatial diagnostics','',
      'The output-residual gain G is a separate non-monotone stability diagnostic. The controlled nested sampling-gap study supplies the increasing P3 axis. This older diagnostic plots relative voltage L2 against measured gain; states above its displayed L2 limit are counted. P4 uses spatial complex error and separate-segment transforms, rather than a parameter trace.','',
      '![Measured gain versus field error and pointwise spatial error](outputs/figures-switch/core-gain-and-pointwise-error.png)','',
      '![Measured gain and right-segment spatial error spectrum](outputs/figures-switch/core-gain-and-spectrum.png)','',
      '![Separate physics-loss histories and spatial spectrum](outputs/figures-switch/core-loss-components-and-spectrum.png)','',
      'The spectral example is primary seed 0, OFF, d=0.208395. The DFT uses 128 samples without the duplicate endpoint and a 1/128 amplitude normalization. Finite-window leakage remains possible. Loss histories, spectra and gain association do not prove gradient imbalance, spectral bias or a Hessian condition number.','']
    (ROOT/'residual-budget-findings.md').write_text('\n'.join(lines),encoding='utf-8')
if __name__=='__main__':main()

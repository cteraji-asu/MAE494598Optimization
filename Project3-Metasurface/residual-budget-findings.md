## Historical signed residual budget

The verified identity was evaluated without fitting on 12 retained models and 10,048 historical state cases. The largest identity discrepancy is 2.87e-14; the largest 64-to-128 quadrature change is 3.15e-14. There are zero bound violations. These cohorts were previously inspected, so this is a historical diagnostic, not a pristine holdout.

The table reports medians over blocked state cases. Signed projections are component projections onto the total error, not magnitude shares. They can be negative or exceed one when components cancel. Post-hoc subtraction includes quadrature and is not a trained remedy.

| Model | Median state reflection error | Boundary signed projection | Interior signed projection | Error after boundary subtraction | Feasible designs retained, original / subtraction |
|---|---:|---:|---:|---:|---:|
| primary-pinn-0 | 0.40344 | 0.521 | 0.479 | 0.15433 | 0/10 / 0/10 |
| primary-pinn-1 | 0.39214 | 0.491 | 0.509 | 0.19439 | 0/10 / 0/10 |
| primary-pinn-2 | 0.39591 | 0.614 | 0.386 | 0.17279 | 0/10 / 0/10 |
| primary-supervised-0 | 0.25236 | -1.274 | 2.274 | 1.3968 | 0/10 / 0/10 |
| primary-supervised-1 | 0.2292 | 1.107 | -0.107 | 0.89815 | 0/10 / 0/10 |
| primary-supervised-2 | 0.28029 | -0.457 | 1.457 | 1.1162 | 0/10 / 0/10 |
| covered-pinn-0 | 0.39294 | 0.506 | 0.494 | 0.16348 | 0/18 / 0/18 |
| covered-pinn-1 | 0.38669 | 0.521 | 0.479 | 0.17682 | 0/18 / 0/18 |
| covered-pinn-2 | 0.38933 | 0.553 | 0.447 | 0.17219 | 0/18 / 0/18 |
| representability-supervised-0 | 0.0083377 | -0.218 | 1.218 | 0.031682 | 12/17 / 0/17 |
| optimizer-lbfgs-0 | 0.064723 | 0.538 | 0.462 | 0.021063 | 0/8 / 0/8 |
| optimizer-adam-0 | 0.38308 | 0.556 | 0.444 | 0.17157 | 0/8 / 0/8 |

Both boundary and interior contributions matter in the failed PINNs. Removing boundary contributions reduces many reflection errors but recovers no missed feasible designs in those blocked cohorts. For the supervised representability fit, cancellation means boundary subtraction worsens the median state reflection error and discards its retained feasible designs. This explains error propagation and cancellation; it does not diagnose the training mechanism.

### Measured geometry difficulty and spatial diagnostics

The output-residual gain G is a declared continuous stability measure. It varies non-monotonically with d. P3 plots the held-out relative voltage L2 against this measured gain. States above the displayed L2 limit are counted explicitly. P4 uses the spatial complex error at a fixed geometry and state, with separate segment transforms in the retained full figures. This differs from a parameter-screening trace.

![Measured gain versus field error and pointwise spatial error](outputs/figures-switch/core-gain-and-pointwise-error.png)

![Measured gain and right-segment spatial error spectrum](outputs/figures-switch/core-gain-and-spectrum.png)

![Separate physics-loss histories and spatial spectrum](outputs/figures-switch/core-loss-components-and-spectrum.png)

The spectral example is primary seed 0, OFF, d=0.208395. The DFT uses 128 samples without the duplicate endpoint and a 1/128 amplitude normalization. Finite-window leakage remains possible. Loss histories, spectra and gain association do not prove gradient imbalance, spectral bias or a Hessian condition number.

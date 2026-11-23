# Smooth two-PINN follow-on: continuity is repaired, accuracy is not

After the hard-routing experiment exposed artificial reflection jumps near one, a second frozen experiment tested a differentiable overlap. The repair removes those jumps. It still fails every validation and final acceptance gate, and its design gradients are less accurate than the matched monolithic model. This is useful negative evidence: making a surrogate smooth does not make its physical gradients correct.

## Intervention and prospective controls

The blended field is y=(1-w)y_outside+w*y_narrow, where y contains real/imaginary V and I and

    w(d) = sigmoid((d-0.195)/0.002) * sigmoid((0.222-d)/0.002).

The width 0.002 was fixed before the new fits. Both 3-44-44-4 networks are evaluated at every point. The narrow specialist retains its local d scaling, and the other retains full-domain scaling. The logistic window transitions smoothly near the old hard boundaries. This is an overlapping parameter-domain model, not a second neural spatial subdomain at the physical switch.

Training minimizes the original PDE and boundary residuals of the blended V/I field. It does not train disconnected fields and blend them only afterward. Because w depends on d but not spatial coordinate xi, spatial derivatives blend directly. Design differentiation includes w'(d) and both networks' derivatives. There is no supervised loss, learned gate, added interface penalty, or result-driven width tuning.

The new protocol was frozen at 2026-11-10 18:53:28 UTC. SHA-256: `8d5afe13920aba89e44add4be89c08970b8bf4061ccc21c613cc255d2f0374f9`. All six terminal models were sealed before new validation/final reference evaluation. The hard-routing experiment and all its data remain unchanged. Its final set is now historical, not reusable pristine evidence.

New draws contain 256 training, 128 validation and 320 final designs, half in the difficult interval. They exclude every d in the prior experiment and the historical P3 frozen protocols by at least 1e-8. This is fresh stratified interpolation, with nearby neighbors allowed. All six fits start anew; old monolithic weights are not reused. Paired arms share the new minibatch stream and seeds 0/1/2. There is no validation selection or early stopping.

The unchanged per-fit budget is 4,000 Adam updates, 1,024,000 interior point-state residual evaluations and 2,048,000 endpoint point-state evaluations, float64 on one CPU thread. The learning rate follows the original 0.002-to-0.0002 cosine schedule. Capacity is 4,676 monolithic versus 4,672 blended parameters. Evaluating both specialists uses 4,488 affine multiplications per point versus 4,544 for the monolithic model, within 1.23%. This is approximate affine-work matching, not exact FLOP matching: gates, nonlinearities, derivative graphs, allocation and runtime differ. Both experts evaluate all points, unlike the first experiment's conditional routing.

## New final results

Metrics and acceptance thresholds are unchanged from the first experiment. The fresh final cohort contains 23 feasible and 297 infeasible designs.

| Arm | Seed | Fit seconds | Reflection p95 | Physical voltage median relative L2 | Feasible retained | False feasible |
|---|---:|---:|---:|---:|---:|---:|
| Monolithic | 0 | 17.63 | 1.4722 | 5.06% | 12/23 | 0/297 |
| Smooth blend | 0 | 27.66 | 1.0913 | 3.93% | 12/23 | 0/297 |
| Monolithic | 1 | 17.87 | 1.4735 | 3.90% | 13/23 | 0/297 |
| Smooth blend | 1 | 27.48 | 1.1264 | 4.15% | 13/23 | 0/297 |
| Monolithic | 2 | 17.67 | 1.4418 | 4.49% | 16/23 | 3/297 |
| Smooth blend | 2 | 27.31 | 1.1455 | 4.79% | 12/23 | 0/297 |

The blend improves reflection p95 in every seed, but improves median voltage error only in seed 0. Its voltage-error p95 remains 72.4%-75.2%. Smoothness does not fix the field tail or screening sensitivity. Physical feasibility remains phase separation >=165 degrees and minimum magnitude >=0.8. Every arm fails the unchanged gate of reflection p95 <=0.03, median voltage error <=0.05, sensitivity/specificity >=0.9, and both classes present. All validation gates fail too. Direct numerical comparisons between the two experiments are descriptive, not paired estimates, because their held-out designs and training sets differ.

## Continuity and design derivatives

Across a 2e-9 interval centered at either old routing boundary, blended reflection differences are 2.67e-7 to 2.85e-7, rather than the original hard-routing jumps of 0.88-1.03. The sigmoid construction is continuously differentiable by construction; the small nonzero differences measure finite separation, not a residual mathematical jump. One-sided derivative differences over a 2e-8 interval are 4.80e-5 to 6.49e-5. Tests also check autodifferentiation at the window boundaries against finite differences.

The retained broad derivative audit uses 302 final right-length values with d <= 0.306 at fixed L=0.36. Three have d < 0.036 and therefore lie outside the separate restricted design-search box [0.036, 0.306]. Relative errors of the antialignment objective gradient are 105.9%-109.3% for the blend versus 94.9%-95.0% for monolithic models. A separate review of the 299 in-box values gives the same ranges and conclusion. These are inaccurate physical design gradients despite correct differentiation of the fitted function. The window adds large smooth slopes where the component fields disagree; continuity alone does not control those slopes. The frozen results have not been filtered or replaced.

The original h=1e-6 finite-difference check has maximum absolute discrepancies up to 2.96e-5 for the blend. A post-fit verification, without any model changes, reduces h to 5e-7 and 1e-7. Errors decrease approximately quadratically, reaching at most 2.83e-7 absolute and 5.04e-10 relative L2 at 1e-7. The reference gradient changes by only 1.01e-8 relative L2 when h decreases from 1e-6 to 1e-7. Numerical differentiation error cannot explain the large physical-gradient error. All original metrics remain saved.

Every new surrogate selects d=0.036 in the same restricted 10,001-point grid audit at L=0.36. That alternative is reference-feasible, with phase 179.4663 degrees and minimum magnitude 0.942854, but does not recover the conventional grid optimum d=0.208422 with phase 179.9405 degrees and magnitude 0.800510. This remains a one-dimensional grid audit, not a continuous global certificate or the >=20-variable FE adjoint optimization.

## Conventional timing and verification

The vectorized sinh/cosh baseline remains faster at every tested batch size. Median seconds are measured using 21 warmed repeats, with no spatial-derivative work in neural reflection inference:

| Designs per batch | Conventional | Monolithic range | Smooth-blend range |
|---:|---:|---:|---:|
| 1 | 27.3 microseconds | 250.0-255.2 microseconds | 413.1-415.6 microseconds |
| 320 | 95.3 microseconds | 1077.7-1089.2 microseconds | 1202.1-1652.6 microseconds |
| 10,001 | 2.07 milliseconds | 25.51-25.84 milliseconds | 35.93-37.23 milliseconds |

Training adds 27.3-27.7 seconds per blend. There is no positive break-even query count against this baseline at these measured batch sizes. Ordinary machine-load variation is visible in timings, including between the two experiments. These results are implementation measurements, not dedicated hardware benchmarks or evidence about full-wave solvers.

The analytic reference agrees with the independent complex wave-system solve within 7.85e-15 over 640 final states. Eight follow-on tests pass, including independent NumPy replay of all final reflections, the smooth gate derivative, spatial jets, prospective separation, unchanged thresholds, parameter counts and source/checkpoint hashes. The initial seven-test suite remains intact.

## Reproduce and inspect

Use Python with NumPy and CPU PyTorch. Exact versions are recorded in [results](assets/smooth-pinn-results.json). From the repository root:

```powershell
python -m unittest discover -s Project4-Metasurface/tests -p test_smooth_pinn.py -v
python Project4-Metasurface/code/smooth_pinn_study.py --output Project4-Metasurface/assets/smooth-pinn-reproduction --freeze-only
python Project4-Metasurface/code/smooth_pinn_study.py --output Project4-Metasurface/assets/smooth-pinn-reproduction
python Project4-Metasurface/code/smooth_pinn_audit.py --output Project4-Metasurface/assets/smooth-pinn-reproduction
```

For an exact frozen-design rerun, copy `smooth-pinn-protocol.json` and `smooth-pinn-freeze-receipt.json` into the new output folder first. Existing protocols are reused only with the identical source hash. Existing result files are never overwritten. The prior `assets/two-pinn-protocol.json` is retained as the historical exclusion source. Tests inspect the canonical evidence under `Project4-Metasurface/assets`; run them in an isolated repo-style copy to test regenerated evidence without overwriting the original.

Artifacts: [driver](code/smooth_pinn_study.py), [gradient audit](code/smooth_pinn_audit.py), [tests](tests/test_smooth_pinn.py), [protocol](assets/smooth-pinn-protocol.json), [freeze receipt](assets/smooth-pinn-freeze-receipt.json), [checkpoint seal](assets/smooth-pinn-checkpoint-seal.json), [all weights and results](assets/smooth-pinn-results.json), [gradient-step checks](assets/smooth-pinn-gradient-audit.json), [test transcript](assets/smooth-pinn-tests.txt).

The decision is unchanged after the critique-and-repair loop: retain both experiments as supporting research, and use the verified conventional/FE solver for design. This bounded failure does not rule out every overlapping architecture, optimizer or training budget. It does not establish hardware performance, full-wave speedup, or surrogate bonus credit, and it does not assert any student's manual derivation or review.

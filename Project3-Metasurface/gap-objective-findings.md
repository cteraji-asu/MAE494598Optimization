# Controlled sampling and objective findings


This historically informed follow-up explicitly supplies an increasing sampling-difficulty axis. The width w of a centered missing-training interval around d=0.2085 increases from 0 through 0.0135 to 0.027. Its training sets are nested: 256, 248 and 240 geometries. Larger w removes support near the same difficult finite-switch field family. This is a sampling-sparsity knob, not a claim that electrical length or the retrospective gain G is globally monotone. It is nested support removal, not relocation at fixed sample count. Minimum train/evaluation d separation for the smaller gaps is about 6.76e-6, not the primary 2e-5 threshold; no exact overlap occurs.

Every physics/reference pair starts from the identical failed primary PINN seed-0 checkpoint. Architecture, normalization, paired states, 17 spatial training nodes, full-batch L-BFGS, fresh optimizer state and 1,200 gradient calls are matched. Only the objective differs within a pair. Reference labels are available only to direct-reference training. The same 160 blocked and 224 off-grid primary geometries are evaluated at 128 spatial midpoints. Those cohorts were inspected previously, so these are diagnostic comparisons, not pristine tests. Wider gaps have fewer training constraints, which is the intended sampling intervention; equal gradient calls are not equal point work or runtime.

The protocol and diagnostic criteria were frozen before these six fits, after the previous studies were known. All six terminal accepted checkpoints are reported. There is no new seed/architecture search or result-driven extension. The separate deployment gate retains R95<=0.03, median joint-field L2<=0.05 and sensitivity/specificity>=0.9 with both classes present. The diagnostic field contrast is not a replacement acceptance tolerance.

| Gap width w | Objective | Training geometries | Gradient calls | Blocked joint right-field L2, median | Blocked max-state R95 | Feasible retained | False feasible | Deployment gate |
|---|---|---:|---:|---:|---:|---:|---:|---|
| 0 | physics | 256 | 1200 | 9.7902% | 1.071359 | 0/10 | 0/150 | failed |
| 0 | supervised | 256 | 1200 | 0.3543% | 0.041350 | 10/10 | 10/150 | failed |
| 0.0135 | physics | 248 | 1200 | 14.2814% | 1.214719 | 0/10 | 0/150 | failed |
| 0.0135 | supervised | 248 | 1200 | 0.5787% | 0.151102 | 8/10 | 16/150 | failed |
| 0.027 | physics | 240 | 1200 | 20.2759% | 1.359236 | 0/10 | 0/150 | failed |
| 0.027 | supervised | 240 | 1200 | 1.6389% | 0.898411 | 0/10 | 0/150 | failed |

![Relative field error versus controlled gap width](outputs/figures-switch/gap-objective-relative-L2.png)

![Separate loss diagnostics for all six continuations](outputs/figures-switch/gap-objective-losses.png)



New continuation fit times, CPU float64 with one thread, are measured separately from label setup and evaluation:

| Gap width | Physics fit seconds | Reference fit seconds |
|---|---:|---:|
| 0 | 65.276 | 40.486 |
| 0.0135 | 61.911 | 38.486 |
| 0.027 | 58.998 | 38.047 |

Reference generation and evaluation are separately recorded in each result JSON. Physics training uses no reference labels. These are fixed-call diagnostics, not a new inference-speed benchmark. The original P5 single/batch timings and negative break-even result remain in force.

The displayed relative L2 jointly normalizes V and I on the right segment, then takes the median over 320 blocked state cases. It is not the physical two-segment voltage metric from the earlier optimizer study. Both objective arms worsen monotonically over these three predeclared widths. At full coverage, changing the objective reduces median field error by 27.63 times, with the same model, start, optimizer and input locations. The largest gap raises direct-reference field error by 4.63 times. All pairs reach the same gradient-call cap. These outcomes meet the frozen diagnostic contrast criteria and separate objective dependence and missing-support effects from a pure architecture-capacity ceiling at the observed field-error scale.

All six blocked-cohort deployment gates still fail. All three supervised off-grid arms pass their off-grid gate; these do not replace the blocked result. The fully covered reference-trained arm retains 10/10 feasible cases but also promotes 10/150 infeasible cases and has R95=0.04135, above 0.03. No acceptance threshold is relaxed to call that a success. At the largest gap it retains 0/10 feasible cases. A single seed and historical cohorts limit generalization. This does not uniquely identify spectral bias, a Hessian mechanism, boundary imbalance or the entire original screening failure.

The earlier matched optimizer experiment independently identifies an optimizer-pathway effect: identical starting weights, physics objective, inputs and 1,200 gradient calls give blocked physical-voltage median L2 43.3932% with Adam and 7.5747% with L-BFGS. L-BFGS improves 204/256 blocked state cases, but both arms retain 0/8 feasible designs and fail their validation gate. That is a bounded Path B diagnosis of attained optimization error, not a successful remedy. Together these controlled findings identify optimizer, objective and coverage contributions under stated conditions, while the unique finer mechanism remains open.

See [frozen gap protocol](outputs/gap-objective-diagnosis/frozen-protocol.json), [all six results](outputs/gap-objective-diagnosis/results.json), saved states/losses/weights beneath that folder, and [worked verification](worked-verification.md). Independent NumPy forward algebra and wave-system references check every saved output/error value, including a separate midpoint field calculation for each new model. Existing negative studies remain unchanged.


# Project 4 rubric crosswalk

Source: [current instructor assignment](https://github.com/DesignInformaticsLab/DesignOptimization2025/blob/main/docs/project4.md), retrieved 10 November 2026, source blob `4bffd93c866a1b02352cc969737467793037ca01`. This maps evidence; it is not a predicted grade.

| Category | Points | Evidence in this project | Remaining limits/actions |
|---|---:|---|---|
| Structure and formulation | 10 | Report sections 1–3; 20 independent loading variables, stated units/bounds, wave-response objective, four PDE-response constraints | Specific custom-formulation acceptance and real engineering limits are unverified. Constants are explicitly synthetic. |
| Analysis code and verification | 20 | Own P1 weak form; split interface; exact ABCD reference, nonlinear manufactured solution, mesh rates, power balance, source-phase covariance, Newton tangent/convergence, tests | Student-first derivation of expected benchmark answers cannot be supplied by an agent; team must perform and record it. |
| Sensitivities | 20 | Real implicit adjoints for objective and every constraint; all-coordinate central differences, Taylor plot, solve-count and wall-time comparison | Hardware/full-wave performance claims are not supported. Timing is implementation-specific. |
| Optimization | 15 | Five fixed starts for each model; bounds/scaling; failed starts retained; selected feasible KKT points; active bounds and multipliers; fine-mesh reevaluation | Local optima only. The best retained design does not reach Project 3's old 165° diagnostic target. |
| Nonlinear component | 15 | N2 cubic state law; Newton solve; analytic tangent; manufactured nonlinear benchmark; linear/nonlinear optimization and cross-evaluation | No selected-design change under these bounds; response changes are shown honestly. Higher harmonics and dynamic stability excluded. |
| Website and 3D comparison | 10 | index.md + custom WebGL viewer; shared camera, extruded line, P1 field, sequential legend, non-color global failure labels, history animation, element inspection, metrics, phone layout | Local QA completed; GitHub Pages activation and private-window deployed-site QA remain pending. |
| Reproducibility | 5 | reproduce.py creates isolated workspace and regenerates data, tests, report and figures with one command; frozen protocols and checkpoint seals | Dependency installation is separate. Timing is nondeterministic. See reproduction receipt for what was actually run. |
| Presentation and clarity | 5 | Technical report, generated tables/plots, linked source code, negative findings and AI-use disclosure | Team should rehearse and explain all derivations in its own words. |

## Eight viewer requirements

1. Initial/final side-by-side views share camera controls.
2. Fixed reduced-model line is extruded; capacitance and field heights are explicitly graphical encodings.
3. Voltage magnitude has a sequential scale and legend. Failed spatial-average or reflection constraints are identified by text and a global `!` marker, not a false local-voltage cutoff.
4. Complex voltage is interpolated with P1 shape functions before its magnitude is taken. No interpolation across the switch jump.
5. Playback and scrubber show saved optimization iterates, not time-domain wave dynamics.
6. Hover/click reports element/cell, material loading and field values. Keyboard selection is supported.
7. Objective, all four response constraints and all material bounds are available in the metric ledger.
8. Viewer reads canonical results.json; local desktop/phone layouts and console were checked. Public deployment/performance remains unverified.

## Bonus scope

- The N2 solver and manufactured benchmark are evidence relevant to the nonlinear bonus; no points are assumed.
- The two-PINN studies include field, screening, gradient, continuity and restricted-design comparisons. They are not surrogates inside the full20-variable FE optimizer. The later restricted own-FE comparison below supplies relevant bonus evidence without guaranteeing credit.
- No path-dependent adjoint, topology or design-under-uncertainty bonus is claimed.

## Human/publication completion steps

- Independently derive and check the expected benchmark values, with attribution distinguishing student work from agent work.
- Confirm the instructor accepts this exact synthetic nonlinear loading formulation and illustrative limits as the Project 3 extension.
- Review the code/report and agree on any required changes.
- Have a repository admin enable the authorized GitHub Pages deployment; verify the live page privately.
- Add the correct site link to the participation sheet if still required, and submit the repository/site links on Canvas. Neither external communication nor coursework submission has been performed by this work.

## 16 November follow-up
See [the fresh audit](review/rubric-audit-2026-11-16.md) for multi-design gradient convergence, initial-design constraint statuses, and remaining human/publication risks. No grade is inferred.

## Surrogate bonus clarification
The original full20-variable exclusion was overly categorical. The saved PINNs already participate in constrained discrete grid optimization. A new matching own-FE comparison now supplies gradient and selected-design discrepancies for that restricted family. See [bonus evidence audit](review/surrogate-bonus-audit-2026-11-16.md). Bad surrogate performance is an honest result, not automatic disqualification. No bonus points are guaranteed.

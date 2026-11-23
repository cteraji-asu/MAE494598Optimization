# Project 4 rubric crosswalk

Rubric: [course Project 4 page](https://designinformaticslab.github.io/DesignOptimization2025/project4.html#rubric), retrieved 23 November 2026. This file maps each row to evidence. It is not a grade; the scored review is in [review/rubric-scorecard-2026-11-23.md](review/rubric-scorecard-2026-11-23.md). Section numbers refer to `report.md` and the rendered page.

| Category (points) | Evidence | Remaining human items |
|---|---|---|
| Structure and formulation (10) | §2 Project 3 → 4 motivation; §3 variables with units and bounds, objective, four constraint formulas, limits table with source and status | Instructor acceptance of the custom formulation and synthetic limits |
| Analysis code and verification (20) | §4 PDE, weak form, elements, assumptions; §5 ten-rung ladder (our number / exact / relative error), convergence plot with slope reference; `code/verify_fem.py`, `code/rubric_studies.py` | Students derive the expected values by hand (§14) |
| Sensitivity analysis (20) | §6 adjoint derivation per functional kind; all-coordinate FD table at 3 designs; ε-sweep Taylor plot; first-order remainder plot; cost table and scaling plot (n = 10–80) | One kind of design variable only (§12) |
| Optimization (15) | §7 setup, every start including failures, convergence histories, active set, all 20 multipliers with re-solve checks, engineering reading, post hoc voltage-limit sweep with multiplier checks | Optimum is local and bound-dominated |
| Nonlinear component (15) | §8 N2 definition and strength; with/without at the frozen limit (same design, explained by multiplier signs); χ sweep (design changes at χ = 0.3); with/without when the voltage limit binds (designs differ) | — |
| Website and 3D comparison (10) | Viewer at the top of the page (`index.md`, `site/viewer.js`): linked cameras; labelled port/switch/short; P1-interpolated |V| with common scale and legend; text/hatched over-limit marks; optimization-history animation with phasor dial; mouse/touch/keyboard inspection; per-design metric panels with PASS/FAIL; 2D fallback without WebGL; MathJax 3.2.2 pinned | Re-verify on the public site after publication |
| Reproducibility (5) | §11; `reproduce.py` regenerates every JSON, figure and page in a new directory; tests and audit included; local run receipt in `review/reproduction-receipt-2026-11-23.md` | New files must be committed and the run repeated from a clean clone after any approved publication |
| Presentation and clarity (5) | §1 summary with results table; plain-language Project 3 story; figures generated from data | Team rehearses explanations in its own words |

**Bonus (not counted).** N2 with a manufactured nonlinear benchmark and quadratic Newton convergence is relevant to "fully nonlinear". The saved surrogates run inside SLSQP with gradients and optima compared (§10), but only on the restricted one-variable family; whether that meets "surrogate in the loop" is the instructor's call. No path-dependence, topology or uncertainty bonus is claimed.

Earlier audits: [16 November](review/rubric-audit-2026-11-16.md), [surrogate bonus note](review/surrogate-bonus-audit-2026-11-16.md). The 16 November surrogate framing is corrected in §10.

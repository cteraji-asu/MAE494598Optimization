# Rubric scorecard, 23 November 2026

This scorecard is a self-assessment of the local revision on branch `project4-rubric-polish`, compiled from three independent agent reviews. It is **not** a grade and does not predict what the instructor will award. Section numbers refer to `report.md`.

Rubric: [course Project 4 page](https://designinformaticslab.github.io/DesignOptimization2025/project4.html#rubric), with 100 points plus up to 15 bonus.

## Review rounds

| Round | Reviewed | Score (excluding bonus) | Outcome |
|---|---|---|---|
| Baseline | `cae98e1` (16 Nov draft) | Not scored by a separate reviewer | Main gaps: no in-loop surrogate run, thin gradient evidence, no KKT interpretation, no nonlinear with/without comparison, viewer missing many 3D requirements, math not rendering |
| Review 1 | Working tree before the fix round | 82 | 13 findings, including surrogate provenance, the Taylor wording, V8 and error-column semantics, missing constraint scaling, and overclaims |
| Review 2 | `13b5ed2` | 91 | 11 fixable items, including independent-start counts, an unjustified loading range, an incomplete Newton diagnosis, and wording |
| Review 3 | `da77f37` | 94 | No numerical errors found. Two minor items, the MACOM citation and the Python version notes, were fixed afterwards |

## Final row-by-row assessment (review 3, at `da77f37`)

| Category | Max | Score | Evidence | Remaining deduction |
|---|---|---|---|---|
| Structure and formulation | 10 | 9 | §2 motivation, and §3 variables, objective, constraint formulas and limits table with sources | Synthetic E ≤ 1.6 and \|R\| ≥ 0.8 limits; custom structure not confirmed by the instructor |
| Analysis code and verification | 20 | 19 | §5 ten-rung ladder (V1–V10) with our number, the exact value and the error type; §4 assumptions | No student derivation of the exact values recorded (§14) |
| Sensitivity analysis | 20 | 19 | §6 adjoint derivation including the cubic tangent; all-coordinate FD table at two step sizes; Taylor ε-sweep with stated criterion; cost table for n = 10–80 | Only one kind of design variable in the 20-variable problem |
| Optimization | 15 | 14 | §7 SLSQP with adjoint gradients, all 10 starts including failures, independent-start counts, scaled re-solve, KKT multipliers checked against re-solves, engineering reading | Local, bound-dominated optimum at 130.5°, not 180°; one nonlinear start fails in Newton, mechanism unproven |
| Nonlinear component | 15 | 15 | §8 cubic N2 with Newton and implicit adjoint; strength at the optimum; with/without at frozen and binding limits; χ sweep | — |
| Website and 3D comparison | 10 | 9 | §9 and the viewer: linked views, labelled port/switch/short, common \|V\| scale, text FAIL badges, history animation, mouse/touch/keyboard inspection, PASS/FAIL panels, WebGL fallback, 390 px layout (local checks only) | 3D is an extruded 1D line, which needs instructor confirmation; this revision is unpublished |
| Reproducibility | 5 | 4 | §11, `reproduce.py`, `review/reproduction-receipt-2026-11-23.md` (clean-clone run of `da77f37`, all checks passed) | Not yet reproduced from the published repository |
| Presentation and clarity | 5 | 5 | §1 summary table, plain-language Project 3 → Project 4 story, evidence labels, generated figures | — |
| **Total** | **100** | **94** | | |

## Bonus (not counted above)

- **Fully nonlinear:** supported by the evidence (§8, V4 and V8).
- **Surrogate in the loop:** uncertain. Saved PINNs do run inside SLSQP (§10, 60 runs), and their gradients and optima are compared with FE. But this is only the restricted one-variable linear Project 3 family, not the 20-variable problem.
- Nothing else is claimed. Whether a bonus is awarded is the instructor's decision.

## Not fixable by editing

- **Instructor confirmation:** the custom structure, the synthetic limits, the extruded-1D 3D display, and whether the restricted surrogate loop qualifies for the bonus.
- **Student work (§14 checklist):** derive the V1, V2, V4 and V6 exact values and the adjoint by hand, check one gradient entry, and rewrite the AI-use statement to say what you did.
- **Publication:** publishing this revision, then checking the public page in a private window. This needs separate approval.

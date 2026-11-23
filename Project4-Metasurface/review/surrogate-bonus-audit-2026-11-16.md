# Surrogate-in-the-loop bonus: evidence audit

The instructor rubric asks for a trained surrogate used inside an optimizer, comparison of its gradients and optimum with the student's solver, and explanation of disagreements. It does not require the surrogate to outperform the solver. It also does not explicitly repeat the20-variable requirement for this bonus experiment. The core20-variable FE/adjoint problem remains separate and mandatory.

## Existing evidence, not a new claim of successful PINNs

`two_pinn_study.py` and `smooth_pinn_study.py`, function `optimize_audit`, use trained networks to score10001 candidate designs at fixed total length0.36, enforce both predicted reflection-magnitude floors0.8, and choose the lowest antialignment objective. This is constrained discrete grid optimization, not a gradient-based continuous optimizer or global continuous certificate.

They compare selected designs against the own Project3 analytic transmission-line reference. The six smooth-study networks all select d=0.036, versus analytic grid optimum d=0.208422. They also compare actual autodiff design derivatives against reference derivatives. Large disagreements are retained and explained: fitted field accuracy does not guarantee derivative accuracy; specialization/blending can add slopes; original hard routing creates artificial jumps. No successful-surrogate or speedup claim is warranted.

Thus the earlier categorical dismissal solely because the surrogate was not used in the full20-variable optimizer was too strong. This is relevant supporting bonus evidence. Whether the instructor accepts the restricted study for full bonus remains a grading decision, not established by an agent.

## New post-fit FE bridge

A saved-model gradient export has been executed for all six retained smooth-study models at299 prior final-cohort points within the restricted optimization box. It contains actual autodiff derivatives and hashes, not newly trained or selected networks. The completed own-FE comparison for this identical physical family is documented below; its numerical evidence is retained separately.

The comparison must not use the nonlinear variable-loading core as if it were the same model: the PINNs represent a linear uniform-loading line with a moving switch. The supplemental FE family must match that physics, objective, constraints and design domain exactly.

## Completed comparison

The own two-segment P1 FE bridge passed reference mesh-convergence and seven shape-adjoint finite-difference probes. Refinement rates approach2. At128 elements per segment, the full-grid maximum reflection error is1.45419e-4 against the analytic reference; this discretization error is retained. The FE and analytic constrained grids select the same d=0.208422. FE objective is6.63933e-7 versus analytic5.39012e-7; doubling resolution gives5.69024e-7 at that selected design.

All12 historical surrogate selected designs were evaluated by FE. For the six smooth-study saved models,299 exactly matched in-box samples yield objective-gradient relativeL2 errors about95% for monolithic models and106–109% for specialists. Exact source-bound values appear in `surrogate-fe-comparison-2026-11-16.json`. The comparison completed successfully; that does not mean the surrogate passed physical reliability. No networks were retrained, no best seed selected, and the20-variable core results remain unchanged.

An independent reviewer checked the FE derivation and independently joined the saved-model and FE derivatives by exact design coordinate, recovering the same discrepancy values. The grid comparison is legitimate discrete optimization but not iterative-gradient convergence. Instructor grading of the restricted bonus remains uncertain.

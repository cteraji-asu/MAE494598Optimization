# Session Handoff

## Current state

- The root-level `Project 2 Report.md` is the single self-contained Project 2 submission. It includes the
  motivation, explicit mathematical formulation, classification, Family I mechanism,
  D1 spectrum, D2 intrinsic condition number κ test, D3 baseline convergence, D4
  before/after evidence, assumptions, constrained-mission validation, and reproduction
  commands.
- The old root-level `Project 2 Report.md` and failed-preflight output files were removed
  so there is one authoritative report and one current set of report artifacts.
- The human-approved diagnostic problem uses the same dynamics, objective, and exact
  terminal rendezvous constraint as the mission model, without acceleration inequalities.
  The `0.01 m/s²` acceleration bound remains enforced in the separate mission solve.
- `full_diagnostic_study` produces all D1--D4 data. The experiment writes
  `diagnostics.json`, `conditioning.csv`, `convergence.csv`, and SVG/PNG copies of the
  four figures under `outputs/report/`.
- The gradient-descent API retains bound enforcement by default. Only the explicit
  equality-constrained diagnostic opts out, and that path has dedicated tests.
- NumPy is capped below 2.4 so the documented Python 3.11 mypy target remains compatible
  with installed type stubs.

## Confirmed numerical design

- Horizon sweep: `N = 15, 30, 60, 120, 240` with fixed `Δt = 20 s`.
- Representative D1/D3/D4 case: `N = 120`.
- Gradient descent: step `2 / (λ_max + λ_min)`, relative gradient tolerance `1e-8`,
  maximum 200,000 iterations.
- Conjugate gradient: relative residual tolerance `1e-8`, maximum 354 iterations for the
  representative reduced system.
- No random sampling is used.

## Verified results

- `python -m pytest -q`: 32 passed. Two known non-failing CVXPY canonicalization/
  expression-count warnings remain.
- `python -m ruff check src tests experiments`: passes.
- `python -m mypy src`: passes with NumPy 2.3.5.
- `PYTHONPATH=src python experiments/run_conditioning_study.py`: exits zero with status
  `passed`.
- At `N=120`, the reduced Hessian condition number κ is 1834.790493.
- Gradient descent reaches the fixed tolerance in 16,718 iterations; conjugate gradient
  reaches it in 88 iterations.
- The sparse multiple-shooting Newton solve has stationarity residual `6.82e-13`,
  equality residual `4.47e-14`, and relative objective difference `3.05e-14` from the
  condensed solution.
- The separate constrained `N=60` mission result remains optimal and independently
  verified in `outputs/canonical/result.json`.

## Remaining review items

1. Review the root-level `Project 2 Report.md` in GitHub preview after the changes are pushed, especially display
   math and relative SVG links.
2. Add team-member names or course-section metadata if the instructor expects them; no
   names were available in the repository, so none were invented.
3. Commit and push through the repository workflow selected by the maintainer. Stale
   worktree, branch, pull-request, or remote-move notes are intentionally not carried
   forward here.

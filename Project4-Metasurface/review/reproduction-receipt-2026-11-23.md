# One-command reproduction receipt, 23 November 2026

Command: `python Project4-Metasurface/reproduce.py --destination <new scratch directory>`. It was run from a fresh `git clone` of local commit `da77f37` (branch `project4-rubric-polish`, base `cae98e1`; not pushed). Environment: Python 3.14.4 (the frozen 10 November runs used 3.13.15), NumPy 2.5.4, SciPy 1.18.1, PyTorch 2.14.1+cpu, markdown-it-py 4.2.0, Node 24.18.1. CPU only. Exit code 0.

The command reran, in a fresh copy:

- the frozen FE verification and multistart design;
- the gradient sweep;
- both neural experiments: all 12 networks retrained from the frozen protocols;
- the surrogate–FE bridge and comparison;
- `rubric_studies.py` (including the scaled-constraint re-solve and the Newton-failure diagnosis) and `surrogate_optimizer_loop.py`;
- all 29 Python tests (4 + 7 + 8 + 10, all OK);
- the report and site generator, the artifact audit (passed) and the viewer test (passed).

Agreement with the retained files in this folder:

| Quantity | Largest difference |
|---|---|
| Selected linear / nonlinear designs `c` | 3.1e-15 / 9.6e-13 |
| Selected objectives, phase separations, constraints | ≤ 1e-15 (constraints 2.2e-16) |
| Scaled-constraint runs | same successes (4 of 5) and the same high-low failure |
| Newton-failure diagnosis | same: continuation fails at χ = 0.01 |
| Surrogate-in-optimizer endpoints (60 runs) | 3.2e-11 |
| All 12 networks: every stored metric | ≤ 6.4e-10 absolute |

Differences that are expected and not results:

- Timings, timestamps and file hashes (including the retrained network files).
- The degenerate linear-model `uniform` start took 172 iterations instead of 91. It reached the same poor stationary point ($f=3.86276$, difference 1e-12). The linear `high_low` failure took one iteration more. Ties between starts at the same optimum may be reported under a different start name. Iteration counts at these flat or failing points are sensitive to floating-point round-off. No selected design uses them.
- Finite-difference relative errors at round-off level differ in their leading digits. For example, the V9 maximum at $h=10^{-3}$ is 2.20e-7 retained and 2.15e-7 reproduced. Everything still passes.

This receipt covers a local reproduction, not the published site.

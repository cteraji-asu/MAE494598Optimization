# One-command reproduction receipt, 23 November 2026

Command: `python Project4-Metasurface/reproduce.py --destination <new scratch directory>` on the local revision (branch `project4-rubric-polish`, base `cae98e1`). Environment: Python 3.14.9 (the recorded protocol used 3.13), NumPy 2.5.4, SciPy 1.18.1, PyTorch 2.14.1+cpu, markdown-it-py 4.2.0, Node 24. CPU only. Exit code 0.

The command reran, in a fresh copy:

- the frozen FE verification and multistart design;
- the gradient sweep;
- both neural experiments: all 12 networks retrained from the frozen protocols;
- the surrogate–FE bridge and comparison;
- `rubric_studies.py` and `surrogate_optimizer_loop.py`;
- all 26 Python tests (4 + 7 + 8 + 7, all OK);
- the report and site generator, the artifact audit (passed) and the viewer test (passed).

Agreement with the retained files in this folder:

| Quantity | Largest difference |
|---|---|
| Selected linear / nonlinear designs `c` | 3.1e-15 / 9.6e-13 |
| Selected objectives, phase separations, constraints, KKT multipliers | ≤ 1e-15 |
| All 10 frozen verification values | identical to printed precision |
| Voltage-limit sweep and χ sweep optima, failed-start lists | identical to 8 digits; same failures |
| Bound-relaxation re-solves | 1e-15 |
| Surrogate-in-optimizer endpoints (60 runs) and FE reference optimum | 3.2e-11 |
| All 12 networks: reflection p95, feasible retained, false feasible | ≤ 4.4e-16; identical counts |

Differences that are expected and not results:

- Timings, timestamps and file hashes.
- The degenerate linear-model `uniform` start took 172 iterations instead of 91, reaching the same poor stationary point ($f=3.86276$, difference 1e-12). The linear `high_low` failure took 23 instead of 22. Iteration counts at these flat or failing points are sensitive to floating-point round-off. They are not used by any selected design.
- Gradient-check relative errors near round-off differ in the second digit (for example V9 maximum 2.40e-5 versus 2.36e-5). All still pass.

This receipt covers a local reproduction, not the published site.

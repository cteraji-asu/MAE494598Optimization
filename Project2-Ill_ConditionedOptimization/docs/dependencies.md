# Dependency and Platform Review

The confirmed baseline supports CPython 3.11–3.13 on macOS and Linux. Direct
dependencies are bounded in `pyproject.toml`; the installed environment used for the
recorded results was inspected on 2026-09-28. NumPy is capped below 2.4 because later
stub syntax is incompatible with the project's Python 3.11 mypy target.

| Scope | Package | Installed version | Purpose | License metadata |
|---|---|---:|---|---|
| Runtime | NumPy | 2.3.5 | Dense arrays and linear algebra | BSD-3-Clause text |
| Runtime | SciPy | 1.18.1 | Matrix exponential and sparse solve | BSD-3-Clause text |
| Runtime | CVXPY | 1.9.3 | Convex modeling adapter | Apache-2.0 |
| Runtime | Clarabel | 0.11.1 | Conic solver backend | Apache-2.0 |
| Runtime | Matplotlib | 3.11.2 | Reproducible SVG plots | Matplotlib license |
| Runtime | PyYAML | 6.0.3 | Safe YAML configuration parsing | MIT |
| Development | Autograd | 1.9.1 | Independent derivative checks | MIT |
| Development | pytest | 8.4.2 | Automated tests | MIT |
| Development | mypy | 1.20.2 | Static type checks | MIT |
| Development | Ruff | 0.16.9 | Lint and formatting checks | MIT |

Setuptools and Wheel are build-system dependencies. Setuptools reports MIT license
metadata in this environment; Wheel does not expose a license field in its installed
package metadata, so its upstream license must be checked when performing a release
compliance review. This inventory is not legal advice and does not replace organization-
specific security or license approval.

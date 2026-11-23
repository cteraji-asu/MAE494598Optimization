# Project 4: nonlinear switched-line design

A verified 20-variable finite-element design study, with implicit adjoints, a nonlinear capacitive state equation, a linked WebGL comparison and a controlled two-PINN investigation.

Start with [report.md](report.md), the [rubric crosswalk](RUBRIC-CROSSWALK.md), and [two-PINN findings](two-pinn-findings.md). This is a synthetic continuation of Project 3, not calibrated hardware. Independent student benchmark derivation and acceptance of this specific custom formulation remain human review items. No coursework has been submitted.

## Review locally

From this repository, run a local server:

```sh
python -m http.server 8000
```

Then open `http://localhost:8000/Project4-Metasurface/preview.html`. This standalone full-report preview and the Jekyll page load the same `assets/results.json`. Opening the HTML through `file://` will not reliably allow JSON fetches.

`index.md` is the GitHub Pages source; `site/index.html` is a viewer-only preview. The static viewer has no external JavaScript/CDN dependency. It requires WebGL. Desktop and phone-width QA screenshots and limitations are in [site/QA.md](site/QA.md). Browser UI tests are not a substitute for checking the deployed site in a private window.

## Reproduce everything with one command

Use Python 3.13 with the versions in requirements.txt. Install dependencies from their official package registries in a dedicated environment. The scientific code does not download models or data at runtime.

```sh
python Project4-Metasurface/reproduce.py
```

This creates a **new sibling directory**, copies only the necessary code and frozen protocols, runs the FE design, both PINN studies and tests, and regenerates the numerical report/plots/preview. Existing results are never overwritten. A destination that already exists is rejected.

For separately provisioned SciPy and PyTorch environments:

```sh
python Project4-Metasurface/reproduce.py --core-python PATH_TO_SCIPY_PYTHON --pinn-python PATH_TO_TORCH_PYTHON --destination PATH_TO_NEW_DIRECTORY
```

Use `--prepare-only` to create and inspect the reproduction plan before running it. CPU timings and timestamps will differ. Frozen datasets, seeds, architectures, update budgets, objective formulas and tolerances remain unchanged. The original hard-routing study is preserved separately from the follow-on smooth-blending study.

## Audit without fitting

```sh
python -m unittest discover -s Project4-Metasurface/tests -p test_wave_fem.py -v
python -m unittest discover -s Project4-Metasurface/tests -p test_two_pinn.py -v
python -m unittest discover -s Project4-Metasurface/tests -p test_smooth_pinn.py -v
python Project4-Metasurface/code/build_report.py
python Project4-Metasurface/code/audit_artifacts.py
```

Run the core test in a NumPy/SciPy interpreter and PINN tests in a NumPy/PyTorch interpreter if using separate environments. `build_report.py` also requires markdown-it-py. The tests independently check field/reference algebra, derivatives, source hashes, dataset separation and checkpoint seals. [review/scientific-audit.json](review/scientific-audit.json) records an additional agent review, not student verification. A complete fresh reproduction also passed all 19 tests and matched every scientific result, including all 12 trained networks. Only runtimes, timestamps and dependent file hashes differ; see [review/reproduction-audit.json](review/reproduction-audit.json).

## What is in the repository

- `code/wave_fem.py`: own split P1 weak-form solver, analytic real Newton tangent and implicit adjoints.
- `code/verify_fem.py`: exact/reference, manufactured nonlinear, balance, phase-invariance, Newton, gradient and Taylor checks.
- `code/run_design.py`: fixed multistart protocol, KKT reconstruction, cross-evaluation and mesh-refinement audit.
- `assets/results.json`: canonical FE results, all selected fields/history and retained successful/failed starts.
- `code/two_pinn_study.py`: matched monolithic/hard-specialist experiment.
- `code/smooth_pinn_study.py`: separately frozen continuous-blending follow-up.
- `assets/*pinn*.json`: plans, seals, model weights, measurements and derivative audits.
- `code/build_report.py`: data-generated report, SVG figures and full local preview.
- `index.md`, `site/`: GitHub Pages report shell and custom dependency-free WebGL viewer.

No Project 3 file is modified. No hidden credentials, private correspondence or unrelated personal material are part of this project.

## Publishing and submission are separate

The repository did not have GitHub Pages enabled when inspected on 10 November 2026; the connected account has push permission but not repository-administration permission. The prepared page can be served from the selected branch's repository root once a repository admin enables Pages. Its expected path is `/MAE494598Optimization/Project4-Metasurface/`, but it is **not a verified live URL** until deployment is complete.

Do not treat a GitHub Markdown preview as a working WebGL website. After authorized deployment, check the public page in a private window, its math, relative links, two-state fields, mobile layout and controls. Then the team can provide the repository and live-site links to Canvas. This project does not submit anything automatically.

## 16 November rubric audit additions

The reproduction command now also regenerates the supplemental multi-design/direction finite-difference evidence and incorporates its table into the report. Earlier diagnostic step-window failures remain in `review/`; the later wider window is an adaptive check, not a preregistered experiment. Original FE and PINN results were not overwritten.

Run `node Project4-Metasurface/tests/test_viewer_ledger.cjs` for the separate viewer-ledger component regression. It executes the actual viewer against retained results and checks individual initial/selected constraint statuses. This fixture is not a live-browser or deployed-site check. Node is optional for this supplemental UI test, not required by the scientific reproduction.

Current publication caveat: the earlier Pages-setting observation is historical. A later deployment entry was visible, but this Project4 page has not been verified live. Publishing remains incomplete; do not use the expected URL as proof.

## Restricted surrogate bonus comparison
The reproduction runner now also exports saved-model gradients and runs the own-P1-FE bridge and exact-coordinate comparison. See review/surrogate-bonus-audit-2026-11-16.md. This is the linear Project3 moving-switch family, not a surrogate for the20-variable nonlinear core. The saved networks remain inaccurate; the comparison is evidence, not guaranteed bonus credit. All three new stages were executed separately and the combined preparation plan checked; full training was not repeated for this follow-up.

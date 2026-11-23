# Project 4: designing a switched line for 180° reflection

A 20-variable PDE-constrained design study that extends our Project 3 metasurface problem. It uses our own P1 finite-element solver with a nonlinear (N2) state equation, adjoint gradients, SLSQP with a KKT reading, and a live WebGL comparison of the initial and optimized designs. New PINN surrogates of Project 3's restricted problem are also run inside an optimizer and compared with the finite-element reference.

Start with the rendered page (`index.md`, or `preview.html` locally) or [report.md](report.md). The [rubric crosswalk](RUBRIC-CROSSWALK.md) maps each rubric row to its evidence. This is a synthetic reduced model, not calibrated hardware. No coursework has been submitted.

## Review locally

From the repository root:

```sh
python -m http.server 8000
```

Then open `http://localhost:8000/Project4-Metasurface/preview.html`. `preview.html` is a local stand-in for the GitHub Pages build of `index.md`: the generator embeds the identical `site/report-body.html` that `index.md` includes. Whether Pages renders this revision identically is unverified until it is published. Opening through `file://` blocks the JSON fetch. Math is typeset by MathJax 3.2.2 (pinned, from jsDelivr). The 3D viewer has no third-party dependency and falls back to 2D profiles without WebGL (`preview.html?nowebgl=1` forces the fallback).

## Reproduce everything with one command

The pinned NumPy, SciPy, PyTorch and markdown-it-py versions in `requirements.txt`. The frozen 10 November runs used Python 3.13.15; the 23 November runs and reproduction used Python 3.14 with the same pinned packages (versions are recorded in each JSON's provenance). Node is optional and only used for the viewer test.

```sh
python Project4-Metasurface/reproduce.py
```

This command creates a **new sibling directory**, copies only code and frozen protocols, and then reruns, in order:

1. FE verification and the frozen multistart design (`code/run_design.py` → `assets/results.json`);
2. both neural experiments and their audits;
3. the gradient sweep and the surrogate–FE bridge;
4. the 23 November supplemental runs (`code/rubric_studies.py` → `assets/rubric-studies.json`, `code/surrogate_optimizer_loop.py` → `assets/surrogate-optimizer-loop.json`);
5. every test;
6. the report and site generator (`code/build_report.py`), the artifact audit and the viewer test.

Retained results are never overwritten. Use `--prepare-only` to inspect the plan. With separate environments, use `--core-python` (SciPy) and `--pinn-python` (PyTorch **and** SciPy). Timings and timestamps differ between machines.

## Check without retraining

```sh
cd Project4-Metasurface
python -m unittest discover -s tests -p "test_*.py" -v   # 29 tests: FE, both PINN studies, new evidence
python code/audit_artifacts.py                          # hashes, feasibility, links, no Liquid
node tests/test_viewer_ledger.cjs                       # real viewer vs results.json and report table
python code/build_report.py                             # regenerate report.md, preview.html, figures
```

## What is where

| Path | Contents |
|---|---|
| `code/wave_fem.py` | Own split P1 weak-form solver, Newton with exact real tangent, implicit adjoints |
| `code/verify_fem.py`, `code/run_design.py` | Frozen verification ladder and multistart SLSQP design with KKT reconstruction |
| `assets/results.json` | Frozen 10 Nov design study: fields, histories, all starts including failures |
| `code/rubric_studies.py`, `assets/rubric-studies.json` | 23 Nov: exact nonuniform-loading and lossless rungs, gradient checks, cost scaling, multiplier re-solves, post hoc voltage-limit and χ sweeps |
| `code/surrogate_optimizer_loop.py`, `assets/surrogate-optimizer-loop.json` | 23 Nov: saved Project 3-family surrogates inside SLSQP versus the FE adjoint |
| `code/two_pinn_study.py`, `code/smooth_pinn_study.py`, `assets/*pinn*` | Frozen neural experiments, weights, seals and audits |
| `code/build_report.py` | Generates `report.md`, `site/report-body.html`, `preview.html`, every SVG figure |
| `index.md`, `site/` | Pages shell, viewer (`viewer.js`), styles; `site/index.html` redirects to the combined page |
| `review/` | Earlier audits and the 23 Nov rubric scorecard |

No Project 3 file is modified.

## Publication status

Commit `8eac124` (the 16 November version) was mirrored to `docs/Project4-Metasurface/` on `main` and published at `https://cteraji-asu.github.io/MAE494598Optimization/Project4-Metasurface/`. **This revision is local and unpublished.** It must be re-verified on the public site in a private window after any approved publication.

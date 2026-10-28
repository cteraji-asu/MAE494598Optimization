# Project 3: finite switch coupling and reliable screening

Current rehearsal: [40-beat Light Mode presentation, PDF and editable Manim source](PRESENTATION.md).

The core deliverable is [report.md](report.md), a single Markdown report with its six required sections and runnable scientific code. Start there, then read [researcher-memo.md](researcher-memo.md), [worked-verification.md](worked-verification.md).

This is a synthetic frequency-domain finite-switch case, selected as Path B. Optimizer choice, training objective and controlled missing input support causally affect attained error under the matched conditions reported. All six new blocked-cohort gates fail; the three supervised off-grid gates pass. Neither useful hardware accuracy nor a successful remedy is claimed. Hardware validation is a limit on hardware claims, not a requirement to replace the permitted synthetic case.

## Review saved results without fitting

Python 3.13, CPU PyTorch 2.14.1+cpu and NumPy 2.5.4 were used. Pillow 12.3.0 is optional for scientific plots and its portability test. requirements.txt includes the core pins and official CPU wheel index. Installation is an explicit user action, not performed by this review. The authorized [approved briefing](sources/interview/Post_Interview_Briefing.md) and [recording](<sources/interview/Project 3 Interview Audio.m4a>) are copied exactly from the existing repository inputs. [Provenance and attribution](sources/interview/README.md) retain their origin. Audio is unnecessary for running the synthetic numerical model; private ASR/correspondence are excluded.

From this directory in the existing scientific environment:

```shell
python -m unittest discover -s tests -v
python code/audit_saved_results.py
```

The second command independently evaluates saved weights and wave references and never trains. With Pillow available, regenerate core plots from the retained CSV/JSON:

```shell
python code/plot_switched_surrogate.py
python code/plot_gap_diagnosis.py
```

The gap study contains three nested sampling widths, two matched objectives and one retained seed. Existing primary, optimizer, exact-boundary and residual-budget evidence remains under outputs/. Read each ERRATUM.md alongside its unchanged frozen protocol. The lossless reference and one saved PINN output error are worked through explicitly in the report.

## Isolated reproduction commands

Do not run fresh-output training followed by analysis of a different canonical directory. The helper below copies prerequisites and the fixed protocol to a new, nonexistent workspace, omitting completed results only for the selected study. It does not execute training or delete anything. It refuses a destination inside or containing the canonical project.

```shell
python code/prepare_reproduction.py --study primary --destination ../reproduce-primary
python code/prepare_reproduction.py --study optimizer --destination ../reproduce-optimizer
python code/prepare_reproduction.py --study boundary --destination ../reproduce-boundary
python code/prepare_reproduction.py --study residual --destination ../reproduce-residual
python code/prepare_reproduction.py --study gap --destination ../reproduce-gap
```

Each prints a REPRODUCTION-PLAN.json with commands and the required working directory. Only after deliberately choosing to reproduce that study, change into its prepared directory and use the printed commands. Optimizer: optimizer_control.py. Exact boundaries: hard_boundary_control.py then evaluate_hard_boundary.py. Residual attribution: run_residual_error_budget.py. Gap/objective: gap_objective_diagnosis.py. Primary: switched_surrogate.py then its summary and plot scripts. All analysis therefore reads the same isolated output tree. Model training is not part of the default saved-result audit.

The original protocols and all failed results remain unchanged. Project-scoped `.gitattributes` disables line-ending conversion because frozen receipts hash exact source/protocol bytes. A normal Windows clone with system `core.autocrlf=true` otherwise changes those bytes; the audit verifies exact checkout bytes and all five isolated freeze-only paths without training. Publication-only prose redactions, if present, have their own digest receipt. An isolated boundary or residual reproduction may amend only copied source-hash metadata for those documented nonnumeric redactions, retaining frozen-protocol.original.json. It refuses unexplained source changes and never rewrites the canonical frozen protocol.

## Human evidence and publication status

The user/team confirmed researcher approval of the brief on 28 October 2026 and explicitly authorized public links and exact copies of the existing brief/audio. This is team-reported approval, not a reproduced written reply or approval of the model/results. Contact/reservation details and memo delivery still require actual team evidence. The memo remains an unsent draft; no researcher message is authorized by this audit.

The reported revised deadline is October 28. The linked Canvas announcement could not be read through the available web tool, so its exact time and scope remain unverified here.

The core project was published on 21 October at commit `5720474`. This audit is prepared from that current public base, preserving unrelated teammate files and frozen results. It corrects publication/review status, makes the permitted interview evidence discoverable, protects exact source bytes across Git checkouts, and aligns the light rehearsal presentation with the final controlled studies. The previous 37-beat light edition and dark editions are retained locally as superseded presentation versions. Raw ASR, correspondence, local receipts and render caches are excluded from the public change set. Coursework submission remains a team action.

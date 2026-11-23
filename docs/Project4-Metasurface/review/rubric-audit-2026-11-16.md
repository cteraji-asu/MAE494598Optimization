# Project 4 rubric audit: 16 November 2026

## Method choice
The primary assignment (`docs/project4.md`, instructor source blob `4bffd93c866a1b02352cc969737467793037ca01`) requires an owned finite-element solver and adjoint gradients, including Project3 extensions. A PINN/PINO inside the optimizer is an optional bonus, not the required baseline. The retained networks are supporting restricted-design experiments, not a full 20-variable surrogate optimizer. Their failed reliability gates remain negative findings. No bonus score is assumed.

## Verified and improved in this pass
- Fresh existing tests:4 core numerical tests and15 saved-PINN/protocol tests passed. These were replay/verification, not new network training.
- Added `code/verify_gradient_sweep.py`:45 checks across3 interior designs,3 directions and5 metrics pass accuracy and pre-roundoff second-order convergence. Source-bound evidence: `gradient-sweep-final-2026-11-16.json`. Earlier shorter step windows and failures are retained. The diagnostic range was extended after observing numerical-floor effects; it was not preregistered. Solver, seeds, designs, directions and criteria were unchanged.
- Report generator now reads that evidence; reproduction runs the new check in a fresh directory. Prepare-only reproduction plan verified. Full retraining/reproduction was not repeated in this pass.
- Viewer now shows individual constraint pass/fail for both initial and selected designs. `tests/test_viewer_ledger.cjs` executed the actual viewer against retained data: failing4-versus5-column check before repair, passing9 rows and3 headers after. An independent code reviewer also ran it. This is component evidence, not fresh live-browser QA.
- Regenerated report and preview. Artifact audit passed. Original `assets/results.json` SHA256 remains `12585b2d49f43d40f85b9a4a83e0f9eb22f3bb0c8f3020cdea906594001c67b1`.

## Remaining credit risks, not invented fixes
1. Exact synthetic loading law and illustrative engineering limits have not been verified as accepted by the instructor. General encouragement to extend Project3 does not establish that exact approval.
2. Student-independent benchmark derivation before agent test access cannot be manufactured retrospectively. Agent verification must retain its attribution.
3. The viewer openly uses fixed1D reduced-model geometry with graphical loading heights. Instructor acceptance of this interpretation of true geometry remains unverified; arbitrary heights must not be presented as manufactured dimensions.
4. Public Project4 site, private-window behavior and deployment remain unverified. Publishing is incomplete. Only a `.gitignore` was committed on the dedicated remote branch during the earlier attempt; this audit did not publish more files.
5. No Canvas submission or participation-sheet update performed. No grade or full-marks prediction made.

The unchanged linear/nonlinear optimal design is not itself a rubric failure: the assignment permits this if the compared responses and reasoning are evidenced. Preserve that result rather than tuning the problem until a more dramatic answer appears.

## Fresh local browser follow-up
Real desktop Chrome loaded the local report over loopback HTTP. Both WebGL views rendered; OFF-state and element80 controls changed displayed values; initial constraint failures and selected passes were visible. Expanding cell bounds exposed an existing bug: upper slack showed the bound2.5 instead of2.5 minus cell loading. Fixed the subtraction, added a20-cell regression, and verified corrected browser values (cell1:2.0000; cell7:1.430e-13). Original numerical JSON unchanged. No captured console errors. This was local desktop QA, not mobile/private-window/public deployment certification. First server-start attempt refused connection; persistent server then worked. An initial label-based selector had no match; role-based selection worked. No uncertain external action was retried.

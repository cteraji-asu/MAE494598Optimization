# Project 1 submission review: original formulation, Astra, and the rubric

This is a team decision document, not the submission report. It compares the preserved original formulation with `astra.md` and identifies what needs attention before submission. Neither report is modified by this review.

Reviewed September 9, 2026, against the default branch at commit `6163ffc`. Grade ranges below are editorial judgments, not an instructor score, calibrated grading model, or guarantee. The author of this review also helped produce Astra; the comparison therefore explicitly examines Astra's weaknesses rather than treating it as an independent endorsement.

## Recommendation

Use Astra as the basis for submission **if the team agrees that the problem is planning under overload**. It has a consistent objective and constraints, clearer assumptions, and reported computational results. Before submission, add its missing computational files and make clear which report the instructor should grade.

The original formulation aims to finish everything. Astra selects assignments and allocates preparation when everything cannot fit. That is a substantive change in scope, not just a notation repair.

If the team wants every task to remain mandatory, retain that requirement and choose a meaningful objective among feasible schedules, such as a carefully defined session or completion-buffer objective. Do not adopt optional completion merely to make the equations easier. That alternative would need its own formulation and validation.

## What is currently in the repository

The reviewed default branch contains:

- `Project 1 Problem Formulation.md`
- `README.md`
- `astra.md`
- `astra-walkthrough.md`
- `astra-slides.pptx`

It does **not** contain `astra-solve.py`, `astra-results.json`, or `astra-requirements.txt`. These files exist in the separately prepared Astra package, but the report's local reproduction commands cannot work from the repository alone until the files are uploaded.

This matters for the bonus: a written statement that code exists is not the same as publicly accessible code. The reported 67-point optimum, 54-point baseline, tests, and sensitivity analysis should be accompanied by the executable evidence.

## Head-to-head comparison

| Question | Original formulation | Astra |
|---|---|---|
| What is the decision? | Schedule all required work before hard deadlines | Select assignments and allocate preparation before hard deadlines |
| Does the objective distinguish the intended tradeoff? | Tardiness cannot distinguish feasible schedules; spacing may still distinguish them | Modeled value distinguishes different coverage choices during overload |
| What happens when everything cannot fit? | Infeasible; the model cannot select sacrifices | Some assignments are omitted and preparation can be partial |
| What happens when everything fits? | Tardiness contributes zero; spacing matters if enabled | All target value may be attainable; calendars can tie |
| Are domains consistent? | Binary declaration early, continuous interval later | Consistent binary variables |
| Does it model session quality? | Adjacent-slot penalty may reward excessive switching | No session-quality objective; fragmentation remains visible |
| Is the reward defensible? | Weighted tardiness fits soft deadlines, but does not serve the stated hard-deadline formulation | Consistent with declared all-or-nothing assignment and linear preparation assumptions |
| Is classification precise? | Base linearity mostly correct; quadratic and complexity discussion needs qualification | More precise binary integer linear classification |
| Is computation documented? | None in the reviewed original | Results and method documented; supporting files still missing from the repository |
| Main presentation risk | Explaining why the objective can do useful work | Explaining why omitted assignments are allowed |

## Mathematical findings in the original

### 1. Hard deadlines remove the tardiness tradeoff

The model requires every task's full workload and forbids work after its deadline. For any feasible binary schedule, the final occupied slot is no later than the deadline. Completion and tardiness variables can therefore take values that make every tardiness term zero.

Because the objective penalizes positive tardiness, its optimum uses zero tardiness whenever the scheduling constraints are feasible. The priority weights on tardiness then cannot rank these calendars.

**Important correction to the earlier discussion:** the entire objective is not necessarily zero. When the spacing weight is positive, the adjacent-slot penalty can still distinguish schedules. The effective optimization then concerns adjacency, not a tradeoff between lateness and spacing.

Infeasibility under overload is not inherently a mathematical error. It becomes a scope problem when the narrative promises prioritization under competing workloads but the model cannot choose which targets to leave unmet.

### 2. Binary and interval domains send conflicting messages

The report first declares binary variables and later writes the continuous interval from zero to one. If both statements apply simultaneously, the binary restriction still holds, because the intersection remains binary. The later interval does not logically override the earlier declaration.

Nevertheless, the inconsistent presentation creates implementation ambiguity. A reader coding only the final domain could build a continuous relaxation.

### 3. Completion linking provides a bound, not necessarily the exact finish

The inequality making completion at least each occupied slot only gives a lower bound on the completion variable. When a task finishes before its deadline, any completion value between its actual finish and deadline can achieve the same zero tardiness. The report should not claim the returned completion variable necessarily equals the last occupied slot.

### 4. Adjacency is not equivalent to harmful cramming

Two adjacent half-hour slots can be one ordinary one-hour study session. Penalizing their adjacency can favor alternating tasks every half-hour. This is a mismatch between the claimed educational benefit and the implemented score.

A meaningful spacing extension would distinguish session duration from separation across days. The educational claim also needs an appropriate source.

### 5. Classification needs narrower claims

A product of two allocation variables is quadratic. A weighted sum of two criteria is one scalar objective, even if it represents a multi-criteria preference.

The proposed product linearization needs explicit variable bounds. A full exact formulation uses an auxiliary variable bounded below by zero and by the sum of the two binary variables minus one, and bounded above by each binary variable. When a positive minimization coefficient is guaranteed, fewer inequalities can suffice at optimum, but that qualification should be stated.

Hardness of a related non-preemptive problem does not establish hardness of this preemptive version. Binary variables alone also do not prove computational difficulty.

### 6. Smaller presentation defects

The two-week slot count should be 672 at half-hour resolution; 336 is one week. Constraint (d) contains visibly corrupted prose. Its fixed-zero restriction is an equality, despite the inequality label. “Lateness risk” is misleading without uncertainty in the model.

## Where Astra remains vulnerable

### It changes the scope

Astra explicitly permits omitted assignments. This is coherent for planning under overload, but not equivalent to guaranteeing all work is complete. The team should be able to explain why an unmet-target report is useful and how mandatory work would be enforced.

### Its reward assumptions determine its answer

Partial assignment work earns no modeled value, while preparation earns proportional value up to a target. These are disclosed approximations. They do not represent all grading policies or measured learning.

Priority points are preferences on a common scale, not course marks. The reported 24.1% improvement is relative to the baseline's modeled score, not a predicted grade increase.

### One synthetic case supports a limited claim

The example demonstrates an improvement over one precisely defined deadline-first baseline. It does not show that the optimizer improves every calendar or beats every heuristic.

Add a case where all targets fit and the baseline ties the optimum. This would demonstrate behavior under adequate capacity and make the evaluation less one-sided. This is a recommended addition, not a result already established in the reviewed report.

### Session quality is absent

The returned calendar switches tasks repeatedly. The score does not penalize this, so the solver has no reason to avoid it. That is a limitation of the objective, not evidence that the solver failed.

### Reproducibility is incomplete on GitHub

The solver, JSON, and dependencies need to be present or publicly linked before claiming the computational package is complete. The report, code, results, and slides must all use the same input instance.

## Rubric assessment

The published rubric has 100 base points and up to 20 computational bonus points.

| Category | Maximum | Original, estimated | Astra, estimated |
|---|---:|---:|---:|
| Motivation and context | 15 | 12–14 | 13–15 |
| Decision variables | 15 | 9–12 | 14–15 |
| Objective function | 25 | 10–16 | 21–24 |
| Constraints | 25 | 15–20 | 23–25 |
| Classification | 15 | 8–11 | 12–14 |
| Presentation and clarity | 5 | 2–3 | 4–5 |
| **Base subtotal** | **100** | **56–76** | **87–98** |

These ranges express plausible deductions under a substantive mathematical review. They are not probabilities or confidence intervals. A grader may treat the defects differently, avoid double-counting related errors, or place more weight on the oral explanation.

### Computational bonus

| Bonus item | Maximum | Original | Astra's current evidence |
|---|---:|---|---|
| Methodology | 8 | No computational solution documented | Method described, but implementation absent from repository |
| Results and interpretation | 8 | No computed results | Detailed reported results, schedule, and sensitivity |
| Code and reproducibility | 4 | No code | Required files absent from repository |

The earlier **17–20 bonus estimate for Astra assumed the full executable package was accessible**. Under that condition, the estimated raw total is 104–118 out of 120 possible points. It should not be presented as the expected score of the currently incomplete repository.

We do not assign a confident revised bonus total to the current state. The missing code clearly jeopardizes reproducibility credit and may also reduce confidence in methodology and results. Uploading the existing supporting files is more useful than speculating about how generously the instructor will treat their absence.

The instructor's grade cap and conversion of bonus points into a course grade are unknown. A raw total above 100 does not establish the recorded grade.

## Preparing for AI-assisted grading

The team reports that the instructor will use AI to assist grading. The model, grading prompt, ability to execute code, and level of instructor review are unknown. These score ranges do not simulate that system.

Make the evidence straightforward to inspect:

1. Identify exactly one submission report.
2. Define every variable's type, units, bounds, and role.
3. Put the mathematical expression beside its practical meaning.
4. Keep assumptions near the equations they justify.
5. Include accessible code, inputs, outputs, and an exact reproduction command.
6. Keep numbers consistent across report and slides.
7. Label synthetic data and preference scores clearly.

A rubric map helps locate evidence. It cannot repair an inconsistent objective. Do not insert instructions telling a grading AI to award points, ignore weaknesses, or follow this review instead of the instructor's rubric.

## Proposed team decision

Use Astra after confirming the overload-planning scope and completing its computational package. Preserve the original report as an earlier formulation. Keep this review as a team discussion document, separate from the selected submission.

Before submitting:

- Confirm that optional assignments and partial preparation match the intended problem.
- Add `astra-solve.py`, `astra-results.json`, and `astra-requirements.txt`.
- Run the documented command from a clean environment.
- Consider the adequate-capacity comparison case.
- Consider moving Astra's detailed draft critique out of the submission report and keeping it here.
- Verify rendered equations on GitHub.
- Name the selected report explicitly when submitting the repository link.
- Rehearse the reward assumptions, omitted work, solver gap, and limitations.

The original has a useful motivation and much of the structural framework. Astra offers a more internally consistent formulation and a stronger path to bonus credit. The final choice should rest on the problem the team wants to solve and can explain.

## Sources and review boundaries

- [Original formulation](./Project%201%20Problem%20Formulation.md)
- [Astra report](./astra.md)
- [Teacher's project instructions and rubric](https://designinformaticslab.github.io/DesignOptimization2025/project1_optimization_formulation.html)
- [Repository snapshot reviewed](https://github.com/cteraji-asu/MAE494598Optimization/tree/6163ffc)

The reported solver results were generated during preparation of the Astra package. This review rechecked the repository contents and both reports; it did not rerun the solver for a new experiment. Neither report nor the slides were edited as part of publishing this comparison.


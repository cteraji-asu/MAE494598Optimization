# Astra walkthrough: building the scheduler from first principles

This guide explains the model in `astra.md` and the results from `astra-solve.py`. Read Sections 1–6 to understand the idea, Sections 7–11 to reproduce and defend it, and Section 12 before presenting. The original team Markdown remains unchanged.

## 1. The actual problem

Imagine looking at your calendar on Sunday. You have 14 hours available next week. Your assignments and intended exam preparation require 22 hours. No arrangement of calendar blocks can turn 14 into 22.

There are two separate questions:

1. What work can fit before its deadline?
2. Of those possible plans, which protects what you value most?

The first question supplies the rules. The second supplies the score. Optimization chooses the highest-scoring plan that obeys the rules.

The result may omit something important. That is an honest warning about an overloaded week. It should prompt a real-world decision about adding time, reducing scope, getting help, or changing priorities.

**What you should be able to explain:** the optimizer rearranges and selects work. It cannot create time or guarantee academic success.

## 2. Build backward from the output

Our target is a usable calendar: which task do I work on at each available time?

To select a calendar, we need a way to compare calendars. We choose modeled priority value earned before deadlines.

To calculate that value, we need to know which assignments finish and how much exam preparation happens.

To know those things, we need to count the time blocks allocated to each task.

That takes us to the smallest decision: **Does this task occupy this time block?**

We call that decision $x_{it}$. The letters below it are addresses: task $i$, time $t$. They do not mean multiply $i$ by $t$.

$$x_{it}=1\text{ means yes},\qquad x_{it}=0\text{ means no}.$$

## 3. The calendar is a matrix

Here is a small calendar with two tasks and three available slots:

| Task / slot | 1 | 2 | 3 | Row total |
|---|---:|---:|---:|---:|
| A | 1 | 1 | 0 | 2 |
| B | 0 | 0 | 1 | 1 |
| Column total | 1 | 1 | 1 | |

You work on A in slots 1 and 2, then B in slot 3. A receives two slots. B receives one. Every column contains at most one 1, so no time is double-booked.

This is the useful connection to linear algebra: a matrix can organize the decisions, and row/column sums count allocated work. You do not need eigenvalues, inverses, or determinants to understand the formulation.

### Reading the symbols

| Symbol | Read it as | Example |
|---|---|---|
| $i$ | Which task? | Task A |
| $t$ | Which slot? | Slot 3 |
| $\sum_t x_{it}$ | Add across one task's row | Total time given to A |
| $\sum_i x_{it}$ | Add down one time column | Tasks occupying slot 3 |
| $\forall i$ | Repeat this rule for every task | No special exceptions |
| $\le$ | At most | Zero or one task |
| $=$ | Exactly | Precisely six work slots |
| $\in\{0,1\}$ | Must be zero or one | Whole-block decisions |

### Why braces matter

$x\in\{0,1\}$ gives two choices. $x\in[0,1]$ gives every number between them, including 0.4. Our calendar uses whole slots, so we use braces.

**Quick check:** If a task row is $[1,0,1,1]$, how many hours did it receive with 30-minute slots?

<details><summary>Answer</summary>

Three ones mean three slots, or 1.5 hours. The gap does not erase earlier work. The model allows a task to pause and resume.

</details>

## 4. Separate facts from choices

The optimizer does not decide when your teacher releases homework or how long an hour is. Those are inputs, called parameters.

For each task:

- $p_i$: how many slots you estimate it needs;
- $r_i$: first slot you may use;
- $d_i$: last slot you may use;
- $v_i$: how much you value achieving the target.

For each slot, $a_t$ tells us whether you are free: 1 for available, 0 for busy.

The optimizer chooses $x_{it}$ and, for assignments, $y_i$. The latter is a completion switch: 1 selects the assignment for completion; 0 leaves it out.

### Convert clock times carefully

We start the week Monday 00:00. One slot is half an hour. Monday 18:00–18:30 is slot 37 because 36 earlier slots cover the first 18 hours. Tuesday's slots are 48 higher. Sunday 19:30–20:00 is slot 328.

A deadline of $d_i=88$ allows work through Tuesday 20:00. It does not allow a block starting at 20:00. A release at Wednesday 00:00 gives $r_i=97$.

For a 19:45 deadline, do not count the whole 19:30–20:00 block. Either use a finer grid or stop at the previous complete slot. Similarly, a task released at 18:10 cannot use the whole 18:00–18:30 slot.

**Quick check:** How many 30-minute slots are in one full week?

<details><summary>Answer</summary>

$7\times24\times2=336$. That includes sleep and classes. Availability sets those unusable slots to zero. Two weeks contain 672 slots.

</details>

## 5. Derive each rule from a real restriction

### Rule 1: a chosen assignment must finish

Suppose a report needs six slots. If we choose it, its row must contain six ones. If we skip it, its row must contain zero ones.

The equation is:

$$\sum_t x_{it}=p_i y_i.$$

When $y_i=1$, the right side is $6(1)=6$. When $y_i=0$, it is $6(0)=0$. One equation handles both cases.

Why not allow three slots of unfinished work? Because this version assigns no reward to a partly completed assignment. That is a modeling assumption. If partial submissions earn credit, we should change the reward and effort rules.

### Rule 2: preparation can be partial

Preparing for half of a target can still help. A preparation row can therefore contain anything from zero to $p_i$ ones:

$$\sum_t x_{it}\le p_i.$$

There is no assignment-completion switch for preparation. We assume every preparation slot contributes equally until the target. Actual learning is more complicated.

### Rule 3: one brain, one slot

Count the tasks in each time column:

$$\sum_i x_{it}\le a_t.$$

If free, the right side is 1. If busy, it is 0. This handles availability and double-booking together.

### Rule 4: work must lie inside its window

$$x_{it}=0\quad\text{when }t<r_i\text{ or }t>d_i.$$

Anything outside the task's window is forbidden. This is an equality restriction, even though it describes a time range. Studying after an exam cannot count toward preparation for that exam.

### Rule 5: whole slots

$$x_{it},y_i\in\{0,1\}.$$

There is no half-completed assignment switch and no simultaneous 0.5/0.5 split within a slot.

**Understanding check:** Why could the original model have no solution during an overloaded week?

<details><summary>Answer</summary>

It demanded every task's full effort before its deadline, even if too few slots existed. The new model permits omissions and partial preparation, so it can report the best achievable coverage. Making omissions possible changes the scope explicitly; it does not magically meet every requirement.

</details>

## 6. Build the score

### Assignment value

If A is worth five points, completing it earns $5y_A$. Since $y_A$ is zero or one, it earns zero or five.

### Preparation value

If B's two-slot preparation target is worth four points, each slot earns $4/2=2$ points. One slot earns two. Two slots earn four.

Putting every task together:

$$V=\sum_{i\in A}v_i y_i+\sum_{i\in E}\frac{v_i}{p_i}\sum_t x_{it}.$$

Read it aloud: “Add the value of completed assignments. Then add the proportional value of the preparation we scheduled.”

The optimizer maximizes $V$. More is better **under our chosen preference scale**.

### A complete hand-solvable example

There are three slots. Assignment A needs two slots, earns five points, and can use slots 1–3. Preparation B has a two-slot target, earns four points for full coverage, and is available only in slots 2–3.

| Legal choice | Score |
|---|---:|
| Finish A, no preparation | 5 |
| Skip A, prepare B fully | 4 |
| Finish A and prepare B for one slot | **7** |
| Do nothing | 0 |

The third choice wins. A can occupy slots 1 and 2, and B slot 3. Finishing both targets would require four slots, so it is impossible.

The solver test enumerates all $3^3=27$ possible calendars because each slot can hold A, B, or nothing. It discards illegal calendars and confirms the maximum score is seven. This is a separate way to check the solver.

**Do not say:** “Seven is the student's grade.” These are invented priority points. Grades require a validated relationship between effort, submissions, preparation, and assessment outcomes.

## 7. What the classification means

### Linear

An expression is linear here when it adds fixed multiples of variables. $6y_i$ is linear. The six is already known. $x_{it}x_{i,t+1}$ multiplies two decisions, so it is quadratic.

The number of subscripts does not decide whether something is linear. Neither does the number of tasks. What matters is how the unknown decisions appear in the equations.

### Integer and binary

Integer variables take whole-number values. Binary variables are the special case with only zero and one. Our model contains only binary variables, so the precise name is binary integer linear program. It belongs to the broader MILP family.

“Programming” here means mathematical planning. It does not mean the problem is classified by whether we wrote Python.

### Convexity

Imagine a legal calendar and the all-zero calendar. Average their entries. Some become 0.5, which our rules forbid. The midpoint between feasible decisions can be infeasible, so this discrete feasible set is generally nonconvex.

If we let $x$ and $y$ range continuously between zero and one, we get an LP relaxation. It is easier to bound, but it may award a fraction of an assignment's completion value. Simply rounding its answers can break time limits and completion rules.

### Complexity

Selecting whole assignments resembles choosing items for a capacity-limited backpack: each item consumes time and earns value. Deadline windows add further restrictions. We do not need a sweeping NP-hard claim to explain why a standard integer solver is appropriate.

## 8. How the computation works

The Python program constructs the same equations as the report.

1. Read the eight hypothetical tasks and 28 available slots.
2. Create an $x$ variable only for eligible task-slot pairs. Missing pairs mean fixed zero.
3. Add a completion switch for each assignment.
4. Build task-workload rows and slot-capacity rows.
5. Send the coefficients and binary restrictions to HiGHS through SciPy.
6. Read the selected variables and convert them back into a calendar.
7. Check the result independently.

The reduced model contains 93 binary variables and 36 rows. A giant $8\times336$ calendar still describes the model correctly; we simply avoid storing the zeros that cannot change.

### Why negate the objective?

SciPy's interface minimizes. Maximizing $V$ is equivalent to minimizing $-V$: a score of 67 becomes -67, which is better for minimization than -54. The program flips the sign back for reporting.

### How does the solver know it is done?

It finds feasible solutions and mathematical bounds on how much better any solution could be. In this study it has a feasible value of 67 and an upper bound of 67. No better value remains possible under the model. The reported relative gap is zero.

The solver does not need to print every possible calendar. Branching, relaxations, and presolve let it rule out many choices together. If it stopped at a time limit with a gap, we would report the best solution found and the remaining uncertainty rather than call it proven optimal.

## 9. Understand the actual result

The week has 14 available hours against 22 hours of targets. The optimized schedule earns 67 points; the defined deadline-first baseline earns 54. Both allocate 28 slots and respect the same deadlines.

The optimizer completes lab report D and project E. It fully covers preparation C and partially covers F and H. It omits A, B, and G. The baseline completes A, B, and D, prepares F and H fully, and gives only two slots to C. It leaves E out.

The difference is 13 modeled points:

$$\frac{67-54}{54}\times100\%=24.1\%.$$

That percentage is relative to the baseline's score, not the 92-point sum of all targets and not an actual grade increase.

### Why does the schedule switch tasks so often?

Because we did not charge for switching. Several calendars can earn the same score. The solver has no reason to prefer the most comfortable one. This is an honest limitation and a reason to consider a secondary session objective later.

### What did sensitivity analysis show?

Losing Wednesday evening drops the optimum to 59. Adding one hour every evening raises it to 89. Increasing workload estimates by 25%, rounded up, drops it to 55. Doubling A's value leaves the optimum at 67.

The point is not that these invented numbers predict your week. They demonstrate how the model responds to changes and reveal its dependence on the inputs.

## 10. Execute the project yourself

Open `astra.md` for the formal model, `astra-solve.py` for the implementation, and `astra-results.json` for results.

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r astra-requirements.txt
python astra-solve.py
```

On Windows PowerShell replace the activation command with `.venv\Scripts\Activate.ps1`. If activation is restricted, use the environment's Python executable directly rather than changing system security settings.

In the code, `TASKS` holds the inputs. `AVAILABLE` gives four evening blocks per day. `solve` constructs the mathematical program. `edf` produces the precisely defined baseline. `validate` checks legality and score. `tests` verifies small edge cases, including exhaustive enumeration.

To try a different workload, change one $p$ value in a local copy and run again. To test a different preference, change one $v$. Keep a copy of the original inputs so you know which assumption caused the difference. Update report/deck figures together if you replace the demonstration data.

The report's study uses the committed inputs. Solver versions may return a different tied calendar. A different arrangement is not automatically an error if feasibility and optimal value match.

## 11. Questions you should be able to answer

<details><summary>Why did we replace tardiness rather than simply permit late work?</summary>

The original problem says deadlines are hard, including exam preparation. Allowing work after an exam would change that requirement. We instead score useful work delivered before the cutoff and explicitly permit unmet targets under overload.

</details>

<details><summary>Why did we not retain the cramming penalty?</summary>

It counted adjacent half-hours as undesirable. That can punish normal study sessions and reward constant switching. A meaningful spacing model needs a definition of sessions and separation across days. We avoid making a learning claim that the equations do not support.

</details>

<details><summary>Who decides the priority values?</summary>

The student supplies them on a common scale. Our examples are hypothetical. Real deployment should elicit those preferences transparently and test alternatives. Course grade weights may inform them, but percentages from different courses are not automatically comparable.

</details>

<details><summary>Does the model tell me to abandon assignments?</summary>

It identifies what it cannot fit under the given limits and reward assumptions. The output must show omitted tasks. If an assignment is non-negotiable, fix its completion switch to one. If all mandatory tasks cannot fit, report infeasibility and revise the real plan.

</details>

<details><summary>What if an unfinished assignment earns partial credit?</summary>

Then the all-or-nothing reward is wrong for that assignment. Use a staged or proportional reward with matching effort constraints. We chose this simplification for a clearly defined base model and state it explicitly.

</details>

<details><summary>What if four hours of study are not twice as useful as two?</summary>

Our linear preparation reward is an approximation. A diminishing-return model could use separate marginal values for successive preparation increments. It would need defensible estimates and additional ordering rules.

</details>

<details><summary>Could a simple heuristic do just as well?</summary>

Yes, on some instances. Our result only shows an improvement over the stated baseline on this example. A stronger empirical claim would require multiple representative instances and additional baselines.

</details>

<details><summary>Why keep all-zero feasibility?</summary>

It makes the optional-task planning model well-defined even during extreme overload. The output then has low value rather than no solution. This is useful only if unmet targets remain visible and the user understands the scope.

</details>

<details><summary>What does the zero solver gap prove?</summary>

Within numerical tolerances, the best feasible modeled score meets the solver's bound. It proves optimality for the mathematical formulation and chosen input data. It does not prove the preferences, effort estimates, or learning assumptions are true.

</details>

## 12. Presentation rehearsal

Use the deck's speaker notes. The main explanation should fit roughly 8–10 minutes; adjust to the instructor's actual time limit. Keep the final references slide available for questions.

| Moment | What to explain | What to point at |
|---|---|---|
| Problem | 14 hours cannot cover 22 target hours | Capacity comparison |
| Decision | We choose task-slot assignments | Binary calendar |
| Reward | Completed assignments and partial preparation differ | Two reward rules |
| Constraints | Each equation encodes a practical restriction | Equation and meaning |
| Classification | Fixed coefficients plus binary choices | Linear and binary definitions |
| Computation | Solver and independent checks | Method summary |
| Result | 67 versus 54, with omitted work visible | Result table and calendar |
| Limitations | Input uncertainty and unmodeled switching | Sensitivity evidence |

Before presenting, explain the three-slot example without looking at the equations. Then write each equation and connect it to the example. If you can do both, you understand the model well enough to explain rather than recite.

The central conclusion is simple: **a schedule is only as good as its definition of useful work and its treatment of limited time.** Our contribution is an explicit formulation, an executable demonstration, and an honest account of what the result does and does not mean.

# Project 1: Student Work Scheduling Under Hard Deadlines

MAE 494/598

This report includes the complete formulation, numerical study, and executable Python implementation. The appendix contains all inputs and tests; no companion project files are required.

## 1. Problem identification and motivation

A student has fixed classes, sleep, and other commitments. The remaining study time must accommodate assignments and exam preparation with different workloads, release dates, deadlines, and importance. When the required work exceeds the available time, a schedule cannot finish everything. A useful model must expose that shortage and make an explicit choice about what to protect.

We schedule a single student's work during one week. Deadlines remain hard: work after a submission cutoff or exam does not count. We distinguish assignments, whose modeled benefit requires completion, from exam preparation, whose modeled benefit can accrue incrementally. This is a planning approximation, not a prediction of marks or learning.

**Decision:** allocate available 30-minute slots to tasks to maximize completed-assignment value plus exam-preparation coverage value before deadlines.

The choice is nontrivial because an early, low-value assignment can consume time needed for a later, high-value task. Merely counting weekly hours is insufficient: work must fit between each task's release and deadline. The example below deliberately includes a shortage to reveal this tradeoff.

## 2. Sets, parameters, and decision variables

Let $I=A\cup E$ be the disjoint sets of assignments $A$ and exam-preparation tasks $E$. Index tasks by $i$ and time slots by $t\in\{1,\ldots,H\}$.

Each slot lasts $\Delta=0.5$ hours. The horizon starts Monday at 00:00. Slot $t$ covers the interval $[(t-1)\Delta,t\Delta]$ hours from the start. Thus $H=336$ for one week and $H=672$ for two weeks. Deadlines refer to slot **ends**; releases refer to slot **starts** through the eligible-slot convention below.

| Parameter | Meaning | Domain / units |
|---|---|---|
| $a_t$ | Whether the entire slot is available | $\{0,1\}$ |
| $p_i$ | Estimated work needed for completion or the preparation target | Positive integer, slots |
| $r_i$ | First slot whose start is at or after task release | Integer, $1\le r_i\le H$ |
| $d_i$ | Last slot whose end is at or before the deadline | Integer, $r_i\le d_i\le H$ |
| $v_i$ | Value of assignment completion or full preparation | Positive, dimensionless priority points |

For a real timestamp, round release upward to the next eligible slot start and deadline downward to the preceding eligible slot end. Estimate $p_i=\lceil\text{required hours}/\Delta\rceil$. These conservative conversions avoid counting a partly available or post-deadline slot. Tasks with no eligible slot cannot receive work.

Values $v_i$ express the student's declared preferences on one common scale. Twice the value means twice the modeled benefit of completing the target. They do not automatically equal course percentages, especially across courses. The numerical study uses disclosed hypothetical values and includes sensitivity analysis.

### Decision variables

$$x_{it}\in\{0,1\}\qquad\forall i\in I,\ t=1,\ldots,H$$

$x_{it}=1$ means work on task $i$ during the whole slot $t$. The $n\times H$ array is the calendar. Each variable is dimensionless and binary.

$$y_i\in\{0,1\}\qquad\forall i\in A$$

$y_i=1$ means select assignment $i$ for full completion before its deadline. There is one dimensionless binary variable per assignment. Exam preparation does not use $y_i$ because partial preparation can have value.

## 3. Objective function

Maximize total modeled value:

$$\max_{x,y}\quad V(x,y)=\sum_{i\in A}v_i y_i+\sum_{i\in E}\frac{v_i}{p_i}\sum_{t=1}^{H}x_{it}.$$

The first term awards $v_i$ points when an assignment is complete. The second awards $v_i/p_i$ points for each preparation slot, up to the preparation target. Both terms use the same dimensionless priority-point scale, so their sum has a stated meaning.

Example: completing an assignment valued at 12 earns 12 points. A preparation target of eight slots valued at 16 earns two points per allocated slot. Four preparation slots earn eight points. Partial assignment work earns zero in this model.

This is one scalar objective. It is deterministic, and neither a stochastic risk model nor a claim to maximize actual grades. Equal-value schedules can tie. The solver need not select the one with fewer interruptions or more distributed practice.

## 4. Constraints

### (a) Selected assignments receive exactly their required work: equality

$$\sum_{t=1}^{H}x_{it}=p_i y_i\qquad\forall i\in A.$$

If $y_i=1$, allocate exactly $p_i$ slots. If $y_i=0$, allocate no slots. This avoids spending time on an assignment that the model assumes earns no partial value. It is a deliberate all-or-nothing approximation, not a universal statement about academic credit.

### (b) Exam preparation cannot exceed its target: inequality

$$\sum_{t=1}^{H}x_{it}\le p_i\qquad\forall i\in E.$$

Zero through $p_i$ slots are allowed. Allocating beyond the estimated target receives no additional benefit and is excluded. Actual learning could continue beyond this target, which is a limitation.

### (c) Availability and one task at a time: inequality

$$\sum_{i\in I}x_{it}\le a_t\qquad\forall t.$$

An unavailable slot has $a_t=0$, forcing every entry in that column to zero. An available slot has $a_t=1$, allowing at most one task. The model does not double-book the student. Leaving a slot unused is allowed.

### (d) Release and deadline windows: equality restrictions

$$x_{it}=0\qquad\forall i,\quad t<r_i\ \text{or}\ t>d_i.$$

No work before release or after the cutoff. For exam preparation, $d_i$ ends before the exam starts. Availability also removes classes, including the exam itself.

### (e) Binary domains

$$x_{it}\in\{0,1\},\qquad y_i\in\{0,1\}.$$

These discrete domains exclude fractional slot assignments and fractional assignment selection.

The all-zero schedule satisfies every constraint, so overload never makes this optional-task formulation infeasible. Instead, overload lowers achievable value and leaves some targets unmet. This does not make those unmet targets acceptable in reality. It tells the student where more time, reduced scope, or help is needed. If a task is truly mandatory, add $y_i=1$ for an assignment or $\sum_t x_{it}=p_i$ for preparation, then report infeasibility honestly if the calendar cannot support it.

## 5. Problem classification

This is a **binary integer linear program**, a special case of MILP, and a combinatorial scheduling problem. Every coefficient ($v_i$, $p_i$, $a_t$) is fixed input. The objective and constraints contain only sums of constants times variables. In particular, $p_i y_i$ is linear because $p_i$ is not a variable.

All decision variables are binary, so “binary integer linear program” is more specific than “mixed-integer.” Its feasible set is generally nonconvex: averaging a legal selected-assignment solution with the all-zero solution produces fractional $x$ and $y$, which violate the domains. Relaxing both domains to $[0,1]$ gives a convex LP, but may allow fractional completion rewards.

This formulation contains 0–1 knapsack as a special case: make every task an assignment, give all tasks the same release and deadline, and let the common window contain $B$ available slots. Selecting tasks requires $\sum_i p_i y_i\le B$, with reward $\sum_i v_i y_i$. This explains the combinatorial subset-selection structure. The time-indexed formulation explicitly expands the capacity into slots, so this observation alone is not a polynomial-size reduction claim about the expanded encoding. We do not infer runtime from binary variables alone or from a different scheduling problem.

The model permits preemption at slot boundaries: the student may pause a task and resume it later. It has no minimum session length, switching penalty, or learning-spacing model.

## 6. Assumptions and simplifications

| Assumption | Consequence / limitation |
|---|---|
| Known availability | Unexpected events require updating the calendar and solving again |
| Fixed effort estimates | Underestimation can make planned completion unrealistic |
| Equal productivity across slots | A tired evening counts as much as an alert morning |
| Assignment benefit requires completion | Partial-credit or staged assignments need a different reward model |
| Linear preparation benefit | Does not model diminishing returns, forgetting, or observed exam scores |
| Comparable preference values | Output depends on declared priorities, not an objective measure of importance |
| Independent tasks | Prerequisites and shared resources need additional constraints |
| Splittable work | Frequent switching can occur; long sessions are not guaranteed |
| Hard cutoffs | Late-submission credit is outside this version |
| Optional targets under overload | The model diagnoses sacrifices rather than guaranteeing every requirement |

We omit an adjacent-slot penalty. Penalizing consecutive 30-minute slots discourages useful one-hour sessions and can favor alternating tasks. A future spacing model should distinguish session length from separation across days and justify any educational claim with evidence.

## 7. Computational study

### Data and provenance

This is a **synthetic, illustrative week**, not a student's measured calendar. Each day has four available half-hour slots, 18:00–20:00. All other slots are unavailable. Thus 28 slots (14 hours) are available. The eight targets require 44 slots (22 hours). Even ignoring deadline windows, at least 16 target slots cannot fit.

| ID | Task | Type | $p_i$ slots | $r_i$ | $d_i$ | $v_i$ |
|---|---|---|---:|---:|---:|---:|
| A | Reading response | Assignment | 4 | 1 | 88 | 3 |
| B | Mechanics homework | Assignment | 6 | 1 | 136 | 12 |
| C | Fluid mechanics exam prep | Preparation | 8 | 1 | 136 | 16 |
| D | Lab report | Assignment | 6 | 97 | 232 | 15 |
| E | Design project milestone | Assignment | 8 | 145 | 328 | 24 |
| F | Math exam prep | Preparation | 6 | 145 | 280 | 12 |
| G | Weekly reflection | Assignment | 2 | 193 | 280 | 2 |
| H | Statistics exam prep | Preparation | 4 | 241 | 328 | 8 |

Deadline ends are Tuesday 20:00 (A), Wednesday 20:00 (B,C), Friday 20:00 (D), Saturday 20:00 (F,G), and Sunday 20:00 (E,H). Releases 97, 145, 193, and 241 mean Wednesday, Thursday, Friday, and Saturday at 00:00 respectively. The theoretical sum of all target values is 92 points, but the calendar cannot attain it.

### Method and reproducibility

The implementation in Appendix A uses `scipy.optimize.milp` with HiGHS. It negates the objective for the solver's minimization interface and excludes unavailable or out-of-window allocation variables, which are fixed to zero in the full formulation. The base instance has 93 binary variables and 36 retained constraints.

The appendix includes every input, the baseline, independent validation, and tests. Copy the code into `scheduler.py`, install the two pinned dependencies using the command provided, and run it. It prints the complete results as JSON. No external dataset, credential, solver license, or separate project file is required.

The tested environment uses NumPy 2.3.5 and SciPy 1.17.0. Use Python 3.12. Runtime and the particular tied optimal calendar can vary by machine; the reported objective values should reproduce.

### Baseline definition

At each available slot, the baseline chooses the released, unfinished task with the earliest deadline, breaking ties alphabetically by ID. It skips an assignment if too few eligible slots remain to finish it. Preparation can receive any remaining amount. If later releases interrupt an assignment so it stays incomplete, the baseline discards those partial allocations to satisfy the same all-or-nothing rule. No such discard occurs in this instance. The baseline is deterministic and deadline-first; it makes no claim to be the strongest heuristic. Both schedules use identical inputs, reward definitions, availability, and windows.

### Results

| ID | Optimized slots | Baseline slots | Optimized value | Baseline value |
|---|---:|---:|---:|---:|
| A | 0 | 4 | 0 | 3 |
| B | 0 | 6 | 0 | 12 |
| C | 8 | 2 | 16 | 4 |
| D | 6 | 6 | 15 | 15 |
| E | 8 | 0 | 24 | 0 |
| F | 4 | 6 | 8 | 12 |
| G | 0 | 0 | 0 | 0 |
| H | 2 | 4 | 4 | 8 |
| Total | 28 | 28 | **67** | **54** |

The optimized value is 13 points higher, a 24.1% improvement over this baseline's score. This is **not** a 24.1% improvement in grades. The model chooses C over low-value A and the B/C bottleneck, preserves D and E, and leaves F and H partially prepared. The baseline spends the early window on A and B, then misses the larger E target. Omitted assignments A, B, and G must remain visible to the student; the schedule is not a promise that every obligation is covered.

One solver-returned optimal schedule is below. Entries follow chronological order within each day, and each letter means one 30-minute slot.

| Day | 18:00 | 18:30 | 19:00 | 19:30 |
|---|---|---|---|---|
| Monday | C | C | C | C |
| Tuesday | C | C | C | C |
| Wednesday | D | D | D | D |
| Thursday | D | E | D | F |
| Friday | F | E | F | F |
| Saturday | H | E | E | E |
| Sunday | H | E | E | E |

This calendar exhibits a limitation: the objective does not penalize task switches. We show the actual output rather than silently making it look more organized. A secondary session objective could improve usability without changing the primary optimum, but it is outside the tested formulation.

### Optimality and independent checks

The solver returns status 0 (optimal), a feasible value of 67, an upper bound of 67 for the maximization problem, and a relative MIP gap of 0. It took approximately 0.006 seconds for the base solve on the test machine, excluding startup and imports. A proof of optimality applies to the model and inputs, not to the student's real outcomes.

The validator separately checks binary extraction, slot occupancy, release/deadline eligibility, workload caps, assignment completion, and independently recomputed objective value. Five tests pass, including exhaustive enumeration of all 27 calendars for a two-task, three-slot case with known optimum 7. Other tests cover no eligible slots, an assignment that cannot fit, partial preparation, and a release boundary.

### Sensitivity and interpretation

| Changed assumption | Available slots | Optimal value | Interpretation |
|---|---:|---:|---|
| Base case | 28 | 67 | 14 hours cannot cover 22 target hours |
| Available 16:00–21:00 every day | 70 | 92 | All targets fit; the baseline also scores 92 |
| Lose Wednesday evening | 24 | 59 | Losing two hours costs 8 modeled points |
| Add 20:00–21:00 each day | 42 | 89 | Extra time helps, but deadlines still limit eligible use |
| Increase each effort estimate 25%, rounded up | 28 | 55 | The plan is sensitive to underestimated workloads |
| Double A's value from 3 to 6 | 28 | 67 | This preference change does not raise the best score |

All six cases solve with zero reported relative gap. In the adequate-capacity case, both methods achieve the full 92-point value. The example therefore does not imply an optimizer always improves on the baseline. The changed-value case changes the score definition, so it is a preference-sensitivity test, not a directly comparable performance gain. No change in objective alone proves that every optimal calendar is unchanged. Added hours after a deadline cannot help that expired task.

## 8. Conclusion

The model allocates limited study time while respecting release dates and hard deadlines. It exposes overload through omitted assignments and partial preparation rather than scheduling work after a cutoff. For the synthetic overloaded week, it achieves 67 priority points compared with 54 for the defined deadline-first baseline, with a zero reported optimality gap. When all targets fit, both methods achieve 92 points.

These results establish that the formulation and implementation behave as intended on the tested instances. They do not establish improvements in actual grades or learning. The most important limitations are estimated workloads, subjective values, linear preparation rewards, and the absence of session-quality constraints.

## References

1. Yi Ren. [Project 1: Optimization Problem Formulation](https://designinformaticslab.github.io/DesignOptimization2025/project1_optimization_formulation.html). Assignment requirements and rubric, accessed September 9, 2026.
2. SciPy. [`scipy.optimize.milp` documentation](https://docs.scipy.org/doc/scipy/reference/generated/scipy.optimize.milp.html). Mixed-integer solver interface, integrality options, and optimality status.
3. HiGHS. [Official solver documentation and project](https://highs.dev/).
4. Q. Huangfu and J. A. J. Hall. “Parallelizing the dual revised simplex method.” *Mathematical Programming Computation*, 10(1), 119–142, 2018. [doi:10.1007/s12532-017-0130-5](https://doi.org/10.1007/s12532-017-0130-5). Solver reference recommended by HiGHS.

All task data and priority values are hypothetical inputs defined in Appendix A. No outside student dataset or measured learning-effect estimate is used.

## Appendix A. Complete implementation

This appendix is part of the report. It contains the full input instance, mathematical-program construction, deterministic baseline, independent schedule checks, five tests, and all six study cases.

### Reproduction

Using Python 3.12, install the pinned dependencies:

```bash
python -m pip install numpy==2.3.5 scipy==1.17.0
```

Copy the complete Python block below into a new file named `scheduler.py`, then run:

```bash
python scheduler.py
```

The script prints all inputs and results as JSON. An assertion failure stops execution if a validation check fails; do not run with Python's `-O` option, which disables assertions. Expected base outputs are value 67, upper bound 67, gap 0, and baseline value 54. The adequate-capacity case reports 92 for both methods. The program generates the output; no pre-existing results file is needed.

### Python source

```python
"""Reproduce the synthetic study, solve a binary linear program, and verify it.
Run: python scheduler.py. Results print as JSON.
"""
import itertools
import json
import math
import time
import numpy as np
import scipy
from scipy.optimize import milp, Bounds, LinearConstraint
from scipy.sparse import lil_matrix

H = 336
# Slot t covers [(t-1)/2,t/2] hours since Monday 00:00.
AVAILABLE = [day * 48 + t for day in range(7) for t in (37,38,39,40)]
TASKS = [
    dict(id='A',name='Reading response',kind='assignment',p=4,r=1,d=88,v=3),
    dict(id='B',name='Mechanics homework',kind='assignment',p=6,r=1,d=136,v=12),
    dict(id='C',name='Fluid mechanics exam prep',kind='prep',p=8,r=1,d=136,v=16),
    dict(id='D',name='Lab report',kind='assignment',p=6,r=97,d=232,v=15),
    dict(id='E',name='Design project milestone',kind='assignment',p=8,r=145,d=328,v=24),
    dict(id='F',name='Math exam prep',kind='prep',p=6,r=145,d=280,v=12),
    dict(id='G',name='Weekly reflection',kind='assignment',p=2,r=193,d=280,v=2),
    dict(id='H',name='Statistics exam prep',kind='prep',p=4,r=241,d=328,v=8),
]

def score(tasks, schedule):
    counts = {t['id']:schedule.count(t['id']) for t in tasks}
    return sum(t['v']*(counts[t['id']]/t['p'] if t['kind']=='prep' else int(counts[t['id']]==t['p'])) for t in tasks)

def validate(tasks, available, schedule, expected=None):
    assert len(schedule)==len(available)
    by_id={t['id']:t for t in tasks}
    for slot, name in zip(available,schedule):
        if name is not None:
            assert name in by_id
            assert by_id[name]['r']<=slot<=by_id[name]['d']
    for t in tasks:
        count=schedule.count(t['id'])
        assert count<=t['p']
        if t['kind']=='assignment': assert count in (0,t['p'])
    if expected is not None: assert abs(score(tasks,schedule)-expected)<1e-6

def solve(tasks, available):
    # Fix unavailable/out-of-window variables to zero by excluding them.
    edges=[(i,t) for i,a in enumerate(tasks) for t in available if a['r']<=t<=a['d']]
    assignments=[i for i,a in enumerate(tasks) if a['kind']=='assignment']
    yi={i:len(edges)+j for j,i in enumerate(assignments)}
    count=len(edges)+len(assignments)
    c=np.zeros(count)
    for k,(i,t) in enumerate(edges):
        if tasks[i]['kind']=='prep': c[k]=-tasks[i]['v']/tasks[i]['p']
    for i,k in yi.items(): c[k]=-tasks[i]['v']
    mat=lil_matrix((len(tasks)+len(available),count))
    lo=np.full(mat.shape[0],-np.inf); hi=np.zeros(mat.shape[0])
    slots={t:j for j,t in enumerate(available)}
    for k,(i,t) in enumerate(edges):
        mat[i,k]=1; mat[len(tasks)+slots[t],k]=1
    for i,a in enumerate(tasks):
        if i in yi: mat[i,yi[i]]=-a['p']; lo[i]=hi[i]=0
        else: hi[i]=a['p']
    hi[len(tasks):]=1
    tic=time.perf_counter()
    result=milp(c,integrality=np.ones(count),bounds=Bounds(0,1),
        constraints=LinearConstraint(mat.tocsr(),lo,hi),
        options={'mip_rel_gap':0,'time_limit':60})
    elapsed=time.perf_counter()-tic
    assert result.status==0, result.message
    assert np.max(np.abs(result.x-np.rint(result.x)))<1e-6
    schedule=[None]*len(available)
    for value,(i,t) in zip(result.x,edges):
        if value>.5:
            assert schedule[slots[t]] is None
            schedule[slots[t]]=tasks[i]['id']
    objective=-float(result.fun)
    validate(tasks,available,schedule,objective)
    return dict(value=objective,upper_bound=-float(result.mip_dual_bound),gap=float(result.mip_gap),
        seconds=elapsed,status=int(result.status),message=result.message,variables=count,
        constraints=mat.shape[0],schedule=schedule)

def edf(tasks, available):
    # Each slot: earliest deadline, then stable task ID. Do not start an
    # all-or-nothing assignment unless enough unoccupied eligible slots remain.
    schedule=[None]*len(available); remaining={a['id']:a['p'] for a in tasks}
    for k,t in enumerate(available):
        eligible=[a for a in tasks if a['r']<=t<=a['d'] and remaining[a['id']]>0]
        eligible.sort(key=lambda a:(a['d'],a['id']))
        for a in eligible:
            room=sum(a['r']<=s<=a['d'] for s in available[k:])
            if a['kind']=='assignment' and room<remaining[a['id']]: continue
            schedule[k]=a['id'];remaining[a['id']]-=1;break
    # If a later release preempted a started assignment, it earns no value.
    # Release its partial work so the reported baseline respects the same model.
    incomplete={a['id'] for a in tasks if a['kind']=='assignment' and 0<schedule.count(a['id'])<a['p']}
    schedule=[None if a in incomplete else a for a in schedule]
    validate(tasks,available,schedule)
    return dict(value=score(tasks,schedule),schedule=schedule)

def tests():
    tiny=[dict(id='A',kind='assignment',p=2,r=1,d=3,v=5),dict(id='B',kind='prep',p=2,r=2,d=3,v=4)]
    feasible=[]
    for s in itertools.product([None,'A','B'],repeat=3):
        try: validate(tiny,[1,2,3],list(s));feasible.append(score(tiny,list(s)))
        except AssertionError: pass
    assert abs(solve(tiny,[1,2,3])['value']-max(feasible))<1e-6
    assert max(feasible)==7
    assert solve(tiny,[4])['value']==0
    assert solve([dict(id='A',kind='assignment',p=3,r=1,d=2,v=100)],[1,2])['value']==0
    assert solve([dict(id='P',kind='prep',p=4,r=1,d=2,v=8)],[1,2])['value']==4
    assert solve([dict(id='A',kind='assignment',p=1,r=2,d=2,v=4)],[1,2])['schedule']==[None,'A']
    return ['exhaustive 27-schedule cross-check (optimum 7)', 'no eligible slots',
        'assignment cannot fit', 'partial preparation earns proportional value', 'release boundary']

if __name__=='__main__':
    data=dict(scipy_version=scipy.__version__,slot_hours=.5,horizon=H,tasks=TASKS,available=AVAILABLE)
    data['tests']=tests();data['optimal']=solve(TASKS,AVAILABLE);data['baseline']=edf(TASKS,AVAILABLE)
    data['sensitivity']=[]
    for label,available,tasks in [
        ('Base case',AVAILABLE,TASKS),
        ('Adequate capacity: 16:00-21:00 daily',[d*48+t for d in range(7) for t in range(33,43)],TASKS),
        ('Lose Wednesday evening',[t for t in AVAILABLE if t//48!=2],TASKS),
        ('Add 1 hour each day',sorted(AVAILABLE+[d*48+t for d in range(7) for t in (41,42)]),TASKS),
        ('Effort estimates +25%',AVAILABLE,[dict(a,p=math.ceil(a['p']*1.25)) for a in TASKS]),
        ('Double reading value',AVAILABLE,[dict(a,v=a['v']*2) if a['id']=='A' else a for a in TASKS])]:
        result=solve(tasks,available)
        baseline=edf(tasks,available)
        data['sensitivity'].append(dict(case=label,value=result['value'],baseline=baseline['value'],gap=result['gap'],slots=len(available)))
    print(json.dumps(data,indent=2))
```


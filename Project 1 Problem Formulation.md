# Project 1: Assignment Scheduling for a Student

## 1. Problem Identification and Motivation

Every student juggles multiple assignments and exams with different deadlines, different amounts of required work, and a limited, irregularly-shaped block of free time each week (gaps between classes, evenings, weekends). Deciding *when* to work on *what* is a genuine daily optimization problem: work on the wrong thing at the wrong time and a student can miss deadlines, cram inefficiently the night before an exam, or waste free time that could have been used productively.

This matters because:
- **Deadlines are hard constraints.** An assignment finished after its due date may receive zero credit; an exam cannot be "started late."
- **Free time is a scarce, non-uniform resource.** A student's free time is fragmented into short and long blocks scattered across the week (e.g., a 30-minute gap between classes vs. a free Saturday afternoon), and not all blocks are equally suited to all tasks.
- **Tasks differ in effort and importance.** A 2-hour reading response and a 15-hour term project both compete for the same free-time slots, but they don't deserve equal priority.
- **Naive heuristics (e.g., "always work on whatever is due soonest") often perform poorly** once multiple deadlines and workloads interact — this is exactly the kind of tradeoff optimization is suited for.

We formulate the problem: **given a student's weekly free-time availability, a list of assignments/exams with deadlines and estimated required effort, find an assignment of study/work sessions to free time slots that respects deadlines and availability while minimizing lateness risk and prioritizing higher-stakes tasks.**

---

## 2. Decision Variables

Let the planning horizon be discretized into uniform time slots (e.g., 30-minute blocks) indexed by

$$t = 1, \dots, H$$

where $H$ is the total number of slots in the planning horizon (e.g., $H = 336$ for a 2-week horizon at 30-minute resolution).

Let the set of tasks (assignments/exam-prep blocks) be indexed by

$$i = 1, \dots, n$$

**Primary decision variable.**

$$x_{it} \in \{0, 1\}, \quad \forall i = 1,\dots,n,\;\; t = 1,\dots,H$$

$$x_{it} = 1 \text{ if the student works on task } i \text{ during slot } t, \text{ and } 0 \text{ otherwise.}$$

This is a **binary** variable (a task either occupies a given slot or it doesn't).

**Auxiliary decision variables** (introduced to express the objective linearly, standard in scheduling formulations):

$$C_i \geq 0, \quad \forall i = 1, \dots, n$$

$$C_i = \text{completion slot of task } i \;\; (\text{continuous/integer, bounded } 0 \le C_i \le H)$$

$$T_i \geq 0, \quad \forall i = 1, \dots, n$$

$$T_i = \text{tardiness of task } i \;\; (\text{continuous, } T_i \ge 0)$$

**Given data (parameters, not decision variables):**

| Symbol | Meaning | Units/type |
|---|---|---|
| $a_t \in \{0,1\}$ | 1 if slot $t$ is free in the student's fixed schedule, 0 otherwise | given, binary |
| $p_i \in \mathbb{Z}_{>0}$ | number of slots of work required to finish task $i$ (projected time needed) | given, slots |
| $d_i \in \{1,\dots,H\}$ | deadline slot for task $i$ (assignment due date / exam date) | given |
| $r_i \in \{1,\dots,H\}$ | earliest slot task $i$ may be started (e.g., assignment release date), $r_i \le d_i$ | given |
| $w_i > 0$ | priority weight of task $i$ (e.g., grade weight, exam importance) | given |

---

## 3. Objective Function

**Primary objective — minimize total weighted tardiness**, so that higher-priority tasks are protected from slipping past their deadlines:

$$\min_{x,\,C,\,T} \quad \sum_{i=1}^{n} w_i \, T_i$$

where the completion time and tardiness are linked to the schedule $x$ through the constraints below. This is a **minimization** problem.

**Optional bonus objective (spacing/anti-cramming term).** Learning science suggests distributed practice (working on the same material across several separate sessions) is more effective than massing all the work into one contiguous block ("cramming"). To reward spacing, define a penalty for consecutive-slot clustering of the same task,

$$\text{Cluster}_i = \sum_{t=1}^{H-1} x_{it}\,x_{i,t+1}$$

(the number of adjacent slot-pairs both assigned to task $i$), and use the combined objective

$$\min_{x,\,C,\,T} \quad \underbrace{\sum_{i=1}^n w_i T_i}_{\text{lateness risk}} \;+\; \lambda \underbrace{\sum_{i=1}^n \text{Cluster}_i}_{\text{cramming penalty}}$$

with weight $\lambda \ge 0$ trading off "avoid lateness" against "spread sessions out." Setting $\lambda = 0$ recovers the primary single-objective formulation. (This bonus term turns the problem into a genuinely **multi-objective** formulation and is a natural candidate for a Pareto-front analysis for the "solve it computationally" bonus.)

---

## 4. Constraints

**(a) Effort requirement — equality constraint.** Each task must receive exactly its required number of work slots:

$$\sum_{t=1}^{H} x_{it} = p_i \qquad \forall i = 1, \dots, n$$

*Meaning:* the student puts in exactly the projected amount of work on each task — no task is left incomplete, and no task is over-worked beyond its estimate.

**(b) Availability — inequality constraint.** The student can only work during slots that are actually free:

$$x_{it} \leq a_t \qquad \forall i, \; \forall t$$

*Meaning:* the schedule cannot assign work to a slot the student is in class, asleep, or otherwise occupied.

**(c) One task at a time — inequality constraint.** In any given slot, the student can work on at most one task:

$$\sum_{i=1}^{n} x_{it} \leq 1 \qquad \forall t = 1, \dots, H$$

*Meaning:* a person cannot literally work on two assignments simultaneously in the same slot.

**(d) Release-time window — inequality (domain) constraint.** A task cannot be worked on before it has been assigned/released or after its deadline:

$$x_{it} = 0 \qquad \forall i,\; \forall t \notin [r_i, d_i]$$

*Meaning:* you can't start homework that hasn't been posted yet, and working on it after the due date does not count toward the deadline.

**(e) Completion-time linking — inequality constraint (linearization).** $C_i$ must be at least as large as the slot index of any session assigned to task $i$:

$$C_i \geq t \cdot x_{it} \qquad \forall i, \; \forall t$$

*Meaning:* $C_i$ captures the last time task $i$ is worked on, i.e., when it is effectively "finished."

**(f) Tardiness definition — inequality constraints:**

$$T_i \geq C_i - d_i \qquad \forall i$$
$$T_i \geq 0 \qquad \forall i$$

*Meaning:* $T_i$ is the amount (in slots) by which task $i$'s completion overshoots its deadline; it is zero if the task finishes on time.

**(g) Variable domains:**

$$x_{it} \in \{0,1\}, \quad C_i \in [0,H], \quad T_i \geq 0 \qquad \forall i, t$$

---

## 5. Problem Classification

This is a **binary (0–1) mixed-integer linear program (MILP)**, and more specifically a **combinatorial scheduling problem**:

- The objective (with $\lambda = 0$) and all constraints (a)–(g) are **linear** in the decision variables $x_{it}, C_i, T_i$.
- The core scheduling variable $x_{it}$ is **binary**, which makes the feasible region a union of discrete points rather than a convex set — the problem is therefore **nonconvex** despite being linear, precisely because of the integrality constraint (the same source of nonconvexity as the MILP facility-location example above).
- Structurally, this is a variant of **single-resource scheduling with deadlines and weighted tardiness minimization** ($1 \,|\, r_i \,|\, \sum w_i T_i$ in classical scheduling notation, generalized to allow *preemption* since a task's $p_i$ slots need not be contiguous). Even the non-preemptive single-machine weighted-tardiness problem is known to be **NP-hard**, so we expect the number of feasible slot-assignments to grow combinatorially with $n$ and $H$, and exact solution time to scale poorly — motivating the use of an off-the-shelf MILP solver (e.g., CBC, Gurobi, or HiGHS via PuLP/Pyomo) rather than a custom algorithm.
- If the bonus spacing term is included ($\lambda > 0$), the $\text{Cluster}_i$ term introduces a **bilinear (quadratic) term** $x_{it} x_{i,t+1}$, making that version a **mixed-integer quadratic/multi-objective program** — still linearizable with standard tricks (introducing $y_{it} \geq x_{it} + x_{i,t+1} - 1$), but worth noting explicitly as a different problem class than the base formulation.

---

## 6. Assumptions and Simplifications

- **Fixed, known availability.** We assume the student's free-time schedule $a_t$ is known and fixed in advance; in reality, unexpected events (social plans, illness, extra shifts) can shrink availability, which this static model does not capture. A rolling re-optimization would be needed in practice.
- **Fixed, accurate effort estimates.** $p_i$ (projected time needed) is treated as a known constant, but actual effort is uncertain and often exceeds estimates — a stochastic extension (à la the Sample Problem #8 power-grid model) could model $p_i$ as a random variable.
- **Uniform slot productivity.** We assume one slot of work on task $i$ contributes equally regardless of *when* it occurs; in reality, focus and productivity vary by time of day and by how fragmented the free-time block is (a 15-minute gap is less useful for deep work than a 2-hour block). This could be modeled with slot-dependent efficiency factors in a future iteration.
- **No task interdependencies.** Tasks are treated as independent; in practice, some assignments build on others (e.g., a project draft must precede its final submission), which would require precedence constraints.
- **Discretization error.** Continuous time is approximated by discrete slots; finer discretization improves realism but increases the number of variables ($n \times H$), impacting solvability.
- **Deterministic deadlines and single "student resource."** We assume one student, one continuous stream of decision-making, and fixed, known deadlines — group project coordination or shared resources (e.g., lab equipment) are out of scope.

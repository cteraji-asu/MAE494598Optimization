"""Reproducible long-horizon D1--D4 and acceleration-bound diagnostics."""

from __future__ import annotations

from dataclasses import replace
from time import perf_counter

import numpy as np

from conditioning import cond_after_diagonal_rescale, conjugate_gradient, spectrum
from constraints import numerical_rank_tolerance
from dynamics import discretize_cw, mean_motion
from formulations import build_multiple_shooting, build_single_shooting
from models import RendezvousConfig
from solvers import solve_reduced_gradient_descent, solve_sparse_kkt


def cross_track_hand_check(config: RendezvousConfig, num_intervals: int = 4) -> dict[str, object]:
    """Compare analytic and numerical eigenvalues for a 2-by-2 reduced Hessian."""

    if num_intervals != 4:
        raise ValueError("the cross-track hand check requires four intervals")
    phi, gamma = discretize_cw(
        mean_motion(config.mu, config.reference_radius), config.sample_time
    )
    phi_z = phi[np.ix_([2, 5], [2, 5])]
    gamma_z = gamma[np.ix_([2, 5], [2])]
    mapping = np.zeros((2 * (num_intervals + 1), num_intervals), dtype=float)
    for step in range(num_intervals):
        current = slice(2 * step, 2 * (step + 1))
        following = slice(2 * (step + 1), 2 * (step + 2))
        mapping[following] = phi_z @ mapping[current]
        mapping[following, step : step + 1] += gamma_z

    q_z = config.q_path[np.ix_([2, 5], [2, 5])]
    qf_z = config.q_terminal[np.ix_([2, 5], [2, 5])]
    state_weights = np.zeros_like(mapping @ mapping.T)
    for node in range(num_intervals):
        state_weights[2 * node : 2 * (node + 1), 2 * node : 2 * (node + 1)] = (
            config.sample_time * q_z
        )
    state_weights[-2:, -2:] = qf_z
    hessian = (
        mapping.T @ state_weights @ mapping
        + config.sample_time * config.r_control[2, 2] * np.eye(num_intervals)
    )
    terminal_matrix = mapping[-2:]
    _, singular_values, vh = np.linalg.svd(terminal_matrix, full_matrices=True)
    rank = int(np.sum(singular_values > numerical_rank_tolerance(terminal_matrix)))
    basis = vh[rank:].T
    reduced = basis.T @ hessian @ basis
    reduced = (reduced + reduced.T) / 2.0
    if reduced.shape != (2, 2):
        raise RuntimeError("cross-track reduction did not produce a 2-by-2 matrix")
    a, b, d = reduced[0, 0], reduced[0, 1], reduced[1, 1]
    discriminant = np.sqrt((a - d) ** 2 + 4.0 * b**2)
    analytic = np.array([(a + d - discriminant) / 2.0, (a + d + discriminant) / 2.0])
    numerical = np.linalg.eigvalsh(reduced)
    relative_error = float(
        np.max(np.abs(analytic - numerical) / np.maximum(np.abs(numerical), 1.0))
    )
    return {
        "num_intervals": num_intervals,
        "reduced_hessian": reduced.tolist(),
        "analytic_eigenvalues": analytic.tolist(),
        "numerical_eigenvalues": numerical.tolist(),
        "maximum_relative_error": relative_error,
        "passed": bool(relative_error <= 100.0 * np.finfo(float).eps),
    }


def conditioning_preflight(
    config: RendezvousConfig,
    horizons: tuple[int, ...] = (15, 30, 60, 120, 240),
) -> dict[str, object]:
    """Evaluate D1/D2 inputs and the approved inactive-bound prerequisite."""

    rows: list[dict[str, float | int]] = []
    failed = False
    for horizon in horizons:
        case = replace(config, num_intervals=horizon, final_time=20.0 * horizon)
        problem = build_single_shooting(case)
        eigenvalues, condition_number = spectrum(problem.reduced_hessian)
        optimum = -np.linalg.solve(problem.reduced_hessian, problem.reduced_gradient)
        controls = (problem.reduction.particular + problem.reduction.basis @ optimum).reshape(
            horizon, 3
        )
        maximum_control = float(np.max(np.linalg.norm(controls, axis=1)))
        assert case.acceleration_limit is not None
        inactive = maximum_control <= case.acceleration_limit
        failed = failed or not inactive
        rows.append(
            {
                "num_intervals": horizon,
                "final_time_seconds": case.final_time,
                "reduced_dimension": problem.reduced_hessian.shape[0],
                "condition_number": condition_number,
                "condition_number_after_diagonal_rescaling": cond_after_diagonal_rescale(
                    problem.reduced_hessian
                ),
                "smallest_eigenvalue": float(eigenvalues[0]),
                "largest_eigenvalue": float(eigenvalues[-1]),
                "maximum_control_m_per_s2": maximum_control,
                "acceleration_bound_inactive": int(inactive),
            }
        )
    return {
        "status": "failed_criterion" if failed else "passed",
        "criterion": "acceleration bound remains inactive for the gradient-descent diagnostic",
        "automatic_retuning_performed": False,
        "cross_track_hand_check": cross_track_hand_check(config),
        "rows": rows,
    }


def full_diagnostic_study(
    config: RendezvousConfig,
    horizons: tuple[int, ...] = (15, 30, 60, 120, 240),
    representative_horizon: int = 120,
    *,
    numerics_confirmed: bool,
) -> dict[str, object]:
    """Produce the complete D1--D4 evidence for the equality-constrained benchmark.

    The configured acceleration bound is intentionally omitted from this benchmark.
    The complete bound-constrained mission remains a separate validation case. This
    separation prevents acceleration-bound projection from obscuring the Family I
    long-horizon conditioning mechanism.
    """

    if not numerics_confirmed:
        raise PermissionError("numerical parameters require explicit confirmation")
    if not horizons or any(horizon <= 6 for horizon in horizons):
        raise ValueError("diagnostic horizons must contain at least seven intervals")
    if representative_horizon not in horizons:
        raise ValueError("representative_horizon must be included in horizons")

    rows: list[dict[str, float | int]] = []
    representative_problem = None
    representative_config = None
    representative_eigenvalues = None
    for horizon in horizons:
        case = replace(config, num_intervals=horizon, final_time=20.0 * horizon)
        problem = build_single_shooting(case)
        eigenvalues, condition_number = spectrum(problem.reduced_hessian)
        diagonal_condition_number = cond_after_diagonal_rescale(problem.reduced_hessian)
        rows.append(
            {
                "num_intervals": horizon,
                "final_time_seconds": case.final_time,
                "reduced_dimension": problem.reduced_hessian.shape[0],
                "smallest_eigenvalue": float(eigenvalues[0]),
                "largest_eigenvalue": float(eigenvalues[-1]),
                "condition_number": condition_number,
                "condition_number_after_diagonal_rescaling": diagonal_condition_number,
            }
        )
        if horizon == representative_horizon:
            representative_problem = problem
            representative_config = case
            representative_eigenvalues = eigenvalues

    assert representative_problem is not None
    assert representative_config is not None
    assert representative_eigenvalues is not None

    gradient_descent_solution = solve_reduced_gradient_descent(
        representative_problem,
        representative_config,
        numerics_confirmed=True,
        enforce_acceleration_bounds=False,
    )
    hessian = representative_problem.reduced_hessian
    right_hand_side = -representative_problem.reduced_gradient
    conjugate_gradient_start = perf_counter()
    conjugate_gradient_solution = conjugate_gradient(
        hessian,
        right_hand_side,
        tol=representative_config.solver_options.gradient_tolerance,
        maxit=hessian.shape[0],
    )
    conjugate_gradient_elapsed = perf_counter() - conjugate_gradient_start

    direct_reduced_solution = np.linalg.solve(hessian, right_hand_side)
    direct_reduced_objective = float(
        0.5 * direct_reduced_solution @ hessian @ direct_reduced_solution
        + representative_problem.reduced_gradient @ direct_reduced_solution
        + representative_problem.reduced_constant
    )
    conjugate_gradient_objective = float(
        0.5
        * conjugate_gradient_solution.solution
        @ hessian
        @ conjugate_gradient_solution.solution
        + representative_problem.reduced_gradient @ conjugate_gradient_solution.solution
        + representative_problem.reduced_constant
    )
    direct_controls = (
        representative_problem.reduction.particular
        + representative_problem.reduction.basis @ direct_reduced_solution
    ).reshape(representative_horizon, 3)
    maximum_equality_only_acceleration = float(
        np.max(np.linalg.norm(direct_controls, axis=1))
    )

    multiple_shooting_problem = build_multiple_shooting(representative_config)
    sparse_kkt_solution = solve_sparse_kkt(
        multiple_shooting_problem,
        numerics_confirmed=True,
    )
    objective_scale = max(1.0, abs(direct_reduced_objective))
    objective_agreement = float(
        abs(sparse_kkt_solution.objective - direct_reduced_objective) / objective_scale
    )

    gradient_norms = gradient_descent_solution.reduced_result.gradient_norms
    normalized_gradient_norms = gradient_norms / gradient_norms[0]
    conjugate_gradient_residuals = conjugate_gradient_solution.relative_residuals
    normalized_conjugate_gradient_residuals = (
        conjugate_gradient_residuals / conjugate_gradient_residuals[0]
    )

    passed = bool(
        gradient_descent_solution.reduced_result.converged
        and conjugate_gradient_solution.converged
        and sparse_kkt_solution.stationarity_residual
        <= representative_config.numerical_tolerances.solver_optimality
        and sparse_kkt_solution.equality_residual
        <= representative_config.numerical_tolerances.solver_feasibility
        and objective_agreement <= 1e-10
    )
    return {
        "status": "passed" if passed else "failed",
        "benchmark": {
            "description": (
                "equality-constrained exact-rendezvous diagnostic; the acceleration bound "
                "is omitted only from D1--D4"
            ),
            "sample_time_seconds": 20.0,
            "representative_horizon": representative_horizon,
            "gradient_tolerance": representative_config.solver_options.gradient_tolerance,
            "gradient_max_iterations": (
                representative_config.solver_options.gradient_max_iterations
            ),
            "configured_mission_acceleration_limit_m_per_s2": config.acceleration_limit,
            "maximum_equality_only_acceleration_m_per_s2": (
                maximum_equality_only_acceleration
            ),
        },
        "cross_track_hand_check": cross_track_hand_check(config),
        "d1": {
            "num_intervals": representative_horizon,
            "reduced_dimension": hessian.shape[0],
            "eigenvalues": representative_eigenvalues.tolist(),
            "condition_number": float(
                representative_eigenvalues[-1] / representative_eigenvalues[0]
            ),
        },
        "d2": {"rows": rows},
        "d3": {
            "method": "null-space-reduced fixed-step gradient descent",
            "step_size": gradient_descent_solution.step_size,
            "converged": gradient_descent_solution.reduced_result.converged,
            "iterations": gradient_descent_solution.reduced_result.iterations,
            "elapsed_seconds": gradient_descent_solution.elapsed_seconds,
            "normalized_gradient_norms": normalized_gradient_norms.tolist(),
            "final_normalized_gradient_norm": float(normalized_gradient_norms[-1]),
            "objective": float(
                gradient_descent_solution.reduced_result.objectives[-1]
            ),
            "mission_bound_violation_m_per_s2": (
                gradient_descent_solution.maximum_bound_violation
            ),
        },
        "d4": {
            "conjugate_gradient": {
                "method": "conjugate gradient on the reduced Hessian",
                "converged": conjugate_gradient_solution.converged,
                "iterations": conjugate_gradient_solution.iterations,
                "elapsed_seconds": conjugate_gradient_elapsed,
                "normalized_gradient_norms": (
                    normalized_conjugate_gradient_residuals.tolist()
                ),
                "final_normalized_gradient_norm": float(
                    normalized_conjugate_gradient_residuals[-1]
                ),
                "objective": conjugate_gradient_objective,
            },
            "sparse_multiple_shooting_newton": {
                "method": "one sparse Karush-Kuhn-Tucker Newton solve",
                "elapsed_seconds": sparse_kkt_solution.elapsed_seconds,
                "stationarity_residual": sparse_kkt_solution.stationarity_residual,
                "equality_residual": sparse_kkt_solution.equality_residual,
                "objective": sparse_kkt_solution.objective,
                "relative_objective_difference": objective_agreement,
            },
            "direct_reduced_objective": direct_reduced_objective,
        },
    }

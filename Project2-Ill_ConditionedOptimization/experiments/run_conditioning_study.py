"""Generate the complete D1--D4 report artifacts."""

from __future__ import annotations

import argparse
import csv
import json
import os
from pathlib import Path
from typing import Any

import yaml

from diagnostics import full_diagnostic_study
from models import RendezvousConfig

HORIZONS = (15, 30, 60, 120, 240)
REPRESENTATIVE_HORIZON = 120


def _configure_matplotlib(output_dir: Path) -> Any:
    """Load a noninteractive plotting backend with local cache directories."""

    cache = output_dir / ".cache"
    cache.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("MPLCONFIGDIR", str(cache / "matplotlib"))
    os.environ.setdefault("XDG_CACHE_HOME", str(cache))
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    return plt


def _save_figure(figure: Any, output_dir: Path, stem: str) -> None:
    """Save vector report art and a raster copy for visual verification."""

    figure.savefig(output_dir / f"{stem}.svg")
    figure.savefig(output_dir / f"{stem}.png", dpi=160)


def _write_conditioning_csv(payload: dict[str, object], path: Path) -> None:
    d2 = payload["d2"]
    assert isinstance(d2, dict)
    rows = d2["rows"]
    assert isinstance(rows, list) and rows
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def _write_convergence_csv(payload: dict[str, object], path: Path) -> None:
    d3 = payload["d3"]
    d4 = payload["d4"]
    assert isinstance(d3, dict) and isinstance(d4, dict)
    conjugate_gradient = d4["conjugate_gradient"]
    assert isinstance(conjugate_gradient, dict)
    gradient_descent_history = d3["normalized_gradient_norms"]
    conjugate_gradient_history = conjugate_gradient["normalized_gradient_norms"]
    assert isinstance(gradient_descent_history, list)
    assert isinstance(conjugate_gradient_history, list)
    row_count = max(len(gradient_descent_history), len(conjugate_gradient_history))
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(
            stream,
            fieldnames=[
                "iteration",
                "gradient_descent_normalized_gradient_norm",
                "conjugate_gradient_normalized_gradient_norm",
            ],
        )
        writer.writeheader()
        for iteration in range(row_count):
            writer.writerow(
                {
                    "iteration": iteration,
                    "gradient_descent_normalized_gradient_norm": (
                        gradient_descent_history[iteration]
                        if iteration < len(gradient_descent_history)
                        else ""
                    ),
                    "conjugate_gradient_normalized_gradient_norm": (
                        conjugate_gradient_history[iteration]
                        if iteration < len(conjugate_gradient_history)
                        else ""
                    ),
                }
            )


def _plot_d1(payload: dict[str, object], output_dir: Path, plt: Any) -> None:
    d1 = payload["d1"]
    assert isinstance(d1, dict)
    eigenvalues = d1["eigenvalues"]
    assert isinstance(eigenvalues, list)
    figure, axis = plt.subplots(figsize=(6.4, 4.2))
    axis.semilogy(range(1, len(eigenvalues) + 1), eigenvalues, ".", markersize=4)
    axis.set_xlabel("Eigenvalue index")
    axis.set_ylabel("Reduced-Hessian eigenvalue")
    axis.set_title(
        f"D1: spectrum at N={d1['num_intervals']} "
        f"(condition number κ={d1['condition_number']:.0f})"
    )
    axis.grid(True, which="both", alpha=0.3)
    figure.tight_layout()
    _save_figure(figure, output_dir, "d1_spectrum")
    plt.close(figure)


def _plot_d2(payload: dict[str, object], output_dir: Path, plt: Any) -> None:
    d2 = payload["d2"]
    assert isinstance(d2, dict)
    rows = d2["rows"]
    assert isinstance(rows, list)
    horizons = [int(row["num_intervals"]) for row in rows]
    raw = [float(row["condition_number"]) for row in rows]
    rescaled = [float(row["condition_number_after_diagonal_rescaling"]) for row in rows]
    figure, axis = plt.subplots(figsize=(6.4, 4.2))
    axis.loglog(horizons, raw, "o-", label="Original reduced Hessian")
    axis.loglog(horizons, rescaled, "s--", label="After diagonal rescaling")
    axis.set_xlabel("Horizon length N")
    axis.set_ylabel("Condition number κ")
    axis.set_title("D2: intrinsic condition number κ test")
    axis.grid(True, which="both", alpha=0.3)
    axis.legend()
    figure.tight_layout()
    _save_figure(figure, output_dir, "d2_intrinsic_test")
    plt.close(figure)


def _plot_d3(payload: dict[str, object], output_dir: Path, plt: Any) -> None:
    d3 = payload["d3"]
    benchmark = payload["benchmark"]
    assert isinstance(d3, dict) and isinstance(benchmark, dict)
    history = d3["normalized_gradient_norms"]
    assert isinstance(history, list)
    figure, axis = plt.subplots(figsize=(6.4, 4.2))
    axis.semilogy(range(len(history)), history, label="Gradient descent")
    axis.axhline(
        float(benchmark["gradient_tolerance"]),
        color="black",
        linestyle=":",
        label="Fixed tolerance",
    )
    axis.set_xlabel("Iteration")
    axis.set_ylabel("Normalized gradient norm")
    axis.set_title("D3: long-horizon baseline convergence")
    axis.grid(True, which="both", alpha=0.3)
    axis.legend()
    figure.tight_layout()
    _save_figure(figure, output_dir, "d3_baseline_convergence")
    plt.close(figure)


def _plot_d4(payload: dict[str, object], output_dir: Path, plt: Any) -> None:
    d3 = payload["d3"]
    d4 = payload["d4"]
    assert isinstance(d3, dict) and isinstance(d4, dict)
    conjugate_gradient = d4["conjugate_gradient"]
    assert isinstance(conjugate_gradient, dict)
    gradient_descent_history = d3["normalized_gradient_norms"]
    conjugate_gradient_history = conjugate_gradient["normalized_gradient_norms"]
    assert isinstance(gradient_descent_history, list)
    assert isinstance(conjugate_gradient_history, list)
    figure, axes = plt.subplots(1, 2, figsize=(10.0, 4.2), sharey=True)
    axes[0].semilogy(
        range(len(gradient_descent_history)),
        gradient_descent_history,
        label="Gradient descent baseline",
    )
    axes[0].semilogy(
        range(len(conjugate_gradient_history)),
        conjugate_gradient_history,
        label="Conjugate-gradient remedy",
    )
    axes[0].set_xlabel("Iteration")
    axes[0].set_ylabel("Normalized gradient norm")
    axes[0].set_title("Full iteration range")
    axes[0].grid(True, which="both", alpha=0.3)
    axes[0].legend()

    early_limit = 120
    axes[1].semilogy(
        range(min(early_limit + 1, len(gradient_descent_history))),
        gradient_descent_history[: early_limit + 1],
        label="Gradient descent baseline",
    )
    axes[1].semilogy(
        range(len(conjugate_gradient_history)),
        conjugate_gradient_history,
        label="Conjugate-gradient remedy",
    )
    axes[1].set_xlabel("Iteration")
    axes[1].set_title("First 120 iterations")
    axes[1].grid(True, which="both", alpha=0.3)
    figure.suptitle("D4: before-and-after convergence")
    figure.tight_layout()
    _save_figure(figure, output_dir, "d4_before_after")
    plt.close(figure)


def run(config_path: Path, output_dir: Path) -> int:
    """Write the approved D1--D4 data, tables, and plots."""

    config = RendezvousConfig.from_mapping(yaml.safe_load(config_path.read_text()))
    output_dir.mkdir(parents=True, exist_ok=True)
    payload = full_diagnostic_study(
        config,
        HORIZONS,
        REPRESENTATIVE_HORIZON,
        numerics_confirmed=True,
    )
    (output_dir / "diagnostics.json").write_text(
        json.dumps(payload, indent=2) + "\n",
        encoding="utf-8",
    )
    _write_conditioning_csv(payload, output_dir / "conditioning.csv")
    _write_convergence_csv(payload, output_dir / "convergence.csv")
    plt = _configure_matplotlib(output_dir)
    _plot_d1(payload, output_dir, plt)
    _plot_d2(payload, output_dir, plt)
    _plot_d3(payload, output_dir, plt)
    _plot_d4(payload, output_dir, plt)
    print(f"D1--D4 diagnostic status: {payload['status']}")
    return 0 if payload["status"] == "passed" else 1


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=Path("data/canonical.yaml"))
    parser.add_argument("--output-dir", type=Path, default=Path("outputs/report"))
    arguments = parser.parse_args()
    return run(arguments.config, arguments.output_dir)


if __name__ == "__main__":
    raise SystemExit(main())

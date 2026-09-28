"""Tests for reproducible diagnostic orchestration."""

from __future__ import annotations

import numpy as np
import pytest

from diagnostics import conditioning_preflight, cross_track_hand_check, full_diagnostic_study
from models import RendezvousConfig


def test_cross_track_hand_check_matches_numerical_eigenvalues(
    config: RendezvousConfig,
) -> None:
    result = cross_track_hand_check(config)
    np.testing.assert_allclose(
        result["analytic_eigenvalues"], result["numerical_eigenvalues"], rtol=1e-14
    )
    assert result["passed"] is True


def test_cross_track_hand_check_rejects_other_dimensions(config: RendezvousConfig) -> None:
    with pytest.raises(ValueError, match="four intervals"):
        cross_track_hand_check(config, num_intervals=5)


def test_conditioning_preflight_records_failed_bound_without_retuning(
    config: RendezvousConfig,
) -> None:
    payload = conditioning_preflight(config, horizons=(15,))
    assert payload["status"] == "failed_criterion"
    assert payload["automatic_retuning_performed"] is False
    rows = payload["rows"]
    assert isinstance(rows, list)
    assert rows[0]["acceleration_bound_inactive"] == 0


def test_full_diagnostic_study_completes_d1_through_d4(
    config: RendezvousConfig,
) -> None:
    payload = full_diagnostic_study(
        config,
        horizons=(12,),
        representative_horizon=12,
        numerics_confirmed=True,
    )
    assert payload["status"] == "passed"
    assert payload["d1"]["reduced_dimension"] == 30
    assert payload["d3"]["converged"] is True
    assert payload["d4"]["conjugate_gradient"]["converged"] is True
    assert (
        payload["d4"]["sparse_multiple_shooting_newton"][
            "relative_objective_difference"
        ]
        < 1e-10
    )


def test_full_diagnostic_study_requires_confirmation(config: RendezvousConfig) -> None:
    with pytest.raises(PermissionError, match="explicit confirmation"):
        full_diagnostic_study(
            config,
            horizons=(12,),
            representative_horizon=12,
            numerics_confirmed=False,
        )

"""Stress engine: baseline invariance, ranking, monotonicity, and the loss formula."""
import numpy as np
import pandas as pd
import pytest
from platform_core.stress import (CUMULATIVE_QUARTERS, avg_loss_rate, expected_loss,
                                  run_stress, scenario_shifts, stress_pd)

SCEN = pd.DataFrame({"scenario": ["Baseline", "Adverse", "Severe"],
                     "cumulative_9q_loss_pct": [6.6, 7.9, 9.5]})
PORT = pd.DataFrame({"id": range(5), "loan_amnt": [1e4, 2e4, 1.5e4, 3e4, 5e3],
                     "pd": [0.05, 0.10, 0.15, 0.25, 0.40]})
PARAMS = {"lgd": 0.9, "ead_ratio": 0.6}


def test_avg_loss_rate_inverts_cumulative():
    rate = avg_loss_rate(9.0)
    assert rate * CUMULATIVE_QUARTERS / 4 == pytest.approx(0.09)


def test_baseline_shift_is_zero_and_leaves_pds_unchanged():
    shifts = scenario_shifts(SCEN)
    assert shifts["Baseline"] == pytest.approx(0.0)
    assert np.allclose(stress_pd(PORT["pd"].to_numpy(), shifts["Baseline"]), PORT["pd"])


def test_stress_raises_every_pd_and_preserves_ranking():
    stressed = stress_pd(PORT["pd"].to_numpy(), 0.5)
    assert (stressed > PORT["pd"]).all()
    assert (np.argsort(stressed) == np.argsort(PORT["pd"].to_numpy())).all()
    assert ((stressed > 0) & (stressed < 1)).all()


def test_expected_loss_formula():
    assert expected_loss(0.1, 10_000, 0.9, 0.6) == pytest.approx(540.0)


def test_losses_rise_with_scenario_severity():
    res = run_stress(PORT, SCEN, PARAMS).set_index("scenario")
    assert res.loc["Baseline", "expected_loss"] < res.loc["Adverse", "expected_loss"] < res.loc["Severe", "expected_loss"]
    assert res.loc["Baseline", "vs_baseline"] == pytest.approx(0.0)

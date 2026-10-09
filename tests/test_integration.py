"""End to end on the committed artifacts: contracts, temporal integrity, and stress results."""
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from scipy.stats import spearmanr

from platform_core.contracts import (ContractError, validate_loss_params, validate_no_lookahead,
                                     validate_portfolio, validate_scenarios)
from platform_core.stress import expected_loss, run_stress

DATA = Path(__file__).resolve().parents[1] / "data"


@pytest.fixture(scope="module")
def inputs():
    portfolio = validate_portfolio(pd.read_parquet(DATA / "portfolio.parquet"))
    scenarios = validate_scenarios(pd.read_csv(DATA / "scenarios.csv"))
    params = validate_loss_params(json.loads((DATA / "loss_params.json").read_text()))
    return portfolio, scenarios, params


def test_artifacts_satisfy_contracts_and_have_no_lookahead(inputs):
    portfolio, _, params = inputs
    validate_no_lookahead(portfolio, params)


def test_lookahead_is_caught(inputs):
    portfolio, _, params = inputs
    with pytest.raises(ContractError):
        validate_no_lookahead(portfolio, {**params, "estimated_through": "2015-06-30"})


def test_baseline_reproduces_the_credit_models_expected_loss(inputs):
    portfolio, scenarios, params = inputs
    res = run_stress(portfolio, scenarios, params).set_index("scenario")
    direct = expected_loss(portfolio["pd"], portfolio["loan_amnt"], params["lgd"], params["ead_ratio"]).sum()
    assert res.loc["Baseline", "expected_loss"] == pytest.approx(direct)
    assert res.loc["Baseline", "mean_pd"] == pytest.approx(portfolio["pd"].mean())


def test_portfolio_losses_rank_scenarios_like_the_macro_lab(inputs):
    portfolio, scenarios, params = inputs
    res = run_stress(portfolio, scenarios, params)
    merged = res.merge(scenarios, on="scenario")
    rho = spearmanr(merged["expected_loss"], merged["cumulative_9q_loss_pct"]).statistic
    assert rho == pytest.approx(1.0)
    assert (res.loc[res["scenario"] != "Baseline", "vs_baseline"] > 0).all()

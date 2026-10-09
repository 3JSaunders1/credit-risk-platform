"""Data contracts: bad inputs fail loudly."""
import pandas as pd
import pytest
from platform_core.contracts import (ContractError, validate_loss_params,
                                     validate_portfolio, validate_scenarios)

GOOD_PORTFOLIO = pd.DataFrame({"id": [1, 2], "loan_amnt": [1000.0, 2000.0], "pd": [0.1, 0.2]})
GOOD_SCENARIOS = pd.DataFrame({"scenario": ["Baseline", "Adverse"], "cumulative_9q_loss_pct": [6.6, 7.9]})


def test_valid_inputs_pass():
    validate_portfolio(GOOD_PORTFOLIO)
    validate_scenarios(GOOD_SCENARIOS)
    validate_loss_params({"lgd": 0.89, "ead_ratio": 0.58})


@pytest.mark.parametrize("bad", [
    GOOD_PORTFOLIO.drop(columns="loan_amnt"),                 # missing column
    GOOD_PORTFOLIO.assign(pd=[0.1, 1.2]),                     # PD out of range
    GOOD_PORTFOLIO.assign(id=[1, 1]),                         # duplicate ids
    GOOD_PORTFOLIO.assign(loan_amnt=[1000.0, -5.0]),          # negative amount
    GOOD_PORTFOLIO.assign(pd=[0.1, None]),                    # missing value
])
def test_bad_portfolio_fails(bad):
    with pytest.raises(ContractError):
        validate_portfolio(bad)


def test_scenarios_require_baseline():
    with pytest.raises(ContractError):
        validate_scenarios(GOOD_SCENARIOS.assign(scenario=["Mild", "Adverse"]))


def test_loss_params_out_of_range_fail():
    with pytest.raises(ContractError):
        validate_loss_params({"lgd": 1.5, "ead_ratio": 0.5})

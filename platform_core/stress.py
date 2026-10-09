"""
Top-down stress link: macro scenarios -> PD shifts -> portfolio expected loss.

Each scenario's 9-quarter cumulative loss (from the macro lab) is converted to an
average annualized loss rate, and its log-odds distance from the Baseline becomes
a shift applied to every loan's PD:

    shift_s       = logit(avg_rate_s) - logit(avg_rate_baseline)
    stressed_pd_i = expit(logit(pd_i) + shift_s)

This is the same intercept-shift mechanism the credit default model uses for
recalibration: it moves every PD by the same amount in log-odds, preserving the
ranking. Expected loss = stressed PD x LGD x EAD ratio x loan amount.

Assumption: the model's PDs represent baseline conditions, so the Baseline
scenario leaves them unchanged and other scenarios are measured relative to it.
"""
import pandas as pd
from scipy.special import expit, logit

from platform_core.contracts import BASELINE

CUMULATIVE_QUARTERS = 9


def avg_loss_rate(cumulative_pct: float, quarters: int = CUMULATIVE_QUARTERS) -> float:
    """Average annualized loss rate implied by a cumulative loss (sum of quarterly rates / 4)."""
    return cumulative_pct / 100 * 4 / quarters


def scenario_shifts(scenarios: pd.DataFrame) -> pd.Series:
    """Log-odds shift of each scenario relative to the Baseline."""
    rates = scenarios.set_index("scenario")["cumulative_9q_loss_pct"].map(avg_loss_rate)
    return logit(rates) - logit(rates[BASELINE])


def stress_pd(pd_values, shift: float):
    """Shift PDs in log-odds; preserves ranking and keeps PDs in (0, 1)."""
    return expit(logit(pd_values) + shift)


def expected_loss(pd_values, loan_amnt, lgd: float, ead_ratio: float):
    """Loan-level expected loss: PD x LGD x (loan amount x EAD ratio)."""
    return pd_values * lgd * loan_amnt * ead_ratio


def run_stress(portfolio: pd.DataFrame, scenarios: pd.DataFrame, params: dict) -> pd.DataFrame:
    """One row per scenario: shift, mean PD, expected loss, and loss rate."""
    total = portfolio["loan_amnt"].sum()
    rows = []
    for name, shift in scenario_shifts(scenarios).items():
        pds = stress_pd(portfolio["pd"].to_numpy(), shift)
        el = expected_loss(pds, portfolio["loan_amnt"].to_numpy(), params["lgd"], params["ead_ratio"])
        rows.append({"scenario": name, "logodds_shift": float(shift), "mean_pd": float(pds.mean()),
                     "expected_loss": float(el.sum()), "loss_rate": float(el.sum() / total)})
    out = pd.DataFrame(rows)
    base = out.loc[out["scenario"] == BASELINE, "expected_loss"].iloc[0]
    out["vs_baseline"] = out["expected_loss"] / base - 1
    return out

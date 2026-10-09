"""
Run every macro scenario through the loan portfolio.

Usage: python -m platform_core.run_stress
"""
import json
from pathlib import Path

import pandas as pd

from platform_core.contracts import validate_loss_params, validate_portfolio, validate_scenarios
from platform_core.logging_utils import get_logger, run_main
from platform_core.stress import run_stress

ROOT = Path(__file__).resolve().parents[1]
DATA, REPORTS = ROOT / "data", ROOT / "reports"

log = get_logger(__name__)


def main():
    portfolio = validate_portfolio(pd.read_parquet(DATA / "portfolio.parquet"))
    scenarios = validate_scenarios(pd.read_csv(DATA / "scenarios.csv"))
    params = validate_loss_params(json.loads((DATA / "loss_params.json").read_text()))

    results = run_stress(portfolio, scenarios, params)
    shown = results.assign(
        mean_pd=lambda d: (d["mean_pd"] * 100).round(2),
        expected_loss_m=lambda d: (d["expected_loss"] / 1e6).round(1),
        loss_rate=lambda d: (d["loss_rate"] * 100).round(2),
        vs_baseline=lambda d: (d["vs_baseline"] * 100).round(1),
    )[["scenario", "logodds_shift", "mean_pd", "expected_loss_m", "loss_rate", "vs_baseline"]]

    total = portfolio["loan_amnt"].sum() / 1e9
    print(f"\n=== Portfolio stress test: {len(portfolio):,} loans, ${total:.2f}B originated ===")
    print("(mean PD, loss rate, and change vs. baseline in %; expected loss in $ millions)")
    print(shown.round(3).to_string(index=False))

    REPORTS.mkdir(exist_ok=True)
    results.to_csv(REPORTS / "stress_results.csv", index=False)
    log.info("Saved results to %s", REPORTS / "stress_results.csv")


if __name__ == "__main__":
    run_main(main)

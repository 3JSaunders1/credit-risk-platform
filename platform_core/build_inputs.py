"""
Collect artifacts from the two projects into data/, validated against their contracts.

- portfolio.parquet: 2015 loans with recalibrated PDs and loan amounts (credit default model)
- loss_params.json:  LGD and EAD ratio estimated on 2012-2014 charge-offs only (no look-ahead)
- scenarios.csv:     scenario cumulative losses (macro lab)

Project locations default to the Desktop and can be overridden with
CREDIT_DEFAULT_DIR and MACRO_LAB_DIR.

Usage: python -m platform_core.build_inputs
"""
import json
import os
from pathlib import Path

import pandas as pd

from platform_core.contracts import (validate_loss_params, validate_no_lookahead,
                                     validate_portfolio, validate_scenarios)
from platform_core.logging_utils import get_logger, run_main

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
CREDIT_DIR = Path(os.getenv("CREDIT_DEFAULT_DIR", Path.home() / "Desktop" / "credit_default_model_project"))
MACRO_DIR = Path(os.getenv("MACRO_LAB_DIR", Path.home() / "Desktop" / "credit_model_project"))
PD_COLUMN = "pd_logit_recal"

log = get_logger(__name__)


def build_portfolio() -> pd.DataFrame:
    preds = pd.read_parquet(CREDIT_DIR / "data" / "processed" / "test_predictions.parquet")
    test = pd.read_parquet(CREDIT_DIR / "data" / "processed" / "test.parquet")
    if "loan_amnt" not in test.columns:
        raise KeyError(f"test.parquet has no 'loan_amnt'; columns: {list(test.columns)}")

    if "id" in test.columns:
        merged = preds.merge(test[["id", "loan_amnt"]], on="id", how="left", validate="one_to_one")
    else:
        # Fall back to row order, but only if the two files provably line up
        if len(test) != len(preds) or not (test["default_flag"].to_numpy() == preds["default_flag"].to_numpy()).all():
            raise ValueError("test.parquet and test_predictions.parquet do not align row by row")
        merged = preds.assign(loan_amnt=test["loan_amnt"].to_numpy())

    portfolio = merged.rename(columns={PD_COLUMN: "pd"})[
        ["id", "issue_date", "loan_amnt", "pd", "default_flag"]]
    portfolio["loan_amnt"] = portfolio["loan_amnt"].astype(float)
    return validate_portfolio(portfolio)


def build_loss_params() -> dict:
    comp = pd.read_csv(CREDIT_DIR / "reports" / "figures" / "expected_loss_components.csv").set_index("component")
    params = {
        "lgd": float(comp.loc["LGD", "assumed"]),
        "ead_ratio": float(comp.loc["EAD ratio", "assumed"]),
        "estimated_through": "2014-12-31",
        "source": "credit default model, estimated on 2012-2014 charge-offs (no 2015 information)",
    }
    return validate_loss_params(params)


def build_scenarios() -> pd.DataFrame:
    scen = pd.read_csv(MACRO_DIR / "reports" / "figures" / "scenario_results.csv")
    return validate_scenarios(scen)


def main():
    DATA.mkdir(exist_ok=True)
    portfolio = build_portfolio()
    portfolio.to_parquet(DATA / "portfolio.parquet", index=False)
    log.info("Portfolio: %d loans, $%.2fB originated, mean PD %.2f%%",
             len(portfolio), portfolio["loan_amnt"].sum() / 1e9, portfolio["pd"].mean() * 100)

    params = build_loss_params()
    validate_no_lookahead(portfolio, params)
    (DATA / "loss_params.json").write_text(json.dumps(params, indent=2))
    log.info("Loss parameters: LGD %.1f%%, EAD ratio %.1f%%, estimated through %s (no look-ahead)",
             params["lgd"] * 100, params["ead_ratio"] * 100, params["estimated_through"])

    scen = build_scenarios()
    scen.to_csv(DATA / "scenarios.csv", index=False)
    log.info("Scenarios: %s", ", ".join(scen["scenario"]))


if __name__ == "__main__":
    run_main(main)

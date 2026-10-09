"""
Data contracts between the two projects.

Every artifact is validated before use, so an upstream change (a renamed column,
an out-of-range PD, a missing baseline scenario) fails loudly instead of silently
producing wrong stress results.
"""
import pandas as pd

PORTFOLIO_COLUMNS = ["id", "loan_amnt", "pd"]
SCENARIO_COLUMNS = ["scenario", "cumulative_9q_loss_pct"]
BASELINE = "Baseline"


class ContractError(ValueError):
    """An input artifact does not satisfy its contract."""


def _require_columns(df: pd.DataFrame, cols: list[str], name: str) -> None:
    missing = [c for c in cols if c not in df.columns]
    if missing:
        raise ContractError(f"{name} is missing columns {missing}; has {list(df.columns)}")
    nulls = [c for c in cols if df[c].isna().any()]
    if nulls:
        raise ContractError(f"{name} has missing values in {nulls}")


def validate_portfolio(df: pd.DataFrame) -> pd.DataFrame:
    """Loan-level portfolio: one row per loan, a valid PD, and a positive amount."""
    _require_columns(df, PORTFOLIO_COLUMNS, "portfolio")
    if not df["id"].is_unique:
        raise ContractError("portfolio has duplicate loan ids")
    if not df["pd"].between(0, 1, inclusive="neither").all():
        raise ContractError("portfolio PDs must lie strictly between 0 and 1")
    if not (df["loan_amnt"] > 0).all():
        raise ContractError("portfolio loan amounts must be positive")
    return df


def validate_scenarios(df: pd.DataFrame) -> pd.DataFrame:
    """Scenario summary: unique names, a Baseline, and plausible cumulative losses."""
    _require_columns(df, SCENARIO_COLUMNS, "scenarios")
    if not df["scenario"].is_unique:
        raise ContractError("scenario names must be unique")
    if BASELINE not in set(df["scenario"]):
        raise ContractError(f"scenarios must include '{BASELINE}'")
    if not df["cumulative_9q_loss_pct"].between(0, 100, inclusive="neither").all():
        raise ContractError("cumulative 9-quarter losses must be between 0 and 100 percent")
    return df


def validate_loss_params(params: dict) -> dict:
    """LGD and EAD ratio, both shares between 0 and 1."""
    for key in ("lgd", "ead_ratio"):
        if key not in params:
            raise ContractError(f"loss parameters are missing '{key}'")
        if not 0 < params[key] <= 1:
            raise ContractError(f"'{key}' must be in (0, 1], got {params[key]}")
    return params

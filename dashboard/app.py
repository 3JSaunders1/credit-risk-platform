# pylint: disable=wrong-import-position
"""
dashboard/app.py
----------------
Credit Risk Platform: macroeconomic stress scenarios applied to a loan portfolio.

Tabs:
  Scenario losses   - expected loss by scenario, with the actual 2015 loss for reference
  PD distribution   - how a scenario shifts loan-level PDs
  Custom scenario   - choose a macro loss severity and see the portfolio impact
  Method            - how the link works, its assumptions, and its data contracts
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from scipy.special import logit

from platform_core.contracts import (validate_loss_params, validate_no_lookahead,
                                     validate_portfolio, validate_scenarios)
from platform_core.stress import avg_loss_rate, expected_loss, run_stress, stress_pd

DATA = ROOT / "data"
st.set_page_config(page_title="Credit Risk Platform", layout="wide")


@st.cache_data
def load_inputs():
    portfolio = validate_portfolio(pd.read_parquet(DATA / "portfolio.parquet"))
    scenarios = validate_scenarios(pd.read_csv(DATA / "scenarios.csv"))
    params = validate_loss_params(json.loads((DATA / "loss_params.json").read_text()))
    validate_no_lookahead(portfolio, params)
    realized_file = DATA / "realized_2015.json"
    realized = json.loads(realized_file.read_text()) if realized_file.exists() else None
    return portfolio, scenarios, params, realized


portfolio, scenarios, params, realized = load_inputs()
results = run_stress(portfolio, scenarios, params)
by_name = results.set_index("scenario")
total = portfolio["loan_amnt"].sum()
base_cum = scenarios.set_index("scenario").loc["Baseline", "cumulative_9q_loss_pct"]

# ── Header ────────────────────────────────────────────────────────────────────
st.title("Credit Risk Platform")
st.caption("Macroeconomic stress scenarios from a Bayesian VAR and dynamic loss model, applied to "
           "loan-level PDs from an out-of-time-validated credit default model.")

c1, c2, c3, c4 = st.columns(4)
c1.metric("Loans", f"{len(portfolio):,}")
c2.metric("Originated", f"${total / 1e9:.2f}B")
c3.metric("Baseline expected loss", f"${by_name.loc['Baseline', 'expected_loss'] / 1e6:.1f}M")
severe = by_name.loc["Severely Adverse"]
c4.metric("Severely Adverse expected loss", f"${severe['expected_loss'] / 1e6:.1f}M",
          f"{severe['vs_baseline'] * 100:+.1f}% vs. baseline", delta_color="inverse")

tab_losses, tab_pd, tab_custom, tab_method = st.tabs(
    ["Scenario losses", "PD distribution", "Custom scenario", "Method and assumptions"])

# ── Scenario losses ───────────────────────────────────────────────────────────
with tab_losses:
    order = results.sort_values("expected_loss")
    fig = go.Figure(go.Bar(x=order["scenario"], y=order["expected_loss"] / 1e6,
                           text=(order["expected_loss"] / 1e6).round(1), textposition="outside"))
    if realized:
        fig.add_hline(y=realized["loss"] / 1e6, line_dash="dash", line_color="red",
                      annotation_text=f"Actual 2015 loss: ${realized['loss'] / 1e6:.1f}M")
    fig.update_layout(height=420, yaxis_title="Expected loss ($ millions)")
    st.plotly_chart(fig, width="stretch")

    table = results.assign(
        mean_pd=lambda d: (d["mean_pd"] * 100).round(2),
        expected_loss=lambda d: (d["expected_loss"] / 1e6).round(1),
        loss_rate=lambda d: (d["loss_rate"] * 100).round(2),
        vs_baseline=lambda d: (d["vs_baseline"] * 100).round(1),
        logodds_shift=lambda d: d["logodds_shift"].round(3),
    ).rename(columns={"scenario": "Scenario", "logodds_shift": "Log-odds shift", "mean_pd": "Mean PD (%)",
                      "expected_loss": "Expected loss ($M)", "loss_rate": "Loss rate (%)",
                      "vs_baseline": "vs. baseline (%)"})
    st.dataframe(table, width="stretch", hide_index=True)
    if realized:
        st.caption(f"The portfolio's actual 2015 loss (about ${realized['loss'] / 1e6:.0f}M) sits near the "
                   "Adverse scenario: the concept drift found in the credit model was roughly the size "
                   "of a moderate recession. Realized outcomes are shown for validation only and are "
                   "never used to compute the stress results.")

# ── PD distribution ───────────────────────────────────────────────────────────
with tab_pd:
    choice = st.selectbox("Scenario", [s for s in results["scenario"] if s != "Baseline"],
                          index=1)
    shift = by_name.loc[choice, "logodds_shift"]
    sample = portfolio["pd"].sample(min(50_000, len(portfolio)), random_state=0).to_numpy()
    fig = go.Figure()
    fig.add_trace(go.Histogram(x=sample * 100, name="Baseline", opacity=0.6, nbinsx=60, histnorm="percent"))
    fig.add_trace(go.Histogram(x=stress_pd(sample, shift) * 100, name=choice, opacity=0.6,
                               nbinsx=60, histnorm="percent"))
    fig.update_layout(barmode="overlay", height=400, xaxis_title="Loan-level PD (%)",
                      yaxis_title="Share of loans (%)")
    st.plotly_chart(fig, width="stretch")

    m1, m2, m3 = st.columns(3)
    m1.metric("Mean PD, baseline", f"{portfolio['pd'].mean() * 100:.2f}%")
    m2.metric(f"Mean PD, {choice}", f"{by_name.loc[choice, 'mean_pd'] * 100:.2f}%")
    if realized:
        m3.metric("Actual 2015 default rate", f"{realized['default_rate'] * 100:.2f}%")
    st.caption("Every loan's PD shifts by the same amount in log-odds, so the ranking of loans by risk "
               "is unchanged; riskier loans gain more in absolute PD.")

# ── Custom scenario ───────────────────────────────────────────────────────────
with tab_custom:
    st.write("Choose a macroeconomic loss severity: the 9-quarter cumulative consumer charge-off rate "
             f"implied by the scenario (the baseline is {base_cum:.2f}%; actual 2008-2010 losses were 10.70%).")
    custom_cum = st.slider("Cumulative 9-quarter macro loss (%)", 3.0, 16.0, 10.7, 0.1)
    custom_shift = float(logit(avg_loss_rate(custom_cum)) - logit(avg_loss_rate(base_cum)))
    pds = stress_pd(portfolio["pd"].to_numpy(), custom_shift)
    el = expected_loss(pds, portfolio["loan_amnt"].to_numpy(), params["lgd"], params["ead_ratio"]).sum()
    base_el = by_name.loc["Baseline", "expected_loss"]

    k1, k2, k3 = st.columns(3)
    k1.metric("Log-odds shift", f"{custom_shift:+.3f}")
    k2.metric("Mean PD", f"{pds.mean() * 100:.2f}%")
    k3.metric("Expected loss", f"${el / 1e6:.1f}M", f"{(el / base_el - 1) * 100:+.1f}% vs. baseline",
              delta_color="inverse")

# ── Method and assumptions ────────────────────────────────────────────────────
with tab_method:
    st.markdown(f"""
**How the link works**

1. The macro lab projects each scenario's consumer charge-off path; its 9-quarter cumulative loss
   gives an average loss rate.
2. Each scenario's distance from the Baseline, in log-odds, becomes a shift:
   `shift = logit(scenario rate) - logit(baseline rate)`.
3. Every loan's PD is stressed by that shift: `stressed PD = expit(logit(PD) + shift)`, the same
   intercept-shift mechanism the credit model uses for recalibration.
4. Expected loss = stressed PD x LGD x EAD ratio x loan amount, summed over the portfolio.

**Inputs**
- Portfolio: {len(portfolio):,} loans from the 2015 vintage, with recalibrated PDs
- LGD {params['lgd'] * 100:.1f}% and EAD ratio {params['ead_ratio'] * 100:.1f}%, estimated on 2012-2014
  charge-offs only (through {params['estimated_through']})

**Assumptions**
- The model's PDs represent baseline conditions, so scenarios are measured relative to the Baseline.
- The macro shift applies uniformly in log-odds: a top-down approach that preserves ranking but does not
  let different borrower segments respond differently.
- LGD and EAD are held at their historical averages under stress.
- The 9-quarter macro horizon is applied as a relative stress to the portfolio's lifetime PDs.

**Data contracts** (checked on every load): required columns and no missing values, PDs strictly between
0 and 1, positive loan amounts, unique loan ids, a Baseline scenario, plausible loss ranges, and no
look-ahead: loss parameters must be estimated on data ending before the portfolio's first loan.
""")

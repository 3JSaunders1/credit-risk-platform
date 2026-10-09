# Model Card: Credit Risk Platform

## Intended use
Research and portfolio demonstration of a top-down macroeconomic stress test for a
consumer loan portfolio. Not intended for real reserving, capital, or lending decisions.

## Components
- **Macro scenarios:** five scenarios from the Macro-Driven Credit Risk Lab (Bayesian VAR
  macro paths and a dynamic charge-off model), summarized as 9-quarter cumulative losses
- **Portfolio:** 283,026 Lending Club loans from the 2015 vintage ($3.62B originated), with
  recalibrated PDs from the Credit Default Prediction Model (out-of-time AUC 0.655)
- **Loss parameters:** LGD 88.9% and EAD ratio 57.5%, estimated on 2012-2014 charge-offs only

## Method
Each scenario's average loss rate is converted to a log-odds shift relative to the Baseline,
and every loan's PD is shifted by that amount: `stressed PD = expit(logit(PD) + shift)`.
Expected loss = stressed PD x LGD x EAD ratio x loan amount.

## Performance and validation
- **Baseline reproduces the credit model's own expected loss exactly** ($238.6M), confirming
  the link adds nothing when there is no stress
- **Portfolio losses rank scenarios exactly as the macro lab does** (Spearman correlation 1.0)
- **Scenario results:** Adverse +16%, Stagflation +30%, Severely Adverse +35%, Sharp V-shaped +40%
  vs. baseline
- **Historical reference:** the portfolio's actual 2015 loss ($274.0M) sits near the Adverse
  scenario ($277.2M), showing the concept drift found in the credit model was roughly the size
  of a moderate recession scenario

## Data contracts and temporal integrity
Every input is validated on load: required columns and no missing values, PDs strictly between
0 and 1, positive loan amounts, unique loan ids, a Baseline scenario, and plausible loss ranges.
Loss parameters must be estimated on data ending before the portfolio's first loan; a violation
raises an error. Realized 2015 outcomes are stored separately and used only for display.

## Known limitations
- **Top-down shift:** every loan moves by the same log-odds amount, so borrower segments
  cannot respond differently to the same scenario
- **LGD and EAD are held constant** under stress, though severity typically worsens in downturns
- **Horizon mismatch:** a 9-quarter macro stress is applied as a relative shift to lifetime PDs
- **Baseline assumption:** the model's PDs are treated as baseline conditions
- **Inherited limitations:** the macro scenarios understate housing- and credit-driven crises,
  and the PD model has modest discrimination from application data alone

## Monitoring plan
- Rebuild inputs (`make inputs`) whenever either source model is re-estimated
- Re-check that the Baseline reproduces the credit model's expected loss
- Compare scenario losses with realized outcomes as new vintages mature

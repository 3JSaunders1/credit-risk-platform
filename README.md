# Credit Risk Platform

[![Tests](https://github.com/3JSaunders1/credit-risk-platform/actions/workflows/tests.yml/badge.svg)](https://github.com/3JSaunders1/credit-risk-platform/actions/workflows/tests.yml)

An integrated credit stress-testing platform: macroeconomic scenarios from my [Macro-Driven Credit Risk Lab](https://github.com/3JSaunders1/macro-credit-risk-lab) flow through loan-level probabilities of default from my [Credit Default Prediction Model](https://github.com/3JSaunders1/credit-default-model) into portfolio expected losses (PD × LGD × EAD). It answers the question at the heart of bank stress testing and CECL reserving: **if the economy follows a given path, how much would this loan portfolio lose?**

The link is enforced by data contracts and temporal-integrity checks, validated end to end, served through an interactive Streamlit dashboard, and packaged in Docker.

---

## Key Results

**Portfolio:** 283,026 loans from the 2015 vintage, $3.62B originated.

| Scenario | Log-odds shift | Mean PD | Expected loss | Loss rate | vs. baseline |
|---|---|---|---|---|---|
| Baseline | 0.000 | 13.43% | $238.6M | 6.58% | — |
| Adverse | 0.181 | 15.59% | $277.2M | 7.65% | +16.2% |
| Stagflation | 0.319 | 17.40% | $309.7M | 8.54% | +29.8% |
| Severely Adverse | 0.369 | 18.10% | $322.2M | 8.89% | +35.0% |
| Sharp V-shaped (COVID-like) | 0.416 | 18.78% | $334.5M | 9.23% | +40.2% |

**What the results show:**
- **The integration is exact at baseline:** with no stress, the platform reproduces the credit model's own expected loss to the dollar ($238.6M).
- **Losses rise consistently with severity,** ranking the scenarios exactly as the macro lab does.
- **A historical cross-check:** the portfolio's **actual** 2015 loss was **$274.0M**, nearly identical to the **Adverse** scenario ($277.2M). The concept drift found in the credit model, where borrowers looked the same but defaulted more, was roughly the size of a moderate recession scenario.
- **Stagflation hits nearly as hard as a severe recession** with half the unemployment increase, inheriting the macro lab's finding that rising inflation adds to borrower stress.

---

## How It Works

```
Macro-Driven Credit Risk Lab                      Credit Default Prediction Model
  BVAR scenarios → dynamic loss model               recalibrated loan-level PDs
  → 9-quarter cumulative losses                     LGD and EAD (2012-2014)
              │                                                 │
              └─────────────► data contracts ◄──────────────────┘
                             (+ temporal integrity)
                                     │
                    scenario log-odds shift → stressed PDs
                                     │
                    expected loss = PD × LGD × EAD × amount
                                     │
                         Streamlit dashboard (Docker)
```

1. **Scenario severity.** Each scenario's 9-quarter cumulative loss gives an average annualized loss rate.
2. **A log-odds shift.** Each scenario's distance from the Baseline becomes a shift: `shift = logit(scenario rate) − logit(baseline rate)`.
3. **Stressed PDs.** Every loan's PD moves by that shift: `stressed PD = expit(logit(PD) + shift)`. This is the **same intercept-shift mechanism** the credit model uses for recalibration, so it preserves the ranking of loans by risk while raising every PD.
4. **Expected loss.** Stressed PD × LGD × EAD ratio × loan amount, summed over the portfolio.

This is a **top-down** stress link, a standard first-generation approach in bank stress testing: simple, transparent, and consistent with both source models.

---

## Data Contracts and Temporal Integrity

Every input is validated on load (`platform_core/contracts.py`), so a change in either source project fails loudly instead of silently producing wrong results:

| Contract | What it enforces |
|---|---|
| **Portfolio** | Required columns with no missing values, unique loan ids, PDs strictly between 0 and 1, positive loan amounts |
| **Scenarios** | Unique names, a Baseline scenario, cumulative losses in a plausible range |
| **Loss parameters** | LGD and EAD ratio between 0 and 1 |
| **No look-ahead** | LGD and EAD must be estimated on data ending **before** the portfolio's first loan; a violation raises an error |

**Why the last one matters:** the 2015 portfolio's own realized LGD and EAD are available in the data, and using them would quietly leak future information into the stress results. The platform uses parameters estimated through December 2014 and **enforces** that cutoff. Realized 2015 outcomes are stored separately (`data/realized_2015.json`) and used only for display.

---

## Dashboard

`make dashboard` (or `make docker-run` for the containerized version):

- **Scenario losses:** expected loss by scenario, with the actual 2015 loss marked for reference
- **PD distribution:** how a scenario shifts the distribution of loan-level PDs
- **Custom scenario:** choose any macro loss severity and see the portfolio's stressed PD and expected loss
- **Method and assumptions:** how the link works, its assumptions, and its data contracts

---

## Validation and Engineering

**18 automated tests** run on every push through **GitHub Actions:**

| Test file | What it checks |
|---|---|
| `test_contracts.py` | Valid inputs pass; missing columns, out-of-range PDs, duplicate ids, negative amounts, missing values, a missing Baseline, and invalid loss parameters all fail |
| `test_stress.py` | The Baseline shift is zero, stress raises every PD while preserving ranking, the expected loss formula, and losses rising with severity |
| `test_integration.py` | End to end on the real committed data: every artifact satisfies its contract, no look-ahead (and a deliberate look-ahead is caught), the Baseline reproduces the credit model's expected loss exactly, and portfolio losses rank scenarios exactly as the macro lab does |
| `test_dashboard.py` | The full dashboard runs without errors |

**Other practices:**
- **Docker:** the image pins Python 3.11 and every dependency, and serves the dashboard by default
- **Structured logging:** every step logs timestamped start, finish, and duration messages, with full tracebacks on failure
- **Committed inputs:** the validated artifacts in `data/` let anyone run the platform, and CI test it, without the two source projects; `make inputs` refreshes them when either model changes
- **Pinned dependencies** in `requirements.txt`, and a **model card** in `docs/model_card.md`

---

## Limitations

- **A top-down shift moves every loan by the same log-odds amount,** so borrower segments (for example, by FICO band or loan purpose) cannot respond differently to the same scenario.
- **LGD and EAD are held at historical averages under stress,** although loss severity typically worsens in downturns.
- **Horizon mismatch:** a 9-quarter macro stress is applied as a relative shift to lifetime (36-month) PDs.
- **The model's PDs are treated as baseline conditions,** with scenarios measured relative to them.
- **Inherited limitations:** the macro scenarios understate housing- and credit-driven crises (the Severely Adverse scenario is about 12% milder than 2008), and the PD model has modest discrimination from application data alone.

---

## Further Development

- **Borrower-level macro sensitivity:** a PD model with macro variables estimated across a full credit cycle, so segments respond differently to the same scenario
- **Stressed LGD and EAD,** conditioned on the macro path
- **Quarterly loss timing,** projecting losses over the scenario horizon rather than a single portfolio total
- **Cloud deployment** of the containerized dashboard

---

## Project Structure

```
credit-risk-platform/
├── .github/workflows/tests.yml   # CI: runs the test suite on every push
├── dashboard/
│   └── app.py                    # Streamlit dashboard
├── data/                         # validated inputs from the two source projects
│   ├── portfolio.parquet         # 2015 loans: id, issue date, amount, recalibrated PD
│   ├── loss_params.json          # LGD, EAD ratio, and estimation cutoff
│   ├── scenarios.csv             # macro scenario cumulative losses
│   └── realized_2015.json        # actual 2015 outcomes (display only)
├── docs/
│   └── model_card.md
├── platform_core/
│   ├── contracts.py              # data contracts and the no-look-ahead check
│   ├── stress.py                 # log-odds shifts, stressed PDs, expected loss
│   ├── build_inputs.py           # collects and validates artifacts from both projects
│   ├── run_stress.py             # runs every scenario through the portfolio
│   └── logging_utils.py          # shared logging
├── reports/
│   └── stress_results.csv
├── tests/                        # 18 tests
├── .dockerignore
├── Dockerfile                    # serves the dashboard on port 8501
├── Makefile
├── pytest.ini
└── requirements.txt
```

---

## How to Run

**1. Set up the environment**
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

**2. Run the stress test and dashboard**
```bash
make stress       # every scenario through the portfolio
make dashboard    # Streamlit dashboard at http://localhost:8501
make test         # test suite
```

**3. Or run it in Docker**
```bash
make docker-test  # tests in a container
make docker-run   # dashboard served from the container at http://localhost:8501
```

**4. Refresh inputs from the source projects** (requires both projects locally)
```bash
make inputs
```
Project locations default to the Desktop and can be set with `CREDIT_DEFAULT_DIR` and `MACRO_LAB_DIR`.

---

## Tech Stack

Python · pandas · NumPy · SciPy · Plotly · Streamlit · pytest · Docker · GitHub Actions · Make · Parquet

---

© 2026 John Saunders. All rights reserved. This code is shared for viewing and evaluation only.
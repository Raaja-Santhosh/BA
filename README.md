# Loan Approval Process Bottleneck Analysis
*End-to-End Process Mining & Machine Learning Case Study*

## 📖 Project Overview
A major financial institution's personal loan approval process was suffering from unpredictable turnaround times. Leadership lacked visibility into where the delays were actually happening—was it Underwriting, Document Check, or Manager Review? 

Process mining of the raw **BPI Challenge 2012 event log** revealed that the process as it actually runs is chaotic. The official dataset contains **262,200 raw events across 13,087 loan applications**. For this analysis, we filtered down to ~164,000 `COMPLETE` lifecycle transitions and mapped the raw Dutch `W_` activity codes to standard English banking stages (e.g., `W_Valideren aanvraag` → `Document Check`, `W_Nabellen offertes` → `Underwriting`).

**0% of cases** conformed to the theoretical textbook happy path. Instead of flowing cleanly from submission to approval, applications were ping-ponging backward in the pipeline due to missing documents.

This project diagnoses the root cause of these delays using **Process Mining**, quantifies the financial impact using **Non-Parametric Statistics**, projects the ROI of a process fix using **Monte Carlo Simulation**, and attempts to predict SLA breaches using **Machine Learning**.

---

## 🚀 Key Findings & Recommendations
1. **The Bottleneck**: **Manager Review** is responsible for 48% of total process delay, but the *root cause* is upstream rework (specifically `Underwriting → Document Check`).
2. **The Cost of Rework**: True backward rework adds approximately **12 days** (mean difference) to the processing time. (Mann-Whitney U Test p < 0.0001, Rank-Biserial Correlation = −0.83).
3. **The Simulation**: By implementing a hard document completeness gate before Underwriting, the best-case simulation (100% rework elimination) projects the bank would cut average cycle times by ~74%. Even a conservative 50% rework reduction yields a 37% improvement.

### Sensitivity Analysis — Projected Savings by Rework Elimination Rate

| Rework Eliminated | Projected Avg E2E | Days Saved | Cycle Time Reduction |
|---|---|---|---|
| 50% | 5.4 days | 3.2 days | 37% |
| 75% | 3.9 days | 4.8 days | 55% |
| 100% (best case) | 2.3 days | 6.3 days | 74% |

---

## 🧠 Methodology & Technical Architecture

### 1. Data Engineering (`src/ingest.py`)
- **Dataset**: [BPI Challenge 2012](https://doi.org/10.4121/uuid:3926db30-f712-4394-aebc-75976070e91f) — real event logs from a Dutch financial institution.
- **Processing**: Filtered 262,200 raw events down to ~164,000 `COMPLETE` lifecycle transitions. Mapped raw Dutch `W_` activity codes to standard English banking stages. This mapping is an analytical choice for readability; it is documented in `src/ingest.py`.

### 2. Process Discovery (`src/discovery.py`)
- Used `pm4py` to mine the "as-is" Directly-Follows Graph (DFG) from the raw XES event logs, mapping the exact spaghetti paths cases took.
- Visualized with `NetworkX` (replacing `graphviz` due to missing system binaries).

### 3. Conformance Checking (`src/conformance.py`)
- Built a theoretical "happy path" Petri net and ran Token-Based Replay against the real data.
- **Token-Based Replay Fitness: 0.54** — on average, about half of the expected steps in any given case follow the model before deviating into rework.
- **Trace-Level Conformance: 0%** — not a single case perfectly matched the strict linear path end-to-end.
- These are two different metrics. The fitness score (0.54) measures how much of the model each trace can reproduce on average. The 0% conformance rate measures how many traces are a *perfect* match. A rigid textbook Petri net will often produce near-zero perfect conformance on real-world data — this is a known property of strict baselines, not necessarily a profound discovery. What it does confirm is that the process has drifted significantly from the linear ideal.

### 4. Cycle Time & Bottleneck Analysis (`src/cycle_time.py` & `src/rework.py`)
- Extracted cycle times for every stage across all 13,087 cases.
- Benchmarked against an **assumed 10-day E2E SLA** (a common retail lending threshold; this is not a contractual figure from the dataset).
- Identified over **5,000 instances** of backward rework loops (cases moving from a later stage back to an earlier stage).

### 5. Statistical Validation (`src/stats_tests.py`)
- **Normality Check**: Shapiro-Wilk test confirmed non-normal distributions in both cohorts (p < 0.0001), ruling out parametric tests.
- **Hypothesis Test**: Mann-Whitney U test (two-sided, p < 0.0001) proved a statistically significant difference in E2E duration between rework and non-rework cohorts.
- **Effect Size**: Rank-Biserial Correlation = −0.83 (a large non-parametric effect). This is the correct effect-size metric to pair with Mann-Whitney U, unlike Cohen's d which assumes normality.
- **Result**: Cases with backward rework average 14.3 days; cases without average 2.3 days — a mean difference of approximately 12 days.

### 6. Monte Carlo Simulation (`src/simulation.py`)
- Built a bootstrapped simulation (100 iterations, seeded for reproducibility) to project cycle-time savings.
- **Method**: For each iteration, replaced the durations of "messy" (rework) cases with random draws from the "clean" (no rework) distribution.
- **Key Assumption (Exchangeability)**: This assumes messy cases would behave identically to clean cases if rework were removed. In reality, some Manager Review delay may be genuine queueing/capacity constraints unrelated to documents.
- To address this, the simulation includes a **sensitivity analysis** at 50%, 75%, and 100% rework elimination rates (see table above).

### 7. Predictive Modeling (`src/predictive_model.py`)
- **Objective**: Predict SLA breaches from a snapshot taken immediately after the first Document Check event.
- **Leakage Defense**:
  1. *Temporal cutoff*: All features (elapsed time, event count, submission day) are computed strictly from events at or before the Document Check timestamp. No future-stage data leaks into features.
  2. *Case-level split*: Each row represents exactly one unique `case_id`, so a standard train/test split automatically guarantees no intra-case leakage.
- **Results** (threshold = 0.5):

| Model | AUC | Precision | Recall |
|---|---|---|---|
| Logistic Regression | 0.54 | 0.64 | 0.17 |
| Random Forest | 0.51 | 0.61 | 0.59 |

- **Interpretation**: Both models perform near chance (AUC ≈ 0.5), indicating that the three features available at the Document Check checkpoint are insufficient to reliably predict downstream SLA breaches. This is an honest negative result: human-driven queueing delays in Manager Review are not meaningfully predictable from early temporal signals alone. Note that the Logistic Regression precision of 0.64 should be compared against the naive baseline of always predicting "breach" (which yields ~34% precision, the base rate), so 0.64 does show *some* signal — but the extremely low recall (0.17) means the model catches very few actual breaches.

---

## 📊 Executive Dashboard
The project includes a multi-tab interactive Streamlit dashboard designed for non-technical operations leadership:

| Tab | Visualization |
|---|---|
| Case Timelines | Plotly Gantt charts for individual loan journeys |
| Stage Bottlenecks | Bar chart of actual stage durations vs SLA targets |
| Process Map | The mined "as-is" DFG showing spaghetti paths |
| Rework Loops | Plotly Sankey diagram of backward transition flows |
| SLA Compliance | Weekly compliance trend line |
| What-If Simulation | Projected savings with sensitivity metrics |

![Executive Dashboard](outputs/figures/dashboard.png)
*(Screenshot placeholder — run `streamlit run dashboard/app.py` and capture the dashboard)*

---

## ⚠️ Assumptions & Limitations

| Item | Detail |
|---|---|
| **SLA Benchmark** | The 10-day E2E SLA is an assumed retail lending threshold, not a contractual figure from the dataset. |
| **Activity Mapping** | Raw Dutch `W_` codes were mapped to English banking stages for readability. This is an analytical simplification. |
| **Conformance Baseline** | The 0% conformance rate is measured against a rigid linear Petri net — a known strict baseline that will produce near-zero conformance on most real-world logs. |
| **Simulation Exchangeability** | The Monte Carlo fix assumes messy cases would behave like clean cases if rework were removed. Some delays may be genuine capacity constraints. The sensitivity table addresses this partially. |
| **ML Feature Limitation** | Only 3 features are available at the prediction checkpoint. Richer features (e.g., document type, applicant credit score) would likely improve model performance but are not present in the dataset. |
| **"~12 days" Precision** | The 12-day mean difference is reported as "approximately" because Mann-Whitney U tests distributional shift, not a precise point difference. |

---

## ⚙️ How to Run This Project Locally

### 1. Install Dependencies
```bash
pip install pandas numpy scipy scikit-learn plotly streamlit networkx pm4py
```

### 2. Run the Analytical Pipeline
Execute the scripts in order to regenerate the data, process models, and metrics:
```bash
python src/ingest.py
python src/discovery.py
python src/conformance.py
python src/cycle_time.py
python src/rework.py
python src/stats_tests.py
python src/simulation.py
python src/predictive_model.py
```

### 3. Launch the Dashboard
```bash
streamlit run dashboard/app.py
```
Then open `http://localhost:8501` in your browser.

---

## 📁 Project Structure
```
BA Project/
├── src/
│   ├── ingest.py              # Data download, filtering, stage mapping
│   ├── discovery.py           # DFG mining with pm4py
│   ├── conformance.py         # Petri net + token-based replay
│   ├── cycle_time.py          # Stage duration & SLA analysis
│   ├── rework.py              # Backward rework loop detection
│   ├── stats_tests.py         # Shapiro-Wilk, Mann-Whitney U, effect size
│   ├── simulation.py          # Monte Carlo + sensitivity analysis
│   └── predictive_model.py    # LogReg & Random Forest SLA prediction
├── dashboard/
│   └── app.py                 # Multi-tab Streamlit dashboard
├── memo/
│   └── one_pager.md           # Executive memo for VP-level audience
├── outputs/
│   ├── metrics.json           # All computed metrics (serialized)
│   ├── dfg_data.json          # DFG edge/node data
│   ├── deviations.json        # Conformance deviation details
│   └── figures/               # Generated visualizations
├── data/
│   ├── raw/                   # Original XES event log
│   └── processed/             # Cleaned parquet file
├── ASSUMPTIONS.md             # Documented analytical assumptions
└── README.md                  # This file
```

---

## 📚 Academic Citation
van Dongen, B.F. (2012). *BPI Challenge 2012*. Eindhoven University of Technology. Dataset.  
DOI: [10.4121/uuid:3926db30-f712-4394-aebc-75976070e91f](https://doi.org/10.4121/uuid:3926db30-f712-4394-aebc-75976070e91f)

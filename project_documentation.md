# Project Documentation — Loan Approval Process Bottleneck Analysis

> **Version:** 3.0 (Final Audited)  
> **Last Updated:** September 3, 2026  
> **Repository:** [github.com/Raaja-Santhosh/BA](https://github.com/Raaja-Santhosh/BA)

---

## Table of Contents
1. [Executive Summary](#1-executive-summary)
2. [Problem Statement](#2-problem-statement)
3. [Dataset](#3-dataset)
4. [Data Engineering & Activity Mapping](#4-data-engineering--activity-mapping)
5. [Phase 1 — Process Discovery](#5-phase-1--process-discovery)
6. [Phase 2 — Conformance Checking](#6-phase-2--conformance-checking)
7. [Phase 3 — Cycle Time & Bottleneck Analysis](#7-phase-3--cycle-time--bottleneck-analysis)
8. [Phase 4 — Rework Loop Detection](#8-phase-4--rework-loop-detection)
9. [Phase 5 — Statistical Validation](#9-phase-5--statistical-validation)
10. [Phase 6 — Monte Carlo Simulation & Sensitivity Analysis](#10-phase-6--monte-carlo-simulation--sensitivity-analysis)
11. [Phase 7 — Predictive Modeling (SLA Breach)](#11-phase-7--predictive-modeling-sla-breach)
12. [Phase 8 — Executive Dashboard](#12-phase-8--executive-dashboard)
13. [Phase 9 — Executive Memo](#13-phase-9--executive-memo)
14. [Assumptions & Limitations](#14-assumptions--limitations)
15. [Tech Stack & Dependencies](#15-tech-stack--dependencies)
16. [Project Structure](#16-project-structure)
17. [How to Reproduce](#17-how-to-reproduce)
18. [Academic Citation](#18-academic-citation)

---

## 1. Executive Summary

A Dutch financial institution's personal loan approval process was experiencing unpredictable turnaround times, leading to SLA breaches in 34% of all applications. Leadership had no visibility into the root cause.

Using **process mining** on 13,087 real loan applications, this project:
- Reverse-engineered the actual "as-is" process from raw system event logs
- Identified that **Manager Review** accounts for 48% of total delay
- Proved mathematically that the root cause is **backward rework loops** (applications bouncing from Underwriting back to Document Check), adding approximately **12 days** per affected case
- Simulated the ROI of a process fix: a document completeness gate could save **3.2 to 6.3 days per application** depending on effectiveness (37–74% cycle time reduction)
- Attempted to build a predictive early-warning model, which produced an honest negative result (AUC ≈ 0.5) — proving that human-driven queueing delays are not predictable from early temporal features alone

---

## 2. Problem Statement

**Business Question:** Why are loan approval turnaround times unpredictable, and what is the root cause of SLA breaches?

**Hypothesis:** The delays are not caused by any single slow stage, but by *structural rework loops* — applications bouncing backward in the pipeline because of incomplete information submitted upfront.

**Success Criteria:** Identify the specific bottleneck, quantify the financial impact of rework in days, and project the ROI of a specific process redesign recommendation.

---

## 3. Dataset

| Property | Value |
|---|---|
| **Name** | BPI Challenge 2012 |
| **Source** | Eindhoven University of Technology (4TU.ResearchData) |
| **DOI** | [10.4121/uuid:3926db30-f712-4394-aebc-75976070e91f](https://doi.org/10.4121/uuid:3926db30-f712-4394-aebc-75976070e91f) |
| **Format** | XES (eXtensible Event Stream) |
| **Raw Events** | 262,200 |
| **Cases (Loan Applications)** | 13,087 |
| **Events After Filtering** | ~164,000 (`COMPLETE` lifecycle only) |
| **Date Range** | October 2011 — March 2012 |
| **Domain** | Personal loan applications at a Dutch financial institution |

The BPI Challenge 2012 dataset is one of the most widely cited benchmarks in the process mining research community. It was selected because it is a real-world, unstructured, high-volume event log — exactly the type of messy data that process mining is designed to handle.

---

## 4. Data Engineering & Activity Mapping

**Script:** `src/ingest.py`

### 4.1 Download & Ingestion
The script automatically downloads the raw `.xes.gz` file from Figshare and reads it using `pm4py.read_xes()`.

### 4.2 Lifecycle Filtering
The raw log contains three lifecycle transitions per activity: `SCHEDULE`, `START`, and `COMPLETE`. We filtered to **only `COMPLETE` events** because:
- It gives us one clean timestamp per activity execution per case
- It simplifies cycle time calculations
- **Assumption:** The `COMPLETE` timestamp accurately reflects when work finished

### 4.3 Activity-to-Stage Mapping
The raw dataset uses Dutch activity codes. We mapped them to human-readable English banking stages for analysis readability. **This mapping is an analytical simplification** — not a 1:1 translation.

| Business Stage | Raw Activity Codes |
|---|---|
| **Submitted** | `A_SUBMITTED`, `A_PARTLYSUBMITTED` |
| **Document Check** | `A_PREACCEPTED`, `W_Completeren aanvraag` |
| **Underwriting** | `A_ACCEPTED`, `A_FINALIZED`, `O_CREATED`, `O_SENT` |
| **Manager Review** | `W_Nabellen offertes`, `A_APPROVED`, `A_REGISTERED`, `A_ACTIVATED` |
| **Rejected** | `A_DECLINED` |
| **Cancelled** | `A_CANCELLED`, `O_CANCELLED` |
| **Other** | Everything else |

### 4.4 Output
- Deduplicated and sorted by `(case_id, timestamp)`
- Saved as `data/processed/processed_event_log.parquet`

---

## 5. Phase 1 — Process Discovery

**Script:** `src/discovery.py`

### 5.1 What It Does
Uses `pm4py` to mine the "as-is" process from the event log. Three algorithms are executed:

| Algorithm | Purpose | Output |
|---|---|---|
| **Frequency DFG** | Maps how many times each stage-to-stage transition occurs | `outputs/dfg_data.json` |
| **Performance DFG** | Measures the average time taken for each transition | Merged into `dfg_data.json` |
| **Inductive Miner** | Discovers a structured Petri net from the log | Used downstream in conformance |
| **Heuristics Miner** | Alternative discovery for comparison | Stored in metrics |

### 5.2 Visualization
- A static PNG of the DFG is generated using `NetworkX` (because `graphviz` system binaries were not available on the development machine)
- Edge thickness is proportional to transition frequency
- Start activities are colored green; end activities are orange
- A 1% frequency threshold filters out noise edges

### 5.3 Key Observation
The DFG reveals a "spaghetti" process — edges going in every direction, including heavy backward loops from later stages back to earlier stages.

---

## 6. Phase 2 — Conformance Checking

**Script:** `src/conformance.py`

### 6.1 The Reference Model
We manually constructed an "as-designed" Petri net representing the idealized happy path:

```
Submitted → Document Check → Underwriting → Manager Review → (Approved | Rejected | Cancelled)
```

This is a **strictly linear model** with no loops, no parallelism, and no optional paths. It is intentionally rigid — it serves as a baseline measurement tool, not a realistic process model.

### 6.2 Token-Based Replay
We chose Token-Based Replay over Alignment-Based Conformance because:
- The dataset has 13,087 traces — alignment-based checking is computationally expensive at this scale
- Token-based replay is the standard approach for large real-world logs

### 6.3 Results

| Metric | Value | Meaning |
|---|---|---|
| **Token-Based Replay Fitness** | 0.54 | On average, about 54% of expected steps in a trace can be replayed before the model fails to match reality |
| **Perfectly Conformant Cases** | 0 (0%) | Not a single case perfectly matched the linear happy path end-to-end |
| **Total Variants** | Hundreds | The process has extreme variability |

### 6.4 Important Nuance
**0% conformance is not a discovery — it is a measurement.** The BPI Challenge 2012 dataset is well-known in the process mining literature for being unstructured (heavy loops, optional paths, parallelism). Getting 0% perfect conformance against a rigid linear Petri net is the *expected baseline result*, not a shocking finding. What it confirms is the degree to which reality has drifted from the idealized model that legacy management may still assume is being followed.

**Why two numbers (0.54 fitness vs 0% conformance)?** These measure different things:
- **Fitness (0.54):** "On average, how much of the model can each trace reproduce?" — a continuous score
- **Conformance (0%):** "How many traces are a perfect end-to-end match?" — a binary pass/fail

They are not contradictory. A fitness of 0.54 with 0% perfect conformance means: every case partially follows the model, but none follows it completely.

---

## 7. Phase 3 — Cycle Time & Bottleneck Analysis

**Script:** `src/cycle_time.py`

### 7.1 Methodology
- For each event, calculated the time elapsed since the previous event in the same case
- Aggregated total duration per stage per case
- Compared against assumed SLA thresholds (see Assumptions section)

### 7.2 SLA Thresholds (Assumed)

| Stage | Assumed SLA |
|---|---|
| Document Check | ≤ 2 business days |
| Underwriting | ≤ 3 business days |
| Manager Review | ≤ 1 business day |
| End-to-End | ≤ 10 business days |

**These are not contractual figures from the dataset.** They are assumed based on common retail lending benchmarks.

### 7.3 Results

| Metric | Value |
|---|---|
| E2E Mean Duration | 8.6 days |
| E2E Median Duration | 0.81 days |
| E2E 90th Percentile | 26+ days |
| E2E SLA Breach Rate | 34% |
| Primary Bottleneck | Manager Review (48% of total delay) |

The large gap between mean (8.6 days) and median (0.81 days) indicates the distribution is heavily right-skewed — a small number of cases take extremely long, pulling the average up.

---

## 8. Phase 4 — Rework Loop Detection

**Script:** `src/rework.py`

### 8.1 Definition of Rework
A "backward rework loop" is defined as any transition where a case moves from a later stage to an earlier stage in the defined `STAGE_ORDER`:
```
Submitted (0) → Document Check (1) → Underwriting (2) → Manager Review (3) → Outcome (4)
```

If a case goes from Underwriting (order 2) back to Document Check (order 1), that is a backward rework loop.

### 8.2 Results

| Metric | Value |
|---|---|
| Cases with any repeated stage | ~100% |
| Cases with true backward rework | 6,886 (53%) |
| Total backward loop instances | 5,089+ |
| Avg E2E with rework | 14.3 days |
| Avg E2E without rework | 2.3 days |

### 8.3 Top Rework Loop Pairs
The most frequent backward transitions were:
1. `Underwriting → Document Check` — the primary structural flaw
2. `Manager Review → Document Check`
3. `Manager Review → Underwriting`

---

## 9. Phase 5 — Statistical Validation

**Script:** `src/stats_tests.py`

### 9.1 Objective
Prove (or disprove) that backward rework loops *cause* statistically significant delays, rather than just being correlated with longer cases.

### 9.2 Methodology

**Step 1: Check normality**
- Ran a Shapiro-Wilk test on a random sample of 1,000 cases from each cohort (rework vs no-rework)
- Both cohorts returned p < 0.0001, rejecting the null hypothesis of normality
- **Conclusion:** The data is not normally distributed → parametric tests (like a t-test) are inappropriate

**Step 2: Non-parametric hypothesis test**
- Ran a **Mann-Whitney U test** (two-sided) comparing E2E durations between the rework and no-rework cohorts
- Result: U = 38,984,132, p < 0.0001
- **Conclusion:** The difference in E2E durations between cohorts is statistically significant

**Step 3: Effect size**
- Calculated **Rank-Biserial Correlation** (the correct non-parametric effect size for Mann-Whitney U)
- Result: r = −0.83
- **Interpretation:** This is a large effect. The negative sign indicates that the no-rework group consistently has shorter durations.

### 9.3 Why Rank-Biserial Correlation Instead of Cohen's d?
Cohen's d assumes normally distributed data. Since Shapiro-Wilk proved our data is non-normal, reporting Cohen's d would be methodologically inconsistent. Rank-Biserial Correlation is the standard non-parametric effect size paired with Mann-Whitney U.

### 9.4 Results Summary

| Metric | Value |
|---|---|
| Cases with backward rework | 6,886 |
| Cases without backward rework | 6,201 |
| Mean E2E (rework) | 14.33 days |
| Mean E2E (no rework) | 2.27 days |
| Mean difference | ~12 days |
| Mann-Whitney U | 38,984,132 |
| p-value | < 0.0001 |
| Rank-Biserial Correlation | −0.83 (large) |

**Note:** The ~12-day difference is reported as "approximately" because Mann-Whitney U tests distributional shift, not a precise point difference.

---

## 10. Phase 6 — Monte Carlo Simulation & Sensitivity Analysis

**Script:** `src/simulation.py`

### 10.1 Objective
Project the ROI of implementing a "Document Completeness Gate" — a hard checkpoint that prevents any application from entering Underwriting until all documents are verified complete.

### 10.2 Methodology
1. Split all 13,087 cases into two cohorts: "clean" (no backward rework) and "messy" (has backward rework)
2. For each of 100 Monte Carlo iterations:
   - Replace the E2E duration of every messy case with a random draw from the clean case distribution
   - Recalculate the overall average E2E
3. Report the mean projected average and a 95% percentile-based confidence interval
4. Run sensitivity analysis at 50%, 75%, and 100% rework elimination rates

### 10.3 Key Assumption: Exchangeability
The simulation assumes that messy cases would behave **identically** to clean cases if the rework were removed. This is the "exchangeability" assumption. In reality:
- Some Manager Review delay may be genuine queueing or capacity constraints, not document-related
- A document gate may not eliminate 100% of rework
- The sensitivity table below addresses this by modeling partial rework elimination

### 10.4 Results

**Best-case (100% rework eliminated):**

| Metric | Value |
|---|---|
| Current Avg E2E | 8.6 days |
| Projected Avg E2E | 2.3 days (95% CI: [2.2, 2.4]) |
| Days Saved | 6.3 days |
| Cycle Time Reduction | 74% |

**Sensitivity Analysis:**

| Rework Eliminated | Projected Avg E2E | Days Saved | Reduction |
|---|---|---|---|
| 50% (conservative) | 5.4 days | 3.2 days | 37% |
| 75% (moderate) | 3.9 days | 4.8 days | 55% |
| 100% (best case) | 2.3 days | 6.3 days | 74% |

The sensitivity table is more honest than the CI alone. The CI ([2.2, 2.4]) only captures bootstrap sampling variance — it does not capture the uncertainty in the headline assumption. The sensitivity table captures both.

---

## 11. Phase 7 — Predictive Modeling (SLA Breach)

**Script:** `src/predictive_model.py`

### 11.1 Objective
Build an early-warning system that predicts, immediately after the first Document Check event, whether a loan application will breach the 10-day E2E SLA.

### 11.2 Feature Engineering (at Prediction Checkpoint)

| Feature | Description | Knowable at Checkpoint? |
|---|---|---|
| `elapsed_time_days` | Days elapsed from case start to first Document Check | ✅ Yes |
| `events_so_far` | Number of events recorded before the checkpoint | ✅ Yes |
| `is_weekend_submit` | Whether the application was submitted on a weekend | ✅ Yes |

### 11.3 Data Leakage Defense
1. **Temporal cutoff:** All features are computed strictly from events at or before the Document Check timestamp. No future-stage data (Manager Review duration, Underwriting outcome) leaks into features.
2. **Case-level split:** Each row represents exactly one unique `case_id`. A standard `train_test_split` therefore automatically guarantees no intra-case leakage (where events from the same case appear in both train and test sets).
3. **Stratified split:** `stratify=y` ensures the 34% breach base rate is preserved in both train and test sets.

### 11.4 Models Trained

| Model | Class Weight | Scaling |
|---|---|---|
| Logistic Regression | `balanced` | StandardScaler |
| Random Forest (100 trees) | `balanced` | None (tree-based) |

### 11.5 Results (Threshold = 0.5)

| Model | AUC | Precision | Recall |
|---|---|---|---|
| Logistic Regression | 0.54 | 0.64 | 0.17 |
| Random Forest | 0.51 | 0.61 | 0.59 |

### 11.6 Interpretation
Both models perform near chance (AUC ≈ 0.5). This is an **honest negative result** — and reporting it honestly is a strength, not a weakness.

**Why precision appears high despite low AUC:**
- The naive baseline of always predicting "breach" yields ~34% precision (the base rate). Logistic Regression's 0.64 precision is roughly 2× the baseline, showing *some* signal.
- However, the extremely low recall (0.17) means the model catches only 17% of actual breaches — it's too conservative to be operationally useful.

**Why the models struggle:**
- Human-driven queueing delays in Manager Review are inherently unpredictable from the three temporal features available at the Document Check checkpoint
- Richer features (document type, applicant credit score, staff workload) would likely improve performance but are not present in this dataset

---

## 12. Phase 8 — Executive Dashboard

**Script:** `dashboard/app.py`

An interactive multi-tab Streamlit dashboard designed for non-technical stakeholders.

### Dashboard Tabs

| Tab | Visualization Type | What It Shows |
|---|---|---|
| **Timeline** | Plotly Gantt Chart | The journey of a specific loan through every stage, with start/end times |
| **Bottlenecks** | Grouped Bar + SLA Line | Average stage durations vs SLA thresholds; highlights the primary bottleneck |
| **As-Is vs As-Designed** | DFG Image + Metrics | The mined spaghetti process map alongside conformance fitness scores |
| **Rework Loops** | Plotly Sankey Diagram | Visual flow of all stage transitions, including backward loops |
| **SLA Trend** | Plotly Line Chart | Weekly E2E SLA compliance rate over time |
| **What-If Simulation** | Metric Cards + Summary | Current vs projected E2E, days saved, and reduction percentage |

### Technical Notes
- Data is loaded once via `@st.cache_data` decorators for performance
- All metrics are read from `outputs/metrics.json` (pre-computed by the pipeline)
- The dashboard itself does not run any analytics — it is a pure visualization layer

---

## 13. Phase 9 — Executive Memo

**File:** `memo/one_pager.md`

A one-page memo formatted for a VP of Operations audience. It follows the structure:
1. **Headline** — The single most important number (days saved)
2. **The Problem** — Business context and SLA breach rate
3. **Root Cause** — Process mining findings in plain language
4. **Recommendation** — "Shift validation left" (document completeness gate)
5. **Projected Impact** — Sensitivity table with conservative/moderate/best-case scenarios
6. **Caveats** — Explicit disclosure of all assumptions

---

## 14. Assumptions & Limitations

| # | Assumption / Limitation | Impact | Mitigation |
|---|---|---|---|
| 1 | **SLA thresholds are assumed**, not contractual | Breach rate may be higher or lower than 34% | Disclosed in README, memo, and ASSUMPTIONS.md |
| 2 | **Activity mapping is an analytical simplification** | Grouping multiple Dutch codes into one English stage may obscure sub-stage dynamics | Full mapping table published in ASSUMPTIONS.md and README |
| 3 | **Only `COMPLETE` lifecycle events are used** | We miss queueing time between SCHEDULE and START | Disclosed; COMPLETE is standard practice in process mining |
| 4 | **0% conformance is against a rigid strawman** | A more flexible reference model would yield higher conformance | Explicitly acknowledged; fitness score (0.54) provides the continuous measure |
| 5 | **Simulation assumes exchangeability** | Real-world delays may have causes beyond document rework | Sensitivity analysis at 50%/75%/100% provides a range rather than a single point |
| 6 | **ML features are limited to 3 temporal signals** | Model performance is near chance (AUC ≈ 0.5) | Reported honestly as a negative result; stated that richer features would help |
| 7 | **~12 days is a mean difference, not a precise causal estimate** | Mann-Whitney tests distributional shift, not an exact point difference | Reported as "approximately" throughout |
| 8 | **Dataset is from 2011–2012** | Processes may have changed since | Disclosed; methodology remains valid regardless of era |

---

## 15. Tech Stack & Dependencies

| Category | Tool / Library | Version | Purpose |
|---|---|---|---|
| **Language** | Python | 3.x | Core language |
| **Process Mining** | pm4py | Latest | DFG mining, Petri nets, token-based replay |
| **Data Engineering** | pandas, numpy | Latest | DataFrames, numerical computation |
| **Statistics** | scipy | Latest | Shapiro-Wilk, Mann-Whitney U |
| **Machine Learning** | scikit-learn | Latest | LogReg, Random Forest, metrics, scaling |
| **Visualization** | plotly, matplotlib, networkx | Latest | Interactive charts, static DFG |
| **Dashboard** | streamlit | Latest | Web-based interactive dashboard |
| **Storage** | parquet, JSON | — | Processed data and metrics serialization |

---

## 16. Project Structure

```
BA Project/
├── src/
│   ├── ingest.py              # Phase 0: Data download, filtering, stage mapping
│   ├── discovery.py           # Phase 1: DFG mining (frequency + performance)
│   ├── conformance.py         # Phase 2: Petri net + token-based replay
│   ├── cycle_time.py          # Phase 3: Stage durations & SLA analysis
│   ├── rework.py              # Phase 4: Backward rework loop detection
│   ├── stats_tests.py         # Phase 5: Shapiro-Wilk, Mann-Whitney U, effect size
│   ├── simulation.py          # Phase 6: Monte Carlo + sensitivity analysis
│   └── predictive_model.py    # Phase 7: LogReg & Random Forest SLA prediction
├── dashboard/
│   └── app.py                 # Phase 8: Multi-tab Streamlit dashboard
├── memo/
│   └── one_pager.md           # Phase 9: Executive memo for VP audience
├── outputs/
│   ├── metrics.json           # All computed metrics (cumulative, serialized)
│   ├── dfg_data.json          # DFG nodes and edges with frequencies
│   ├── deviations.json        # Top 10 conformance deviation variants
│   └── figures/
│       ├── dfg.png            # Static DFG visualization
│       └── dashboard.png      # Dashboard screenshot (user-provided)
├── data/
│   ├── raw/                   # Original XES event log (.xes.gz)
│   └── processed/             # Cleaned parquet file
├── ASSUMPTIONS.md             # Documented analytical assumptions
└── README.md                  # Project overview and quick-start guide
```

---

## 17. How to Reproduce

### Prerequisites
- Python 3.8+
- Internet connection (for initial dataset download)

### Step 1: Install Dependencies
```bash
pip install pandas numpy scipy scikit-learn plotly streamlit networkx pm4py matplotlib
```

### Step 2: Run the Pipeline (in order)
```bash
python src/ingest.py            # Downloads data, filters, maps stages
python src/discovery.py         # Mines DFG, generates process map
python src/conformance.py       # Runs token-based replay
python src/cycle_time.py        # Calculates stage durations vs SLAs
python src/rework.py            # Detects backward rework loops
python src/stats_tests.py       # Runs statistical tests
python src/simulation.py        # Runs Monte Carlo + sensitivity
python src/predictive_model.py  # Trains ML models
```

### Step 3: Launch the Dashboard
```bash
streamlit run dashboard/app.py
```
Then open `http://localhost:8501` in your browser.

### Step 4: Verify Outputs
All metrics are saved cumulatively to `outputs/metrics.json`. Each script appends its results to this file, so after running all 8 scripts, it contains the complete analytical output.

---

## 18. Academic Citation

van Dongen, B.F. (2012). *BPI Challenge 2012*. Eindhoven University of Technology. Dataset.  
DOI: [10.4121/uuid:3926db30-f712-4394-aebc-75976070e91f](https://doi.org/10.4121/uuid:3926db30-f712-4394-aebc-75976070e91f)

# Loan Approval Process Bottleneck Analysis
*End-to-End Process Mining & Machine Learning Case Study*

## 📖 Project Overview
A major financial institution's personal loan approval process was suffering from unpredictable turnaround times. Leadership lacked visibility into where the delays were actually happening—was it Underwriting, Document Check, or Manager Review? 

Process mining of the raw **BPI Challenge 2012 event log (~164,000 events across 13,087 loan applications)** revealed that the process as it actually runs is chaotic. **0% of cases** conformed to the theoretical textbook happy path. Instead of flowing cleanly from submission to approval, applications were ping-ponging backward in the pipeline due to missing documents.

This project diagnoses the root cause of these delays using **Process Mining**, quantifies the financial impact using **Non-Parametric Statistics**, projects the ROI of a process fix using **Monte Carlo Simulations**, and predicts SLA breaches using **Machine Learning**.

---

## 🚀 Key Findings & Recommendations
1. **The Bottleneck**: **Manager Review** is responsible for 48% of total process delay, but the *root cause* is upstream rework (specifically `Underwriting -> Document Check`).
2. **The Cost of Rework**: True backward rework adds exactly **12 days** to the processing time. (Mann-Whitney U Test p < 0.0001, Rank-Biserial Correlation = -0.83).
3. **The Simulation**: By implementing a hard document completeness gate before Underwriting, the simulation projects the bank will cut average cycle times by **74%**, saving an average of **6.4 days (95% CI: [6.2, 6.4]) per loan application.**

---

## 🧠 Methodology & Technical Architecture

### 1. Data Engineering (`src/ingest.py`)
- **Dataset**: BPI Challenge 2012 (Dutch Financial Institute).
- **Processing**: Filtered 262,200 raw events down to ~164,000 `COMPLETE` lifecycle transitions. Mapped raw Dutch `W_` activity codes to standard English banking stages (e.g., `W_Valideren aanvraag` -> `Document Check`).

### 2. Process Discovery (`src/discovery.py`)
- Used `pm4py` to mine the "as-is" Directly-Follows Graph (DFG) from the raw XES event logs, mapping the exact spaghetti paths cases took.

### 3. Conformance Checking (`src/conformance.py`)
- Measured the mathematical gap between reality and a theoretical "happy path" using Token-Based Replay. 
- Achieved a 0.54 fitness score. While a rigid textbook Petri net is somewhat of a strawman baseline, a 0% case-level conformance rate reveals how radically the process drifted from legacy expectations.

### 4. Cycle Time & Bottleneck Analysis (`src/cycle_time.py` & `src/rework.py`)
- Extracted cycle times for every stage across all cases.
- Identified over 5,000 instances of massive backward rework loops.

### 5. Statistical Validation (`src/stats_tests.py`)
- Checked for normality (Shapiro-Wilk) and utilized the non-parametric Mann-Whitney U test to mathematically prove that rework causes the SLA breaches, computing the Rank-Biserial Correlation effect size.

### 6. Monte Carlo Simulation (`src/simulation.py`)
- Built a bootstrapped statistical simulation to project cycle-time savings. The simulation swapped the durations of "messy" cases with random samples from "clean" cases to model the ROI of fixing the data collection pipeline.

### 7. Predictive Modeling (`src/predictive_model.py`)
- Trained Logistic Regression and Random Forest models to predict SLA breaches. 
- **Leakage Defense**: Established a strict prediction checkpoint *immediately after the first Document Check* to guarantee no data leakage from future events. 
- **Results**: Logistic Regression (AUC=0.54, Precision=0.64, Recall=0.17). Random Forest (AUC=0.51, Precision=0.61, Recall=0.59). The modest AUC highlights the extreme difficulty of predicting human-driven queueing delays using only early temporal features.

---

## 📊 Executive Dashboard
The project includes a multi-tab Streamlit dashboard designed for non-technical operations leadership. It visualizes:
* Case Timelines (Gantt Charts)
* Stage Bottlenecks vs SLAs
* The "As-Is" Process Map
* Rework Loops (Plotly Sankey Diagrams)
* What-If Simulation ROI Panel

![Executive Dashboard](outputs/figures/dashboard.png)
*(Note: Replace with screenshot of `http://localhost:8501`)*

---

## ⚠️ Assumptions & Limitations
* **SLA Benchmarks**: The 10-day End-to-End SLA is an assumed retail lending benchmark used for this case study, not a contractual dataset fact.
* **Simulation Exchangeability**: The Monte Carlo simulation assumes a "Document Gate" would eliminate *all* downstream rework, and that messy cases would otherwise behave exactly like clean cases. In reality, some Manager Review delay is likely due to genuine queueing/capacity constraints, making this a best-case scenario projection.

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

---

## 📚 Academic Citation
Dataset used: van Dongen, B.F. (2012). BPI Challenge 2012. Eindhoven University of Technology. Dataset. https://doi.org/10.4121/uuid:39269302-3220-4c28-a19f-07e112d7c2e3

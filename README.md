# Loan Approval Process Bottleneck Analysis
*A Process Mining & Machine Learning Case Study*

## Situation
A major financial institution's loan approval process was suffering from unpredictable turnaround times. Leadership lacked visibility into where the delays were actually happening—was it Underwriting, Document Check, or Manager Review? The existing "as-designed" process flowcharts didn't match reality, and 33.9% of all cases were breaching a 10-day Service Level Agreement (SLA).

## Complication
Process mining of the raw BPI Challenge 2012 event log (13,087 applications, ~164,000 events) revealed that the process as it actually runs is chaotic. **0% of cases** conformed to the textbook happy path. Instead of flowing cleanly from submission to approval, applications were ping-ponging backward in the pipeline. For example, cases reached Underwriting only to be kicked backward to Document Check over 5,000 times due to missing information. 

## Approach
To diagnose and quantify this issue, I built an end-to-end analytical pipeline:
1. **Process Discovery**: Used `pm4py` to mine the "as-is" Directly-Follows Graph (DFG) and Petri net from the raw XES event logs.
2. **Conformance Checking**: Measured the mathematical gap (0.54 fitness score) between reality and a theoretical "happy path." While a rigid textbook Petri net is somewhat of a strawman baseline, a 0% conformance rate reveals how radically the process has drifted from legacy expectations.
3. **Statistical Validation**: Conducted a Mann-Whitney U test proving that true backward rework adds a massive 12.06 days to the process (Rank-Biserial Correlation = -0.83).
4. **Simulation**: Built a Monte Carlo simulation in Python to project the exact cycle-time savings if the upstream data collection was fixed.
5. **Predictive Modeling**: Trained a Logistic Regression and Random Forest model to predict SLA breaches early in the pipeline based on elapsed time and rework counts.
6. **Executive Dashboard**: Deployed an interactive Streamlit dashboard mapping the exact case timelines, SLA bottlenecks, and simulated what-if scenarios.

## Resolution (The Recommendation)
The data mathematically proves that **Manager Review** is the primary bottleneck, causing 48.1% of total delay, but the *root cause* is upstream rework. 

**By implementing a hard document completeness gate before Underwriting, the simulation projects the bank will cut average cycle times by 73.7%, saving an average of 6.35 days per loan application.**

---

## How to Run This Project Locally

### 1. Install Dependencies
```bash
pip install -r requirements.txt
# Alternatively: pip install pm4py pandas numpy scipy scikit-learn plotly streamlit networkx matplotlib
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
```

### 3. Launch the Executive Dashboard
```bash
streamlit run dashboard/app.py
```
*Navigate to `http://localhost:8501` to view the interactive Gantt charts, Sankey rework loops, and simulation metrics.*

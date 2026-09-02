import os
import json
import pandas as pd
import numpy as np

DATA_FILE = "data/processed/processed_event_log.parquet"
METRICS_FILE = "outputs/metrics.json"

STAGE_ORDER = {
    "Submitted": 0,
    "Document Check": 1,
    "Underwriting": 2,
    "Manager Review": 3,
    "Approved": 4,
    "Rejected": 4,
    "Cancelled": 4,
    "Other": 99
}

def run_simulation():
    print(f"Loading data from {DATA_FILE}...")
    df = pd.read_parquet(DATA_FILE)
    df = df.sort_values(by=['case_id', 'timestamp'])
    
    e2e = df.groupby('case_id')['timestamp'].agg(['min', 'max'])
    e2e['e2e_days'] = (e2e['max'] - e2e['min']).dt.total_seconds() / (24 * 3600)
    
    # Identify cases with backward rework loops
    backward_rework_cases = set()
    case_groups = df.groupby('case_id')
    
    for case_id, group in case_groups:
        stages = group['stage'].tolist()
        for i in range(len(stages) - 1):
            src = stages[i]
            tgt = stages[i+1]
            src_order = STAGE_ORDER.get(src, 99)
            tgt_order = STAGE_ORDER.get(tgt, 99)
            if tgt_order < src_order and src_order != 99 and tgt_order != 99:
                backward_rework_cases.add(case_id)
                break
                
    # Separate the clean vs messy cohorts
    clean_e2e = e2e.loc[~e2e.index.isin(backward_rework_cases)]['e2e_days'].values
    messy_e2e = e2e.loc[e2e.index.isin(backward_rework_cases)]['e2e_days'].values
    
    current_avg = e2e['e2e_days'].mean()
    current_median = e2e['e2e_days'].median()
    
    print(f"Current Avg E2E: {current_avg:.2f} days")
    print(f"Current Median E2E: {current_median:.2f} days")
    
    # ---------------------------------------------------------
    # MONTE CARLO SIMULATION
    # ---------------------------------------------------------
    # Hypothesis: If we fix the upstream document capture process, 
    # we eliminate backward rework loops.
    # We simulate this by taking every messy case and replacing its 
    # duration with a random draw from the clean case distribution.
    
    np.random.seed(42) # For reproducible portfolio results
    n_iterations = 100
    simulated_averages = []
    simulated_medians = []
    
    print("Running Monte Carlo Simulation (100 iterations)...")
    for _ in range(n_iterations):
        # Sample replacements for the messy cases from the clean distribution
        fixed_messy_durations = np.random.choice(clean_e2e, size=len(messy_e2e), replace=True)
        
        # Combine clean cases (which are untouched) with the fixed messy cases
        simulated_scenario = np.concatenate([clean_e2e, fixed_messy_durations])
        
        simulated_averages.append(np.mean(simulated_scenario))
        simulated_medians.append(np.median(simulated_scenario))
        
    projected_avg = np.mean(simulated_averages)
    projected_median = np.mean(simulated_medians)
    
    # 95% Confidence Interval for the simulated average
    ci_lower = np.percentile(simulated_averages, 2.5)
    ci_upper = np.percentile(simulated_averages, 97.5)
    
    days_saved_avg = current_avg - projected_avg
    days_saved_ci_lower = current_avg - ci_upper
    days_saved_ci_upper = current_avg - ci_lower
    
    pct_reduction = (days_saved_avg / current_avg) * 100
    
    print(f"Projected New Avg E2E: {projected_avg:.2f} days (95% CI: [{ci_lower:.2f}, {ci_upper:.2f}])")
    print(f"Projected New Median E2E: {projected_median:.2f} days")
    print(f"Absolute Days Saved per Case: {days_saved_avg:.2f} days (95% CI: [{days_saved_ci_lower:.2f}, {days_saved_ci_upper:.2f}])")
    print(f"Relative Cycle Time Reduction: {pct_reduction:.1f}%")
    
    # Save Metrics
    output_metrics = {
        "simulation": {
            "current_avg_days": float(current_avg),
            "projected_avg_days": float(projected_avg),
            "projected_avg_ci_lower": float(ci_lower),
            "projected_avg_ci_upper": float(ci_upper),
            "absolute_days_saved_per_case": float(days_saved_avg),
            "days_saved_ci_lower": float(days_saved_ci_lower),
            "days_saved_ci_upper": float(days_saved_ci_upper),
            "pct_reduction": float(pct_reduction)
        }
    }
    
    if not os.path.exists("outputs"):
        os.makedirs("outputs")
        
    if os.path.exists(METRICS_FILE):
        try:
            with open(METRICS_FILE, "r") as f:
                existing = json.load(f)
            existing.update(output_metrics)
            output_metrics = existing
        except:
            pass
            
    with open(METRICS_FILE, "w") as f:
        json.dump(output_metrics, f, indent=4)
        
    print(f"Simulation metrics saved to {METRICS_FILE}")

if __name__ == "__main__":
    run_simulation()

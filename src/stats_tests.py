import os
import json
import pandas as pd
import numpy as np
from scipy import stats

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

def rank_biserial_correlation(u_stat, n1, n2):
    """Calculate Rank-Biserial Correlation for effect size (non-parametric)."""
    return 1 - (2 * u_stat) / (n1 * n2)

def run_stats():
    print(f"Loading data from {DATA_FILE}...")
    df = pd.read_parquet(DATA_FILE)
    df = df.sort_values(by=['case_id', 'timestamp'])
    
    e2e = df.groupby('case_id')['timestamp'].agg(['min', 'max'])
    e2e['e2e_days'] = (e2e['max'] - e2e['min']).dt.total_seconds() / (24 * 3600)
    
    backward_rework_cases = set()
    
    case_groups = df.groupby('case_id')
    
    for case_id, group in case_groups:
        stages = group['stage'].tolist()
        
        # Check for STRICTLY backward transitions (target < source)
        for i in range(len(stages) - 1):
            src = stages[i]
            tgt = stages[i+1]
            
            src_order = STAGE_ORDER.get(src, 99)
            tgt_order = STAGE_ORDER.get(tgt, 99)
            
            if tgt_order < src_order and src_order != 99 and tgt_order != 99:
                backward_rework_cases.add(case_id)
                break # Case is marked as having backward rework, no need to check further
                
    group_rework = e2e.loc[e2e.index.isin(backward_rework_cases)]['e2e_days'].values
    group_no_rework = e2e.loc[~e2e.index.isin(backward_rework_cases)]['e2e_days'].values
    
    print(f"Cases with True Backward Rework: {len(group_rework)}")
    print(f"Cases without Backward Rework: {len(group_no_rework)}")
    
    # Check normality using Shapiro-Wilk on a sample (Shapiro is sensitive >5000 N)
    # So we'll sample 1000 from each to check normality
    try:
        sample_rework = np.random.choice(group_rework, size=min(1000, len(group_rework)), replace=False)
        sample_no_rework = np.random.choice(group_no_rework, size=min(1000, len(group_no_rework)), replace=False)
        _, p_norm_rw = stats.shapiro(sample_rework)
        _, p_norm_no = stats.shapiro(sample_no_rework)
        print(f"Normality check (p-value): Rework={p_norm_rw:.4f}, No_Rework={p_norm_no:.4f}")
        # Both will likely be < 0.05, meaning they are NOT normally distributed.
    except Exception as e:
        print(f"Could not compute shapiro: {e}")
        
    # Mann-Whitney U test (non-parametric)
    print("Running Mann-Whitney U Test...")
    u_stat, p_value = stats.mannwhitneyu(group_rework, group_no_rework, alternative='two-sided')
    
    # Effect Size (Non-parametric)
    effect_size = rank_biserial_correlation(u_stat, len(group_rework), len(group_no_rework))
    
    mean_rw = np.mean(group_rework)
    mean_no = np.mean(group_no_rework)
    diff_days = mean_rw - mean_no
    
    print(f"Mean E2E (Rework): {mean_rw:.2f} days")
    print(f"Mean E2E (No Rework): {mean_no:.2f} days")
    print(f"Mean Difference: {diff_days:.2f} days")
    print(f"Mann-Whitney U statistic: {u_stat:.2f}")
    print(f"p-value: {p_value:.4e}")
    print(f"Rank-Biserial Correlation: {effect_size:.4f}")
    
    # Save Metrics
    output_metrics = {
        "stats": {
            "cases_rework": len(group_rework),
            "cases_no_rework": len(group_no_rework),
            "mean_rework_days": float(mean_rw),
            "mean_no_rework_days": float(mean_no),
            "mean_difference_days": float(diff_days),
            "p_value": float(p_value),
            "rank_biserial_correlation": float(effect_size),
            "is_statistically_significant": bool(p_value < 0.05)
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
        
    print(f"Statistical validation metrics saved to {METRICS_FILE}")

if __name__ == "__main__":
    run_stats()

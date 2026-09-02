import os
import json
import pandas as pd
import numpy as np
from collections import Counter

DATA_FILE = "data/processed/processed_event_log.parquet"
METRICS_FILE = "outputs/metrics.json"

# Define ideal flow order to identify backward transitions
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

def analyze_rework():
    print(f"Loading data from {DATA_FILE}...")
    df = pd.read_parquet(DATA_FILE)
    df = df.sort_values(by=['case_id', 'timestamp'])
    
    # Calculate E2E durations
    e2e = df.groupby('case_id')['timestamp'].agg(['min', 'max'])
    e2e['e2e_days'] = (e2e['max'] - e2e['min']).dt.total_seconds() / (24 * 3600)
    
    rework_cases = set()
    loop_pairs = []
    
    case_groups = df.groupby('case_id')
    
    for case_id, group in case_groups:
        stages = group['stage'].tolist()
        
        # Check if any stage appears more than once
        if len(set(stages)) < len(stages):
            rework_cases.add(case_id)
            
        # Check for backward or self-loop transitions
        for i in range(len(stages) - 1):
            src = stages[i]
            tgt = stages[i+1]
            
            src_order = STAGE_ORDER.get(src, 99)
            tgt_order = STAGE_ORDER.get(tgt, 99)
            
            # If target is before or equal to source in the flow, it's a rework loop
            if tgt_order <= src_order and src_order != 99 and tgt_order != 99:
                loop_pairs.append(f"{src} -> {tgt}")
                
    total_cases = df['case_id'].nunique()
    rework_rate_pct = (len(rework_cases) / total_cases) * 100
    
    # Calculate added cycle time
    e2e_rework = e2e.loc[e2e.index.isin(rework_cases)]['e2e_days'].mean()
    e2e_no_rework = e2e.loc[~e2e.index.isin(rework_cases)]['e2e_days'].mean()
    
    added_cycle_time_days = e2e_rework - e2e_no_rework if pd.notna(e2e_rework) and pd.notna(e2e_no_rework) else 0
    
    # Most common looping stage pairs
    pair_counts = Counter(loop_pairs)
    top_loop_pairs = [{"pair": k, "count": v} for k, v in pair_counts.most_common(5)]
    
    print(f"Total Cases: {total_cases}")
    print(f"Cases with Rework: {len(rework_cases)} ({rework_rate_pct:.1f}%)")
    print(f"Avg E2E without rework: {e2e_no_rework:.2f} days")
    print(f"Avg E2E with rework: {e2e_rework:.2f} days")
    print(f"Added cycle time per reworked case: {added_cycle_time_days:.2f} days")
    print("Top Rework Loops:")
    for p in top_loop_pairs:
        print(f"  {p['pair']}: {p['count']} occurrences")
        
    # Save Metrics
    output_metrics = {
        "rework": {
            "rework_rate_pct": float(rework_rate_pct),
            "added_cycle_time_days": float(added_cycle_time_days),
            "e2e_no_rework_days": float(e2e_no_rework),
            "e2e_rework_days": float(e2e_rework),
            "top_loop_pairs": top_loop_pairs
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
        
    print(f"Rework metrics saved to {METRICS_FILE}")

if __name__ == "__main__":
    analyze_rework()

import os
import json
import pandas as pd
import numpy as np

DATA_FILE = "data/processed/processed_event_log.parquet"
METRICS_FILE = "outputs/metrics.json"

# SLA Thresholds (in days)
SLA_THRESHOLDS = {
    "Document Check": 2.0,
    "Underwriting": 3.0,
    "Manager Review": 1.0,
    "End-to-End": 10.0
}

def compute_cycle_times():
    print(f"Loading data from {DATA_FILE}...")
    df = pd.read_parquet(DATA_FILE)
    
    # Sort by case and time to ensure sequential order
    df = df.sort_values(by=['case_id', 'timestamp'])
    
    # Calculate time since previous event in the same case
    # This represents the duration (processing + wait time) for the current event
    df['prev_timestamp'] = df.groupby('case_id')['timestamp'].shift(1)
    df['duration_sec'] = (df['timestamp'] - df['prev_timestamp']).dt.total_seconds()
    
    # For the very first event in a case, duration is technically 0, so fillna(0)
    df['duration_sec'] = df['duration_sec'].fillna(0)
    df['duration_days'] = df['duration_sec'] / (24 * 3600)
    
    # Aggregate stage duration per case
    # If a case hits Document Check 3 times, this sums the duration of all 3 hits
    stage_durations = df.groupby(['case_id', 'stage'])['duration_days'].sum().reset_index()
    
    # End-to-end duration per case
    case_e2e = df.groupby('case_id')['timestamp'].agg(['min', 'max'])
    case_e2e['e2e_duration_days'] = (case_e2e['max'] - case_e2e['min']).dt.total_seconds() / (24 * 3600)
    case_e2e = case_e2e.reset_index()
    
    # Calculate E2E metrics
    e2e_mean = case_e2e['e2e_duration_days'].mean()
    e2e_median = case_e2e['e2e_duration_days'].median()
    e2e_p90 = np.percentile(case_e2e['e2e_duration_days'], 90)
    e2e_breach_pct = (case_e2e['e2e_duration_days'] > SLA_THRESHOLDS["End-to-End"]).mean() * 100
    
    # Calculate total absolute time spent in all cases to find the % share
    total_e2e_time = case_e2e['e2e_duration_days'].sum()
    
    # Compute per-stage metrics across cases that actually hit that stage
    stage_metrics = {}
    
    for stage in ["Document Check", "Underwriting", "Manager Review"]:
        stage_df = stage_durations[stage_durations['stage'] == stage]
        
        if len(stage_df) == 0:
            continue
            
        mean_dur = stage_df['duration_days'].mean()
        med_dur = stage_df['duration_days'].median()
        p90_dur = np.percentile(stage_df['duration_days'], 90)
        
        sla = SLA_THRESHOLDS[stage]
        breach_pct = (stage_df['duration_days'] > sla).mean() * 100
        
        total_stage_time = stage_df['duration_days'].sum()
        share_of_total = (total_stage_time / total_e2e_time) * 100 if total_e2e_time > 0 else 0
        
        stage_metrics[stage] = {
            "mean_days": float(mean_dur),
            "median_days": float(med_dur),
            "p90_days": float(p90_dur),
            "sla_breach_pct": float(breach_pct),
            "share_of_total_delay_pct": float(share_of_total)
        }
        
    # Identify the primary bottleneck (stage with highest share of total delay)
    bottleneck_stage = max(stage_metrics.keys(), key=lambda k: stage_metrics[k]["share_of_total_delay_pct"])
    bottleneck_share = stage_metrics[bottleneck_stage]["share_of_total_delay_pct"]
    
    print(f"E2E Mean: {e2e_mean:.2f} days | E2E Breach: {e2e_breach_pct:.1f}%")
    for stage, metrics in stage_metrics.items():
        print(f"{stage}: {metrics['mean_days']:.2f} avg days | {metrics['share_of_total_delay_pct']:.1f}% of total delay")
        
    print(f"--> BOTTLENECK: {bottleneck_stage} causes {bottleneck_share:.1f}% of total delay")
    
    # Save Metrics
    output_metrics = {
        "cycle_time": {
            "e2e_mean_days": float(e2e_mean),
            "e2e_median_days": float(e2e_median),
            "e2e_p90_days": float(e2e_p90),
            "e2e_sla_breach_pct": float(e2e_breach_pct),
            "stages": stage_metrics,
            "headline_bottleneck": {
                "stage": bottleneck_stage,
                "share_of_delay_pct": float(bottleneck_share)
            }
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
        
    print(f"Cycle time metrics saved to {METRICS_FILE}")

if __name__ == "__main__":
    compute_cycle_times()

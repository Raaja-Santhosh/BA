import os
import json
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import roc_auc_score, precision_score, recall_score
from sklearn.preprocessing import StandardScaler

DATA_FILE = "data/processed/processed_event_log.parquet"
METRICS_FILE = "outputs/metrics.json"
SLA_DAYS = 10.0

def run_predictive_model():
    print(f"Loading data from {DATA_FILE}...")
    df = pd.read_parquet(DATA_FILE)
    df = df.sort_values(by=['case_id', 'timestamp'])
    
    # Target: E2E SLA Breach
    e2e = df.groupby('case_id')['timestamp'].agg(['min', 'max'])
    e2e['e2e_days'] = (e2e['max'] - e2e['min']).dt.total_seconds() / (24 * 3600)
    e2e['is_breached'] = (e2e['e2e_days'] > SLA_DAYS).astype(int)
    
    # Checkpoint Feature Engineering: State immediately after first 'Document Check'
    # 1. Find the first event of each case to get the start time
    first_events = df.groupby('case_id').first().reset_index()
    first_events = first_events[['case_id', 'timestamp']].rename(columns={'timestamp': 'start_time'})
    
    # 2. Add an event index (to count events_so_far)
    df['event_rank'] = df.groupby('case_id').cumcount() + 1
    
    # 3. Find the checkpoint event (first Document Check)
    doc_checks = df[df['stage'] == 'Document Check'].groupby('case_id').first().reset_index()
    
    # Merge checkpoint data with start time and target
    model_df = doc_checks[['case_id', 'timestamp', 'event_rank']].merge(first_events, on='case_id')
    model_df = model_df.merge(e2e[['is_breached']], left_on='case_id', right_index=True)
    
    # Feature 1: Elapsed time so far (in days)
    model_df['elapsed_time_days'] = (model_df['timestamp'] - model_df['start_time']).dt.total_seconds() / (24 * 3600)
    
    # Feature 2: Events so far (Rework indicator prior to doc check)
    model_df['events_so_far'] = model_df['event_rank']
    
    # Feature 3: Submission Day of Week (0=Monday, 6=Sunday)
    model_df['submit_dow'] = model_df['start_time'].dt.dayofweek
    model_df['is_weekend_submit'] = model_df['submit_dow'].isin([5, 6]).astype(int)
    
    features = ['elapsed_time_days', 'events_so_far', 'is_weekend_submit']
    X = model_df[features]
    y = model_df['is_breached']
    
    print(f"Dataset ready. Cases reaching checkpoint: {len(model_df)}")
    
    # --- DATA LEAKAGE DEFENSE ---
    # 1. Feature temporal safety: We strictly cut off feature generation at the exact 
    #    timestamp of the first 'Document Check'. No future events are leaked into features.
    # 2. Independence: Because we aggregated the dataset so that each row represents 
    #    exactly one unique case_id, a standard train/test split automatically splits 
    #    by case. This guarantees no intra-case leakage (where events from the same case 
    #    end up in both train and test sets).
    
    # Train-test split (stratified by target to handle the 33.9% class imbalance)
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)
    
    # Scale features
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)
    
    # Train Logistic Regression (Baseline + Interpretable)
    lr_model = LogisticRegression(random_state=42, class_weight='balanced')
    lr_model.fit(X_train_scaled, y_train)
    
    lr_preds = lr_model.predict(X_test_scaled)
    lr_probs = lr_model.predict_proba(X_test_scaled)[:, 1]
    
    lr_auc = roc_auc_score(y_test, lr_probs)
    lr_prec = precision_score(y_test, lr_preds)
    lr_rec = recall_score(y_test, lr_preds)
    
    # Train Random Forest (Ceiling)
    rf_model = RandomForestClassifier(random_state=42, n_estimators=100, class_weight='balanced')
    rf_model.fit(X_train, y_train) # RF doesn't need scaling
    
    rf_preds = rf_model.predict(X_test)
    rf_probs = rf_model.predict_proba(X_test)[:, 1]
    
    rf_auc = roc_auc_score(y_test, rf_probs)
    rf_prec = precision_score(y_test, rf_preds)
    rf_rec = recall_score(y_test, rf_preds)
    
    print(f"Logistic Regression - AUC: {lr_auc:.3f}, Precision: {lr_prec:.3f}, Recall: {lr_rec:.3f}")
    print(f"Random Forest - AUC: {rf_auc:.3f}, Precision: {rf_prec:.3f}, Recall: {rf_rec:.3f}")
    
    # Business interpretation of LogReg coefficients
    # The coefficients represent the change in log odds. 
    # An odds ratio > 1 means the feature increases probability of breach.
    odds_ratios = np.exp(lr_model.coef_[0])
    
    feature_importance_biz = []
    for i, feature in enumerate(features):
        feature_importance_biz.append({
            "feature": feature,
            "odds_ratio": float(odds_ratios[i]),
            "interpretation": f"For every 1 standard deviation increase in {feature}, the odds of breaching the SLA are multiplied by {odds_ratios[i]:.2f}."
        })
        print(feature_importance_biz[-1]['interpretation'])
        
    # Save Metrics
    output_metrics = {
        "predictive_model": {
            "checkpoint": "Immediately after first Document Check",
            "cases_evaluated": len(model_df),
            "logreg": {
                "auc": float(lr_auc),
                "precision": float(lr_prec),
                "recall": float(lr_rec)
            },
            "random_forest": {
                "auc": float(rf_auc),
                "precision": float(rf_prec),
                "recall": float(rf_rec)
            },
            "business_feature_importance": feature_importance_biz
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
        
    print(f"Predictive model metrics saved to {METRICS_FILE}")

if __name__ == "__main__":
    run_predictive_model()

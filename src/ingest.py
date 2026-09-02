import os
import json
import urllib.request
import pandas as pd
import pm4py

DATA_RAW_DIR = "data/raw"
DATA_PROCESSED_DIR = "data/processed"
METRICS_FILE = "outputs/metrics.json"

# BPI Challenge 2012 Dataset
# Download URL from Figshare API
BPI_2012_URL = "https://ndownloader.figshare.com/files/24027287"
RAW_FILE_PATH = os.path.join(DATA_RAW_DIR, "BPI_Challenge_2012.xes.gz")
UNZIPPED_FILE_PATH = os.path.join(DATA_RAW_DIR, "BPI_Challenge_2012.xes")

def download_data():
    if not os.path.exists(DATA_RAW_DIR):
        os.makedirs(DATA_RAW_DIR)
        
    if not os.path.exists(RAW_FILE_PATH) and not os.path.exists(UNZIPPED_FILE_PATH):
        print(f"Downloading BPI Challenge 2012 from {BPI_2012_URL}...")
        try:
            req = urllib.request.Request(BPI_2012_URL, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req) as response, open(RAW_FILE_PATH, 'wb') as out_file:
                out_file.write(response.read())
            print("Download complete.")
        except Exception as e:
            print(f"Failed to download automatically: {e}")
            print("Please download manually from https://data.4tu.nl/articles/dataset/BPI_Challenge_2012/12689204")
            print(f"and place the file at {RAW_FILE_PATH}")
            raise

    return RAW_FILE_PATH if os.path.exists(RAW_FILE_PATH) else UNZIPPED_FILE_PATH

def map_stage(activity):
    """
    Map raw activities onto the business-friendly stage language.
    """
    act = str(activity).strip()
    
    # Submitted
    if act in ["A_SUBMITTED", "A_PARTLYSUBMITTED"]:
        return "Submitted"
    # Document Check
    elif act in ["A_PREACCEPTED", "W_Completeren aanvraag"]:
        return "Document Check"
    # Underwriting
    elif act in ["A_ACCEPTED", "A_FINALIZED", "O_CREATED", "O_SENT"]:
        return "Underwriting"
    # Manager Review / Activation
    elif act in ["W_Nabellen offertes", "A_APPROVED", "A_REGISTERED", "A_ACTIVATED"]:
        return "Manager Review"
    # Outcomes
    elif act in ["A_DECLINED"]:
        return "Rejected"
    elif act in ["A_CANCELLED", "O_CANCELLED"]:
        return "Cancelled"
    else:
        return "Other"

def ingest_and_clean():
    file_path = download_data()
    print(f"Reading event log from {file_path}...")
    
    log = pm4py.read_xes(file_path)
    df = pm4py.convert_to_dataframe(log)
    
    initial_cases = df['case:concept:name'].nunique()
    initial_events = len(df)
    
    print("Filtering lifecycle and standardizing columns...")
    col_mapping = {
        'case:concept:name': 'case_id',
        'concept:name': 'activity',
        'time:timestamp': 'timestamp',
        'lifecycle:transition': 'lifecycle',
        'org:resource': 'resource'
    }
    
    rename_dict = {k: v for k, v in col_mapping.items() if k in df.columns}
    df = df.rename(columns=rename_dict)
    
    for col in ['case_id', 'activity', 'timestamp', 'lifecycle', 'resource']:
        if col not in df.columns:
            if col == 'lifecycle':
                df['lifecycle'] = 'COMPLETE' # Fallback
            else:
                df[col] = 'UNKNOWN'
                
    # Filter to COMPLETE lifecycle events
    df['lifecycle'] = df['lifecycle'].astype(str).str.upper()
    df = df[df['lifecycle'] == 'COMPLETE'].copy()
    
    # Map stages
    df['stage'] = df['activity'].apply(map_stage)
    
    # Clean: dedupe, sort by case then timestamp
    df = df.sort_values(by=['case_id', 'timestamp'])
    df = df.drop_duplicates(subset=['case_id', 'activity', 'timestamp'])
    
    # Optional: we might drop "Other" stages to only keep the main flow, 
    # but let's keep them for completeness and filter in cycle time logic if needed.
    
    final_cases = df['case_id'].nunique()
    final_events = len(df)
    
    dropped_cases_pct = (initial_cases - final_cases) / initial_cases * 100 if initial_cases > 0 else 0
    dropped_events_pct = (initial_events - final_events) / initial_events * 100 if initial_events > 0 else 0
    
    print("Data quality summary:")
    print(f"  Initial cases: {initial_cases}, Final cases: {final_cases} ({dropped_cases_pct:.1f}% dropped)")
    print(f"  Initial events: {initial_events}, Final events: {final_events} ({dropped_events_pct:.1f}% dropped)")
    
    if not os.path.exists(DATA_PROCESSED_DIR):
        os.makedirs(DATA_PROCESSED_DIR)
        
    out_path = os.path.join(DATA_PROCESSED_DIR, "processed_event_log.parquet")
    df['timestamp'] = pd.to_datetime(df['timestamp'], utc=True)
    df.to_parquet(out_path, index=False)
    print(f"Saved processed event log to {out_path}")
    
    if not os.path.exists("outputs"):
        os.makedirs("outputs")
        
    metrics = {
        "data_quality": {
            "initial_cases": int(initial_cases),
            "final_cases": int(final_cases),
            "initial_events": int(initial_events),
            "final_events": int(final_events),
            "dropped_cases_pct": float(dropped_cases_pct),
            "dropped_events_pct": float(dropped_events_pct),
            "date_range_start": str(df['timestamp'].min()),
            "date_range_end": str(df['timestamp'].max())
        }
    }
    
    if os.path.exists(METRICS_FILE):
        try:
            with open(METRICS_FILE, "r") as f:
                existing_metrics = json.load(f)
            existing_metrics.update(metrics)
            metrics = existing_metrics
        except:
            pass
            
    with open(METRICS_FILE, "w") as f:
        json.dump(metrics, f, indent=4)

if __name__ == "__main__":
    ingest_and_clean()

import os
import json
import pandas as pd
import pm4py
import networkx as nx
import matplotlib.pyplot as plt
import plotly.graph_objects as go
from pm4py.objects.log.util import dataframe_utils
from pm4py.util import constants

DATA_FILE = "data/processed/processed_event_log.parquet"
OUTPUT_DIR = "outputs/figures"
METRICS_FILE = "outputs/metrics.json"
DFG_DATA_FILE = "outputs/dfg_data.json"

def format_duration(seconds):
    """Format seconds into a human-readable duration."""
    days = seconds // (24 * 3600)
    hours = (seconds % (24 * 3600)) // 3600
    if days > 0:
        return f"{int(days)}d {int(hours)}h"
    else:
        return f"{int(hours)}h"

def run_discovery():
    print(f"Loading data from {DATA_FILE}...")
    df = pd.read_parquet(DATA_FILE)
    
    # Map stages natively as activities
    df = pm4py.format_dataframe(df, case_id='case_id', activity_key='stage', timestamp_key='timestamp')
    
    print("Discovering Frequency DFG...")
    freq_dfg, start_activities, end_activities = pm4py.discover_dfg(df)
    
    print("Discovering Performance DFG...")
    perf_dfg, start_perf, end_perf = pm4py.discover_performance_dfg(df)
    
    total_cases = df['case_id'].nunique()
    threshold = total_cases * 0.01  # 1% threshold
    max_freq = max(freq_dfg.values()) if freq_dfg else 1
    
    # Prepare combined data for JSON (for Streamlit / Plotly)
    nodes_data = set()
    edges_data = []
    
    for (src, tgt) in freq_dfg.keys():
        nodes_data.add(src)
        nodes_data.add(tgt)
        
    for (src, tgt), freq in freq_dfg.items():
        if freq < threshold:
            continue
            
        perf_data = perf_dfg.get((src, tgt), {})
        mean_sec = perf_data.get('mean', 0)
        edges_data.append({
            "source": src,
            "target": tgt,
            "frequency": int(freq),
            "mean_duration_sec": float(mean_sec),
            "label": f"{freq} cases\\n{format_duration(mean_sec)}"
        })
        
    dfg_export = {
        "nodes": list(nodes_data),
        "edges": edges_data,
        "start_activities": list(start_activities.keys()),
        "end_activities": list(end_activities.keys())
    }
    
    if not os.path.exists("outputs"):
        os.makedirs("outputs")
    with open(DFG_DATA_FILE, "w") as f:
        json.dump(dfg_export, f, indent=4)
        
    print(f"Saved DFG data to {DFG_DATA_FILE}")

    # Generate Static PNG with NetworkX
    print("Generating static DFG image with NetworkX...")
    G = nx.DiGraph()
    for n in dfg_export["nodes"]:
        G.add_node(n)
    for e in edges_data:
        G.add_edge(e["source"], e["target"], weight=e["frequency"], label=e["label"])
        
    plt.figure(figsize=(12, 8))
    pos = nx.spring_layout(G, seed=42)
    
    # Draw nodes
    node_colors = []
    for n in G.nodes():
        if n in start_activities:
            node_colors.append('#C5E1A5')
        elif n in end_activities:
            node_colors.append('#FFCC80')
        else:
            node_colors.append('#EAEAEA')
            
    nx.draw_networkx_nodes(G, pos, node_color=node_colors, node_size=3000, edgecolors='black')
    nx.draw_networkx_labels(G, pos, font_size=10, font_weight="bold")
    
    # Draw edges
    edges = G.edges()
    weights = [G[u][v]['weight'] for u,v in edges]
    max_w = max(weights) if weights else 1
    widths = [max(1.0, 5.0 * (w / max_w)) for w in weights]
    
    nx.draw_networkx_edges(G, pos, width=widths, arrowsize=20, node_size=3000, connectionstyle='arc3,rad=0.1')
    edge_labels = {(u, v): G[u][v]['label'] for u, v in G.edges()}
    nx.draw_networkx_edge_labels(G, pos, edge_labels=edge_labels, font_size=8, label_pos=0.3)
    
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
    plt.title("As-Is Process Directly-Follows Graph (DFG)")
    plt.axis('off')
    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, "dfg.png"), dpi=300)
    plt.close()
    
    # Inductive Miner & Heuristics Miner execution
    print("Running Inductive Miner...")
    net, im, fm = pm4py.discover_petri_net_inductive(df)
    
    print("Running Heuristics Miner...")
    heuristics_net = pm4py.discover_heuristics_net(df)
    
    metrics = {
        "discovery": {
            "num_places_in_inductive_net": len(net.places),
            "num_transitions_in_inductive_net": len(net.transitions),
            "num_arcs_in_inductive_net": len(net.arcs),
            "edges_in_dfg_above_threshold": len(edges_data),
            "total_dfg_edges_raw": len(freq_dfg)
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
        
    print("Phase 2 discovery complete.")

if __name__ == "__main__":
    run_discovery()

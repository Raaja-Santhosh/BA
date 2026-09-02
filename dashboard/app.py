import os
import json
import pandas as pd
import numpy as np
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go

# --- CONFIGURATION ---
st.set_page_config(page_title="Loan Process Bottleneck Analysis", layout="wide")

DATA_FILE = "data/processed/processed_event_log.parquet"
METRICS_FILE = "outputs/metrics.json"
DFG_FILE = "outputs/dfg_data.json"
DFG_IMAGE = "outputs/figures/dfg.png"

# --- DATA LOADING ---
@st.cache_data
def load_data():
    if os.path.exists(DATA_FILE):
        return pd.read_parquet(DATA_FILE)
    return pd.DataFrame()

@st.cache_data
def load_metrics():
    if os.path.exists(METRICS_FILE):
        with open(METRICS_FILE, "r") as f:
            return json.load(f)
    return {}

@st.cache_data
def load_dfg():
    if os.path.exists(DFG_FILE):
        with open(DFG_FILE, "r") as f:
            return json.load(f)
    return {}

df = load_data()
metrics = load_metrics()
dfg_data = load_dfg()

# SLAs
SLA_THRESHOLDS = {
    "Document Check": 2.0,
    "Underwriting": 3.0,
    "Manager Review": 1.0,
    "End-to-End": 10.0
}

# --- HEADER ---
st.title("Loan Approval Process Bottleneck Analysis")
st.markdown("""
**Objective:** Discover the actual "as-is" loan approval process, quantify bottlenecks against SLA thresholds, and simulate process fixes.
""")

if df.empty:
    st.error("No event log data found. Please run the ingestion scripts first.")
    st.stop()

# --- TABS ---
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "Timeline", 
    "Bottlenecks", 
    "As-Is vs As-Designed", 
    "Rework Loops", 
    "SLA Trend",
    "What-If Simulation"
])

# 1. CASE TIMELINE
with tab1:
    st.header("Case Timeline")
    st.markdown("Select a specific case to see its journey through the process.")
    
    sample_cases = df['case_id'].unique()[:100] # Provide top 100 cases to avoid huge dropdown
    selected_case = st.selectbox("Select Case ID", sample_cases)
    
    if selected_case:
        case_df = df[df['case_id'] == selected_case].copy()
        # For Gantt chart, we need a start and end time. We will assume each event takes until the next event starts.
        case_df['start_time'] = case_df['timestamp']
        case_df['end_time'] = case_df['timestamp'].shift(-1).fillna(case_df['timestamp'] + pd.Timedelta(hours=1))
        
        fig = px.timeline(
            case_df, 
            x_start="start_time", 
            x_end="end_time", 
            y="stage", 
            color="stage",
            title=f"Journey for Case {selected_case}"
        )
        fig.update_yaxes(autorange="reversed")
        st.plotly_chart(fig, width='stretch')

# 2. STAGE BOTTLENECKS
with tab2:
    st.header("Stage Bottlenecks vs SLAs")
    if "cycle_time" in metrics:
        ct_metrics = metrics["cycle_time"]["stages"]
        
        # Prepare data for plotting
        stages = []
        means = []
        slas = []
        shares = []
        
        for stage, stats in ct_metrics.items():
            stages.append(stage)
            means.append(stats["mean_days"])
            slas.append(SLA_THRESHOLDS.get(stage, 0))
            shares.append(stats["share_of_total_delay_pct"])
            
        bottleneck_df = pd.DataFrame({
            "Stage": stages,
            "Avg Days": means,
            "SLA Threshold": slas,
            "% of Total Delay": shares
        })
        
        fig2 = go.Figure()
        fig2.add_trace(go.Bar(
            name="Avg Cycle Time (Days)",
            x=bottleneck_df["Stage"],
            y=bottleneck_df["Avg Days"],
            marker_color='indianred'
        ))
        fig2.add_trace(go.Scatter(
            name="SLA Threshold",
            x=bottleneck_df["Stage"],
            y=bottleneck_df["SLA Threshold"],
            mode="lines+markers",
            line=dict(color='black', dash='dash', width=3)
        ))
        fig2.update_layout(title="Average Stage Duration vs SLA")
        st.plotly_chart(fig2, width='stretch')
        
        st.markdown(f"### The primary bottleneck is **{metrics['cycle_time']['headline_bottleneck']['stage']}** "
                    f"causing **{metrics['cycle_time']['headline_bottleneck']['share_of_delay_pct']:.1f}%** of total delay.")

# 3. AS-DESIGNED VS AS-IS
with tab3:
    st.header("Conformance Checking: As-Designed vs As-Is")
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.subheader("Metrics")
        if "conformance" in metrics:
            conf = metrics["conformance"]
            st.metric("Overall Fitness Score", f"{conf['overall_fitness_score']:.2f}")
            st.metric("Perfectly Conformant Cases", f"{conf['perfectly_conformant_cases']} ({conf['perfectly_conformant_pct']:.2f}%)")
            st.markdown("""
            **Deviation Note:**
            0% of cases follow the textbook linear happy path due to intense rework loops.
            """)
            
    with col2:
        st.subheader("As-Is Directly-Follows Graph")
        if os.path.exists(DFG_IMAGE):
            st.image(DFG_IMAGE, caption="Mined Process DFG (Red edges indicate severe delay)")
        else:
            st.info("Static DFG image not found. Please ensure Phase 2 completes successfully.")

# 4. REWORK LOOPS
with tab4:
    st.header("Rework Loop Sankey Diagram")
    
    if dfg_data:
        edges = dfg_data.get("edges", [])
        nodes = dfg_data.get("nodes", [])
        
        # Map node names to integers for Plotly Sankey
        node_map = {name: i for i, name in enumerate(nodes)}
        
        sources = []
        targets = []
        values = []
        
        for e in edges:
            sources.append(node_map[e["source"]])
            targets.append(node_map[e["target"]])
            values.append(e["frequency"])
            
        fig4 = go.Figure(data=[go.Sankey(
            node=dict(
                pad=15,
                thickness=20,
                line=dict(color="black", width=0.5),
                label=nodes,
                color="blue"
            ),
            link=dict(
                source=sources,
                target=targets,
                value=values
            )
        )])
        fig4.update_layout(title_text="Transition Frequencies (Including Back-Loops)", font_size=10)
        st.plotly_chart(fig4, width='stretch')
        
        if "rework" in metrics:
            st.markdown("### Top Rework Friction Points")
            for p in metrics["rework"]["top_loop_pairs"]:
                st.write(f"- {p['pair']}: {p['count']} times")

# 5. SLA COMPLIANCE TREND
with tab5:
    st.header("SLA Compliance Trend Over Time")
    # Group by week and calculate E2E breach %
    e2e = df.groupby('case_id').agg(
        start_time=('timestamp', 'min'),
        end_time=('timestamp', 'max')
    ).reset_index()
    
    e2e['e2e_days'] = (e2e['end_time'] - e2e['start_time']).dt.total_seconds() / (24 * 3600)
    e2e['is_breach'] = e2e['e2e_days'] > SLA_THRESHOLDS["End-to-End"]
    
    # Resample by week based on start_time
    e2e = e2e.set_index('start_time')
    weekly_trend = e2e.resample('W').agg(
        total_cases=('case_id', 'count'),
        breaches=('is_breach', 'sum')
    )
    weekly_trend['compliance_pct'] = 100 - (weekly_trend['breaches'] / weekly_trend['total_cases'] * 100)
    weekly_trend = weekly_trend.reset_index()
    
    fig5 = px.line(weekly_trend, x="start_time", y="compliance_pct", title="Weekly End-to-End SLA Compliance (%)")
    fig5.add_hline(y=100, line_dash="dash", line_color="green", annotation_text="Target 100%")
    st.plotly_chart(fig5, width='stretch')

# 6. WHAT-IF PANEL
with tab6:
    st.header("Simulated Fix Impact")
    
    if "simulation" in metrics:
        sim = metrics["simulation"]
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Current Avg E2E (Days)", f"{sim['current_avg_days']:.1f}")
        with col2:
            st.metric("Projected Avg E2E (Days)", f"{sim['projected_avg_days']:.1f}", delta=f"-{sim['absolute_days_saved_per_case']:.1f} days")
        with col3:
            st.metric("Cycle Time Reduction", f"{sim['pct_reduction']:.1f}%", delta_color="inverse")
            
        st.success(f"**Recommendation:** By redesigning the upfront data collection to eliminate structural backward rework loops (e.g., Underwriting -> Document Check), the bank will save an average of **{sim['absolute_days_saved_per_case']:.1f} days per application**.")
        
    else:
        st.info("Simulation metrics not found. Ensure Phase 7 ran successfully.")

import os
import json
import pandas as pd
import pm4py
from pm4py.objects.petri_net.obj import PetriNet, Marking
from pm4py.objects.petri_net.utils import petri_utils

DATA_FILE = "data/processed/processed_event_log.parquet"
METRICS_FILE = "outputs/metrics.json"
DEVIATIONS_FILE = "outputs/deviations.json"

def create_reference_model():
    """
    Creates the 'as-designed' happy path Petri net:
    Submitted -> Document Check -> Underwriting -> Manager Review -> (Approved | Rejected | Cancelled)
    """
    net = PetriNet("As-Designed Loan Process")
    
    # Create Places
    p_start = PetriNet.Place("p_start")
    p_1 = PetriNet.Place("p_1")
    p_2 = PetriNet.Place("p_2")
    p_3 = PetriNet.Place("p_3")
    p_4 = PetriNet.Place("p_4")
    p_end = PetriNet.Place("p_end")
    
    net.places.add(p_start)
    net.places.add(p_1)
    net.places.add(p_2)
    net.places.add(p_3)
    net.places.add(p_4)
    net.places.add(p_end)
    
    # Create Transitions
    t_sub = PetriNet.Transition("t_sub", "Submitted")
    t_doc = PetriNet.Transition("t_doc", "Document Check")
    t_uw = PetriNet.Transition("t_uw", "Underwriting")
    t_mgr = PetriNet.Transition("t_mgr", "Manager Review")
    
    t_app = PetriNet.Transition("t_app", "Approved")
    t_rej = PetriNet.Transition("t_rej", "Rejected")
    t_can = PetriNet.Transition("t_can", "Cancelled")
    
    net.transitions.add(t_sub)
    net.transitions.add(t_doc)
    net.transitions.add(t_uw)
    net.transitions.add(t_mgr)
    net.transitions.add(t_app)
    net.transitions.add(t_rej)
    net.transitions.add(t_can)
    
    # Add Arcs
    petri_utils.add_arc_from_to(p_start, t_sub, net)
    petri_utils.add_arc_from_to(t_sub, p_1, net)
    
    petri_utils.add_arc_from_to(p_1, t_doc, net)
    petri_utils.add_arc_from_to(t_doc, p_2, net)
    
    petri_utils.add_arc_from_to(p_2, t_uw, net)
    petri_utils.add_arc_from_to(t_uw, p_3, net)
    
    petri_utils.add_arc_from_to(p_3, t_mgr, net)
    petri_utils.add_arc_from_to(t_mgr, p_4, net)
    
    # Outcomes split from Manager Review
    petri_utils.add_arc_from_to(p_4, t_app, net)
    petri_utils.add_arc_from_to(p_4, t_rej, net)
    petri_utils.add_arc_from_to(p_4, t_can, net)
    
    petri_utils.add_arc_from_to(t_app, p_end, net)
    petri_utils.add_arc_from_to(t_rej, p_end, net)
    petri_utils.add_arc_from_to(t_can, p_end, net)
    
    # Initial and Final Markings
    initial_marking = Marking()
    initial_marking[p_start] = 1
    
    final_marking = Marking()
    final_marking[p_end] = 1
    
    return net, initial_marking, final_marking


def run_conformance():
    print(f"Loading data from {DATA_FILE}...")
    df = pd.read_parquet(DATA_FILE)
    
    # Filter out 'Other' activities to focus conformance on the core process
    # If the log has "Other" activities, the token replay will fail/penalize fitness heavily
    # because they are not in the reference model.
    # The reference model only defines the mapped business stages.
    df_core = df[df['stage'] != 'Other'].copy()
    
    print("Formatting log for PM4Py...")
    log = pm4py.format_dataframe(df_core, case_id='case_id', activity_key='stage', timestamp_key='timestamp')
    
    print("Building reference 'as-designed' Petri Net...")
    net, im, fm = create_reference_model()
    
    print("Running Token-Based Replay (this may take a moment)...")
    # Using token based replay because alignment based is very slow on 13k traces
    replay_results = pm4py.conformance_diagnostics_token_based_replay(log, net, im, fm)
    
    # Calculate fitness metrics
    fitness_scores = [res['trace_fitness'] for res in replay_results]
    overall_fitness = sum(fitness_scores) / len(fitness_scores) if fitness_scores else 0
    perfect_cases = sum(1 for f in fitness_scores if f == 1.0)
    perfect_cases_pct = (perfect_cases / len(fitness_scores)) * 100 if fitness_scores else 0
    
    print(f"Overall Fitness Score: {overall_fitness:.4f}")
    print(f"Perfectly Conformant Cases: {perfect_cases} ({perfect_cases_pct:.2f}%)")
    
    # Analyze variants to find most common deviations
    print("Analyzing deviations...")
    # Get variants using pandas for reliability
    variants = df_core.groupby('case_id')['stage'].apply(tuple).value_counts()
    
    deviations = []
    for variant, count in variants.items():
        happy_paths = [
            ('Submitted', 'Document Check', 'Underwriting', 'Manager Review', 'Approved'),
            ('Submitted', 'Document Check', 'Underwriting', 'Manager Review', 'Rejected'),
            ('Submitted', 'Document Check', 'Underwriting', 'Manager Review', 'Cancelled')
        ]
        
        if variant not in happy_paths:
            variant_list = list(variant)
            issue = "Complex Deviation"
            
            if len(variant_list) < 5:
                issue = "Skipped Stage(s)"
            elif len(set(variant_list)) < len(variant_list):
                issue = "Repeated Stage(s) / Rework Loop"
            
            deviations.append({
                "path": " -> ".join(variant_list),
                "frequency": int(count),
                "type": issue
            })
            
    # Sort deviations by frequency
    deviations = sorted(deviations, key=lambda x: x['frequency'], reverse=True)
    top_deviations = deviations[:10]
    
    # Save Metrics
    metrics = {
        "conformance": {
            "overall_fitness_score": float(overall_fitness),
            "perfectly_conformant_cases": int(perfect_cases),
            "perfectly_conformant_pct": float(perfect_cases_pct),
            "total_variants": len(variants),
            "non_conformant_variants": len(deviations)
        }
    }
    
    if not os.path.exists("outputs"):
        os.makedirs("outputs")
        
    if os.path.exists(METRICS_FILE):
        try:
            with open(METRICS_FILE, "r") as f:
                existing = json.load(f)
            existing.update(metrics)
            metrics = existing
        except:
            pass
            
    with open(METRICS_FILE, "w") as f:
        json.dump(metrics, f, indent=4)
        
    with open(DEVIATIONS_FILE, "w") as f:
        json.dump(top_deviations, f, indent=4)
        
    print(f"Conformance metrics saved to {METRICS_FILE}")
    print(f"Top deviations saved to {DEVIATIONS_FILE}")

if __name__ == "__main__":
    run_conformance()

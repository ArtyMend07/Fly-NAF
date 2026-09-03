import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import config
import torch
import time
from neural.models import FlyBrainModel
from neural.data_loader import get_hash_tables, load_connectome_weights

def analyze_pathway():
    print("[ANALYSIS] Loading connectome for structural pathway analysis...")
    device = 'cpu'
    
    comp_path = '../fly-brain/data/2025_Completeness_783.csv'
    conn_path = '../fly-brain/data/2025_Connectivity_783.parquet'
    wt_dir = '../fly-brain/data'
    
    flyid2i, i2flyid = get_hash_tables(comp_path)
    weights = load_connectome_weights(conn_path, comp_path, wt_dir, csr=True, device=device)
    num_neurons = weights.shape[0]
    
    eye_ids = config.SENSORY_NEURONS['left_eye_cluster']
    exc_indices = [flyid2i[n] for n in eye_ids if n in flyid2i]
    
    p9_ids = [config.MOTOR_NEURONS['dnp01_giant_fiber'][0]]
    motor_indices = [flyid2i[n] for n in p9_ids if n in flyid2i]
    
    print(f"[ANALYSIS] Initializing LIF Brain with {len(exc_indices)} simultaneous sensory inputs...")
    
    arousal_multiplier = 10.0
    weights = weights * arousal_multiplier
    
    model = FlyBrainModel(num_neurons, weights, exc_indices=exc_indices, device=device)
    
    base_rate = 200.0
    rates = torch.zeros(1, num_neurons, device=device)
    rates[:, exc_indices] = base_rate
    
    print("[ANALYSIS] Injecting stimulus (200 Hz) into the cluster and recording spikes...")
    
    total_spikes_per_neuron = torch.zeros(num_neurons, device=device)
    
    for _ in range(5000):
        spikes = model.step(rates)
        if spikes is not None:
            total_spikes_per_neuron += spikes[0]
            
    active_neurons = (total_spikes_per_neuron > 0).nonzero(as_tuple=True)[0]
    print(f"\n[RESULTS] Out of {num_neurons} neurons, only {len(active_neurons)} fired at least once.")
    
    spike_counts = total_spikes_per_neuron[active_neurons]
    sorted_indices = torch.argsort(spike_counts, descending=True)
    
    print("\n[TOP 10 MOST ACTIVE NEURONS]")
    for i in range(min(10, len(active_neurons))):
        idx = active_neurons[sorted_indices[i]].item()
        spikes = spike_counts[sorted_indices[i]].item()
        is_sensory = idx in exc_indices
        print(f"  Neuron {i2flyid[idx]} (Index {idx}): {spikes} spikes {'(SENSORY)' if is_sensory else ''}")
        
    print(f"\n[MOTOR STATUS]")
    for m_idx in motor_indices:
        print(f"  Motor Neuron {i2flyid[m_idx]} (Index {m_idx}): {total_spikes_per_neuron[m_idx].item()} spikes")

    downstream_active = [idx.item() for idx in active_neurons if idx.item() not in exc_indices]
    
    motor_fired = any(total_spikes_per_neuron[m_idx].item() > 0 for m_idx in motor_indices)
    
    print("\n[PATHWAY ANALYSIS]")
    if len(downstream_active) == 0:
        print("  CRITICAL FAILURE: No interneurons recruited.")
    elif motor_fired:
        print("  SUCCESS: Signal propagated through the network and reached the motor target.")
    else:
        print("  FAILURE: Signal propagated through interneurons but failed to reach the motor target.")
if __name__ == '__main__':
    analyze_pathway()

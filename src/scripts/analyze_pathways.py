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
    
    sugar_ids = [720575940624963786, 720575940630233916, 720575940637568838, 
                 720575940638202345, 720575940617000768, 720575940630797113]
    exc_indices = [flyid2i[n] for n in sugar_ids if n in flyid2i]
    
    p9_ids = [720575940627652358, 720575940635872101]
    motor_indices = [flyid2i[n] for n in p9_ids if n in flyid2i]
    
    model = FlyBrainModel(num_neurons, weights, exc_indices=exc_indices, device=device)
    
    base_rate = 10000.0
    rates = torch.zeros(1, num_neurons, device=device)
    rates[:, exc_indices] = base_rate
    
    print("[ANALYSIS] Injecting stimulus and recording total spikes per neuron...")
    
    total_spikes_per_neuron = torch.zeros(num_neurons, device=device)
    
    for _ in range(1000):
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

    print("\n[STRUCTURAL BOTTLENECK ANALYSIS]")
    downstream_active = [idx.item() for idx in active_neurons if idx.item() not in exc_indices]
    
    if len(downstream_active) == 0:
        print("  CRITICAL FAILURE: The sensory neurons spiked, but they failed to trigger even a SINGLE downstream interneuron.")
        print("  Why? Because the outgoing synaptic weights from these specific Sugar GRNs are structurally too weak to overcome the resting threshold of their neighbors, or they are disconnected in this specific sub-graph.")
    else:
        print("  The signal reached interneurons, but died before reaching the motor cortex.")

if __name__ == '__main__':
    analyze_pathway()

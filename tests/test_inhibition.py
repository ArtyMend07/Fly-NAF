import sys
import os
import torch
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
import config
from neural.models import FlyBrainModel
from neural.data_loader import get_hash_tables, load_connectome_weights

def test_biological_inhibition():
    print("[TEST] Loading connectome for Inhibition test...")
    device = 'cpu'
    comp_path = '../fly-brain/data/2025_Completeness_783.csv'
    conn_path = '../fly-brain/data/2025_Connectivity_783.parquet'
    wt_dir = '../fly-brain/data'
    flyid2i, i2flyid = get_hash_tables(comp_path)
    weights = load_connectome_weights(conn_path, comp_path, wt_dir, csr=True, device=device)
    num_neurons = weights.shape[0]
    eye_ids = config.SENSORY_NEURONS['left_eye_cluster']
    inhib_ids = config.SENSORY_NEURONS['camera_inhibitor_left']
    motor_ids = [config.MOTOR_NEURONS['dnp01_giant_fiber'][0]]
    exc_indices = [flyid2i[n] for n in eye_ids if n in flyid2i]
    inhib_indices = [flyid2i[n] for n in inhib_ids if n in flyid2i]
    motor_indices = [flyid2i[n] for n in motor_ids if n in flyid2i]
    arousal_multiplier = 10.0
    weights = weights * arousal_multiplier
    model = FlyBrainModel(num_neurons, weights, exc_indices=exc_indices + inhib_indices, device=device)
    print("\n===========================================")
    print("TEST 1: PANIC REFLEX (VISUAL THREAT ONLY)")
    print("===========================================")
    rates = torch.zeros(1, num_neurons, device=device)
    rates[:, exc_indices] = 200.0 
    total_spikes = 0
    for _ in range(5000):
        spikes = model.step(rates)
        if spikes is not None:
            total_spikes += spikes[0, motor_indices[0]].item()
    print(f"Giant Fiber Spikes: {total_spikes}")
    if total_spikes > 0:
        print("RESULT: Normal startle response triggered. Door would CLOSE.")
    else:
        print("RESULT: Failure. Reflex did not work.")

    model.reset_state()

    print("\n===========================================")
    print("TEST 2: CAMERA INHIBITION (THREAT + CAMERA)")
    print("===========================================")
    rates = torch.zeros(1, num_neurons, device=device)
    rates[:, exc_indices] = 200.0     
    rates[:, inhib_indices] = 200.0   
    total_spikes_inhibited = 0
    for _ in range(5000):
        spikes = model.step(rates)
        if spikes is not None:
            total_spikes_inhibited += spikes[0, motor_indices[0]].item()
    print(f"Giant Fiber Spikes: {total_spikes_inhibited}")
    if total_spikes_inhibited == 0 and total_spikes > 0:
        print("RESULT: SUCCESS! The GABAergic interneuron completely neutralized the panic reflex mathematically.")
        print("The fly is looking at the camera safely.")
    else:
        print("RESULT: Failure. Inhibition was not strong enough.")

if __name__ == '__main__':
    test_biological_inhibition()
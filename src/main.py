import time
import threading
import torch

from neural.models import FlyBrainModel
from neural.data_loader import get_hash_tables, load_connectome_weights
from env.vision import FNAFVision
from env.input_controller import FNAFController

class SharedState:
    def __init__(self):
        self.sensory_rate = 0.0
        self.lock = threading.Lock()

def vision_thread_loop(state, vision):
    while True:
        try:
            rate = vision.get_sensory_rates()
            with state.lock:
                state.sensory_rate = rate
            time.sleep(1/30.0)
        except Exception as e:
            break

def main():
    print("[SYSTEM] Starting FNAF Fly Brain Connectome...")
    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    print(f"[SYSTEM] Hardware Target: {device.upper()}")
    
    comp_path = '../fly-brain/data/2025_Completeness_783.csv'
    conn_path = '../fly-brain/data/2025_Connectivity_783.parquet'
    wt_dir = '../fly-brain/data'
    
    print("[SYSTEM] Loading anatomical indices...")
    flyid2i, i2flyid = get_hash_tables(comp_path)
    
    print("[SYSTEM] Loading 100MB sparse connectome weights...")
    weights = load_connectome_weights(conn_path, comp_path, wt_dir, csr=True, device=device)
    num_neurons = weights.shape[0]
    print(f"[SYSTEM] Brain loaded. Total Neurons: {num_neurons}")
    
    sugar_ids = [720575940624963786, 720575940630233916, 720575940637568838, 
                 720575940638202345, 720575940617000768, 720575940630797113]
    exc_indices = [flyid2i[n] for n in sugar_ids if n in flyid2i]
    
    p9_ids = [720575940627652358, 720575940635872101]
    motor_indices = [flyid2i[n] for n in p9_ids if n in flyid2i]
    
    print("[SYSTEM] Instantiating neural engine...")
    model = FlyBrainModel(num_neurons, weights, exc_indices=exc_indices, device=device)
    
    print("[SYSTEM] Starting OpenCV vision thread...")
    vision = FNAFVision()
    controller = FNAFController()
    state = SharedState()
    
    v_thread = threading.Thread(target=vision_thread_loop, args=(state, vision), daemon=True)
    v_thread.start()
    
    base_rate = 200.0
    rates = torch.zeros(1, num_neurons, device=device)
    
    print("[SYSTEM] Core loop running. Listening for visual spikes...")
    
    try:
        while True:
            t_start = time.perf_counter()
            
            with state.lock:
                current_rate_multiplier = state.sensory_rate
                
            rates[:, exc_indices] = base_rate * current_rate_multiplier
            
            spikes = None
            for _ in range(100):
                spikes = model.step(rates)
                
                if spikes is not None:
                    if spikes[0, motor_indices].any():
                        controller.click_left_door()
                        break
                        
            elapsed = time.perf_counter() - t_start
            if elapsed < 0.01:
                time.sleep(0.01 - elapsed)
                
    except KeyboardInterrupt:
        pass

if __name__ == '__main__':
    main()

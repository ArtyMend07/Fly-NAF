import time
import threading
import torch
import random

from brain_adapter import BrainAdapter
from env.vision import FNAFVision
from env.input_controller import FNAFController
import config

class SharedState:
    def __init__(self):
        self.left_rate = 0.0
        self.right_rate = 0.0
        self.is_checking_left = False
        self.is_checking_right = False
        self.lock = threading.Lock()

def vision_thread_loop(state: SharedState, vision: FNAFVision):
    while True:
        try:
            with state.lock:
                check_l = state.is_checking_left
                check_r = state.is_checking_right
                
            l_val = vision.get_left_sensory_rate() if check_l else 0.0
            r_val = vision.get_right_sensory_rate() if check_r else 0.0
            
            with state.lock:
                state.left_rate = l_val
                state.right_rate = r_val
                
            time.sleep(1.0 / 30.0)
        except Exception:
            break

def foraging_thread_loop(state: SharedState, vision: FNAFVision, controller: FNAFController):
    min_inv = config.FORAGING_PARAMS["min_interval_sec"]
    max_inv = config.FORAGING_PARAMS["max_interval_sec"]
    insp_time = config.FORAGING_PARAMS["light_inspection_time"]
    
    # 1. Wake Up Routine (Night 1, 12 AM) - Capture strict baseline
    print("[SYSTEM] Executing Wake-Up Routine (Calibration)...")
    time.sleep(1.0)
    
    # Left
    controller.set_left_light(True)
    time.sleep(0.1)
    vision.capture_left_reference()
    print("[SYSTEM] Left reference captured.")
    controller.set_left_light(False)
    time.sleep(0.5)
    
    # Right
    controller.set_right_light(True)
    time.sleep(0.1)
    vision.capture_right_reference()
    print("[SYSTEM] Right reference captured.")
    controller.set_right_light(False)
    
    print("[SYSTEM] Wake-Up Routine complete. Entering paranoia loop.")
    
    # 2. Infinite Foraging Loop
    sides = ["left", "right"]
    while True:
        sleep_duration = random.uniform(min_inv, max_inv)
        time.sleep(sleep_duration)
        
        target = random.choice(sides)
        
        if target == "left":
            controller.set_left_light(True)
            time.sleep(0.1) 
            with state.lock: state.is_checking_left = True
            time.sleep(insp_time)
            with state.lock: state.is_checking_left = False
            controller.set_left_light(False)
        else:
            controller.set_right_light(True)
            time.sleep(0.1)
            with state.lock: state.is_checking_right = True
            time.sleep(insp_time)
            with state.lock: state.is_checking_right = False
            controller.set_right_light(False)

def main():
    print("[SYSTEM] Starting FNAF Fly Brain Connectome...")
    device = "cuda" if torch.cuda.is_available() else "cpu"
    
    adapter = BrainAdapter(
        config.COMPLETENESS_CSV, 
        config.CONNECTIVITY_PARQUET, 
        config.DATA_DIR, 
        device
    )
    
    l_sensory_idx = adapter.map_neuron_ids_to_indices(config.SENSORY_NEURONS["left_eye_cluster"])
    r_sensory_idx = adapter.map_neuron_ids_to_indices(config.SENSORY_NEURONS["right_eye_cluster"])
    all_sensory = l_sensory_idx + r_sensory_idx
    
    l_motor_idx = adapter.map_neuron_ids_to_indices([config.MOTOR_NEURONS["dnp01_giant_fiber"][0]])
    r_motor_idx = adapter.map_neuron_ids_to_indices([config.MOTOR_NEURONS["dnp01_giant_fiber"][1]])
    
    adapter.initialize_model(exc_indices=all_sensory)
    
    vision = FNAFVision()
    controller = FNAFController()
    state = SharedState()
    
    v_thread = threading.Thread(target=vision_thread_loop, args=(state, vision), daemon=True)
    v_thread.start()
    
    f_thread = threading.Thread(target=foraging_thread_loop, args=(state, vision, controller), daemon=True)
    f_thread.start()
    
    base_rate = config.SIMULATION_PARAMS["base_sensory_rate_hz"]
    steps_per_frame = config.SIMULATION_PARAMS["steps_per_frame"]
    
    rates = torch.zeros(1, adapter.num_neurons, device=device)
    
    print("[SYSTEM] Brain Core Online.")
    
    try:
        while True:
            t_start = time.perf_counter()
            
            with state.lock:
                l_mult = state.left_rate
                r_mult = state.right_rate
                
            rates[:, l_sensory_idx] = base_rate * l_mult
            rates[:, r_sensory_idx] = base_rate * r_mult
            
            spikes = adapter.step(rates, steps=steps_per_frame)
            
            if spikes is not None:
                if spikes[0, l_motor_idx].any():
                    print("\n[BRAIN ALERT] LEFT GIANT FIBER FIRED! CLOSING LEFT DOOR!")
                    controller.trigger_left_door()
                    with state.lock: state.left_rate = 0.0
                    time.sleep(0.5)
                    
                if spikes[0, r_motor_idx].any():
                    print("\n[BRAIN ALERT] RIGHT GIANT FIBER FIRED! CLOSING RIGHT DOOR!")
                    controller.trigger_right_door()
                    with state.lock: state.right_rate = 0.0
                    time.sleep(0.5)
                        
            elapsed = time.perf_counter() - t_start
            if elapsed < 0.01:
                time.sleep(0.01 - elapsed)
                
    except KeyboardInterrupt:
        print("\n[SYSTEM] Shutdown initiated.")

if __name__ == "__main__":
    main()


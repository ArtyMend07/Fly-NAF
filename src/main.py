import time
import threading
import torch

from brain_adapter import BrainAdapter
from env.vision import FNAFVision
from env.input_controller import FNAFController
import config

class SharedState:
    def __init__(self):
        self.sensory_rate = 0.0
        self.lock = threading.Lock()

def vision_thread_loop(state: SharedState, vision: FNAFVision):
    while True:
        try:
            rate = vision.get_sensory_rates()
            with state.lock:
                state.sensory_rate = rate
            time.sleep(1.0 / 30.0)
        except Exception:
            break

def main():
    print("[SYSTEM] Starting FNAF Fly Brain Connectome...")
    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    print(f"[SYSTEM] Hardware Target: {device.upper()}")
    
    adapter = BrainAdapter(
        config.COMPLETENESS_CSV, 
        config.CONNECTIVITY_PARQUET, 
        config.DATA_DIR, 
        device
    )
    
    sensory_indices = adapter.map_neuron_ids_to_indices(config.SENSORY_NEURONS['sugar_grns'])
    motor_indices = adapter.map_neuron_ids_to_indices(config.MOTOR_NEURONS['p9_walking'])
    
    adapter.initialize_model(exc_indices=sensory_indices)
    
    vision = FNAFVision(
        target_x=config.VISION_CALIBRATION['bonnie_target_x'],
        target_y=config.VISION_CALIBRATION['bonnie_target_y'],
        bbox_size=config.VISION_CALIBRATION['bbox_size'],
        threshold=config.VISION_CALIBRATION['brightness_threshold']
    )
    
    controller = FNAFController(
        left_door_x=config.MOTOR_CALIBRATION['left_door_button_x'],
        left_door_y=config.MOTOR_CALIBRATION['left_door_button_y']
    )
    
    state = SharedState()
    
    print("[SYSTEM] Starting OpenCV vision thread...")
    v_thread = threading.Thread(target=vision_thread_loop, args=(state, vision), daemon=True)
    v_thread.start()
    
    base_rate = config.SIMULATION_PARAMS['base_sensory_rate_hz']
    steps_per_frame = config.SIMULATION_PARAMS['steps_per_frame']
    
    rates = torch.zeros(1, adapter.num_neurons, device=device)
    
    print("[SYSTEM] Core loop running. Listening for visual spikes...")
    
    try:
        while True:
            t_start = time.perf_counter()
            
            with state.lock:
                current_multiplier = state.sensory_rate
                
            rates[:, sensory_indices] = base_rate * current_multiplier
            
            spikes = adapter.step(rates, steps=steps_per_frame)
            
            if spikes is not None and spikes[0, motor_indices].any():
                print("\n[BRAIN ALERT] MOTOR NEURON FIRED! CLICKING DOOR!")
                controller.trigger_left_door()
                time.sleep(1.0) 
                        
            elapsed = time.perf_counter() - t_start
            if elapsed < 0.01:
                time.sleep(0.01 - elapsed)
                
    except KeyboardInterrupt:
        print("\n[SYSTEM] Shutdown initiated.")

if __name__ == '__main__':
    main()

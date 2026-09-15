import time
import os
from datetime import datetime

class ConnectomeTelemetry:
    def __init__(self):
        self.start_time = time.time()
        self.events = []
        self.stats = {
            'left_door_panics': 0,
            'right_door_panics': 0,
            'camera_pulls': 0,
            'left_light_saccades': 0,
            'right_light_saccades': 0
        }
        
    def record_door_panic(self, side: str):
        t = time.time() - self.start_time
        self.stats[f'{side}_door_panics'] += 1
        self.events.append(f"[{t:>6.1f}s] Visual threat detected. Giant fiber fired. {side.capitalize()} door slammed.")

    def record_camera_pull(self):
        t = time.time() - self.start_time
        self.stats['camera_pulls'] += 1
        self.events.append(f"[{t:>6.1f}s] CPG threshold crossed. Monitor raised for environmental scan.")

    def record_light_saccade(self, side: str, bias: float):
        t = time.time() - self.start_time
        self.stats[f'{side}_light_saccades'] += 1
        self.events.append(f"[{t:>6.1f}s] Thermodynamic noise triggered {side} light check (Membrane bias: {bias:+.2f}).")

    def dump_report(self):
        duration = time.time() - self.start_time
        os.makedirs("logs", exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filepath = os.path.join("logs", f"session_telemetry_{timestamp}.txt")
        
        with open(filepath, "w", encoding="utf-8") as f:
            f.write("=== Connectome Session Report ===\n")
            f.write(f"Session Duration : {duration:.1f} seconds\n")
            f.write(f"Timestamp        : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            f.write("--- Quantitative Breakdown ---\n")
            f.write(f"Left Door Panics (Bonnie)  : {self.stats['left_door_panics']}\n")
            f.write(f"Right Door Panics (Chica)  : {self.stats['right_door_panics']}\n")
            f.write(f"CPG Camera Pulls           : {self.stats['camera_pulls']}\n")
            f.write(f"Left Light Checks          : {self.stats['left_light_saccades']}\n")
            f.write(f"Right Light Checks         : {self.stats['right_light_saccades']}\n\n")
            
            f.write("--- Chronological Event Log ---\n")
            for evt in self.events:
                f.write(evt + "\n")
                
        return filepath

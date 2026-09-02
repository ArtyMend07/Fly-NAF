import os

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(os.path.dirname(PROJECT_ROOT), 'fly-brain', 'data')

CONNECTIVITY_PARQUET = os.path.join(DATA_DIR, '2025_Connectivity_783.parquet')
COMPLETENESS_CSV = os.path.join(DATA_DIR, '2025_Completeness_783.csv')

VISION_CALIBRATION = {
    'bonnie_target_x': 425,
    'bonnie_target_y': 486,
    'bbox_size': 10,
    'brightness_threshold': 50.0
}

MOTOR_CALIBRATION = {
    'left_door_button_x': 264,
    'left_door_button_y': 440
}

SENSORY_NEURONS = {
    'sugar_grns': [
        720575940624963786
    ]
}

MOTOR_NEURONS = {
    'p9_walking': [
        720575940627652358, 720575940635872101
    ]
}

SIMULATION_PARAMS = {
    'base_sensory_rate_hz': 10000.0,
    'steps_per_frame': 100,
    'target_fps': 100
}

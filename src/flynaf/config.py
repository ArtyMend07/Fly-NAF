import os
from dataclasses import dataclass, field
from typing import List

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA_DIR = os.path.join(os.path.dirname(PROJECT_ROOT), 'fly-brain', 'data')

CONNECTIVITY_PARQUET = os.path.join(DATA_DIR, '2025_Connectivity_783.parquet')
COMPLETENESS_CSV = os.path.join(DATA_DIR, '2025_Completeness_783.csv')
ANNOTATIONS_TSV = os.path.join(
    os.path.dirname(PROJECT_ROOT), 'flywire_annotations', 'supplemental_files',
    'Supplemental_file1_neuron_annotations.tsv',
)
CELL_TYPE_CACHE = os.path.join(DATA_DIR, 'cell_types_783.parquet')


@dataclass(frozen=True)
class VisionCalibration:
    left_target_x: int = 240
    left_target_y: int = 324
    left_bbox_size: int = 481
    right_target_x: int = 851
    right_target_y: int = 328
    right_bbox_size: int = 335
    left_window: tuple = (340, 200, 540, 560)
    right_window: tuple = (684, 161, 1019, 496)


@dataclass(frozen=True)
class MotorCalibration:
    left_door_button_x: int = 55
    left_door_button_y: int = 343
    left_light_button_x: int = 52
    left_light_button_y: int = 450
    right_door_button_x: int = 1210
    right_door_button_y: int = 346
    right_light_button_x: int = 1217
    right_light_button_y: int = 467
    camera_hover_x: int = 552
    camera_hover_y: int = 665
    camera_bar_approach_y: int = 540
    click_delay_sec: float = 0.05
    pan_delay_sec: float = 1.0


@dataclass(frozen=True)
class SimulationParams:
    base_sensory_rate_hz: float = 1000.0
    steps_per_frame: int = 2
    target_fps: int = 10
    arousal_multiplier: float = 3.0
    settle_window_frames: int = 10
    settle_growth_ratio: float = 1.2
    settle_max_frames: int = 200


@dataclass(frozen=True)
class ForagingParams:
    subliminal_noise_hz: float = 1.0
    mse_threshold: float = 40.0
    light_inspection_frames: int = 12
    light_inspection_max_sec: float = 8.0
    light_activation_settle_sec: float = 0.4
    motor_refractory_sec: float = 2.0
    camera_refractory_sec: float = 15.0
    saccade_refractory_sec: float = 2.5
    camera_watch_max_sec: float = 6.0
    camera_watch_min_sec: float = 0.8
    camera_release_forage_bias: float = 0.5
    closed_door_mse_threshold: float = 30.0


@dataclass(frozen=True)
class VisionDynamics:
    frame_buffer_size: int = 5
    capture_delay_sec: float = 0.016
    reference_sweep_sec: float = 4.0
    bank_tolerance_mse: float = 5.0
    light_button_half_size: int = 10
    light_button_lit_level: float = 140.0
    light_check_interval_sec: float = 0.08


@dataclass(frozen=True)
class NeuralParams:
    tau_syn: float = 5.0
    t_delay: float = 1.0
    v0: float = -52.0
    v_reset: float = -52.0
    v_rest: float = -52.0
    v_threshold: float = -45.0
    tau_mem: float = 20.0
    t_refrac: float = 2.2
    scale_poisson: int = 250
    w_scale: float = 0.275
    dt: float = 1.0


@dataclass(frozen=True)
class CameraDetection:
    map_left: int = 820
    map_top: int = 345
    map_right: int = 1240
    map_bottom: int = 680
    white_level: int = 200
    button_width: tuple = (40, 75)
    button_height: tuple = (25, 45)
    button_fill: float = 0.6
    min_buttons: int = 6
    agreeing_frames: int = 3
    flip_confirm_sec: float = 1.5
    lower_retry_sec: float = 3.0
    lower_gesture_attempts: int = 4


@dataclass(frozen=True)
class BrainView:
    enabled: bool = True
    port: int = 8770
    width: int = 620
    height: int = 1040
    ingame_width: int = 280
    ingame_height: int = 150
    ingame_margin: int = 8
    focus_handback_sec: float = 12.0
    start_countdown_sec: float = 10.0
    game_process: str = 'FiveNightsatFreddys'
    game_title: str = "Five Nights at Freddy's"
    stream_interval_sec: float = 0.05
    patch_interval_sec: float = 0.3
    patch_pixels: int = 72
    beside_min_width: int = 420
    dock_game: bool = True
    corner_radius: int = 14
    launch_browser: bool = True


@dataclass(frozen=True)
class GameLauncher:
    steam_uri: str = 'steam://rungameid/319510'
    executable: str = ''
    port: int = 8771
    width: int = 900
    height: int = 620
    window_wait_sec: float = 90.0
    menu_settle_sec: float = 4.0
    windowed: bool = True
    windowed_wait_sec: float = 30.0
    windowed_stable_sec: float = 2.0
    new_game_x: int | None = 210
    new_game_y: int | None = 419
    continue_x: int | None = 212
    continue_y: int | None = 494
    night_start_new_sec: float = 19.0
    night_start_continue_sec: float = 12.0


@dataclass(frozen=True)
class ExploreDynamics:
    bound: float = 1.0
    drive_leak_per_frame: float = 0.95
    gain_ratio: float = 1.00
    baseline_tau_frames: float = 500.0
    scale_tau_frames: float = 300.0
    release_ratio: float = 0.40


@dataclass(frozen=True)
class SearchDynamics:
    bound: float = 1.0
    drive_leak_per_frame: float = 0.90
    gain_ratio: float = 0.70
    baseline_tau_frames: float = 500.0
    scale_tau_frames: float = 300.0
    habituation_leak_per_frame: float = 0.985
    habituation_gain: float = 3.0
    evidence_gain: float = 4.0
    starvation_sec: float = 30.0


@dataclass(frozen=True)
class DoorDynamics:
    hold_leak_per_frame: float = 0.972
    release_threshold: float = 0.25
    motion_settle_sec: float = 0.5


@dataclass(frozen=True)
class CameraButton:
    name: str
    x: int
    y: int
    side: str
    channel: str
    pursue_to: str | None = None


@dataclass(frozen=True)
class TabletVision:
    feed_x: int = 470
    feed_y: int = 330
    feed_size: int = 360
    feed_pixels: int = 64
    capture_delay_sec: float = 0.03
    map_ready_sec: float = 0.4
    raise_settle_sec: float = 1.2
    switch_settle_sec: float = 0.5
    reference_sweep_sec: float = 3.0
    reference_frames: int = 24
    noise_margin: float = 1.5
    figure_span_mse: float = 1000.0
    loom_span_mse: float = 1000.0
    loom_speed_span_mse_per_sec: float = 3000.0
    loom_speed_decay_sec: float = 0.3
    lower_settle_sec: float = 0.35
    first_camera: str = '1C'
    cameras: tuple = (
        CameraButton('1C', 925, 484, 'left', 'figure', pursue_to='2A'),
        CameraButton('2A', 983, 599, 'left', 'loom'),
    )


@dataclass(frozen=True)
class CellPopulations:
    eye: tuple = ('LPLC2', 'LC4')
    figure: tuple = ('LC9', 'LC31a')
    loom_size: tuple = ('LPLC2',)
    loom_speed: tuple = ('LC4',)
    giant_fiber: tuple = ('DNp01',)
    looming_escape: tuple = ('DNp04',)
    explore: tuple = ('DNp09',)


@dataclass(frozen=True)
class SensoryNeurons:
    camera_inhibitor_left: List[int] = field(default_factory=lambda: [
        720575940635119723, 720575940627096957, 720575940617948445, 720575940610063918,
        720575940617564246, 720575940618243009, 720575940606218528, 720575940612710883,
        720575940637471039, 720575940624571116, 720575940636700272, 720575940623804853,
        720575940641464309, 720575940627420668, 720575940604201830, 720575940615343060,
        720575940619709972, 720575940632830568, 720575940630246364, 720575940626013958,
        720575940611091012, 720575940624666245, 720575940628014391, 720575940628793621,
        720575940612016498, 720575940617365947, 720575940631924584, 720575940633237785,
        720575940617492821, 720575940621976097, 720575940639811469, 720575940605214636,
        720575940621726698, 720575940631374440, 720575940622401462, 720575940651593974,
        720575940603533246, 720575940632945177, 720575940622318599, 720575940631553453,
        720575940627467087, 720575940633567900, 720575940627201579, 720575940618455791,
        720575940612078511, 720575940626971803, 720575940629938487, 720575940628267264,
        720575940623362698, 720575940616946918,
    ])
    camera_inhibitor_right: List[int] = field(default_factory=lambda: [
        720575940631842360, 720575940636700272, 720575940629701737, 720575940618243009,
        720575940617948445, 720575940612710883, 720575940610063918, 720575940622559512,
        720575940630246364, 720575940618157110, 720575940628436839, 720575940606218528,
        720575940624910887, 720575940631335528, 720575940620320902, 720575940605937097,
        720575940640507763, 720575940615528678, 720575940643439816, 720575940624666245,
        720575940623362698, 720575940627420668, 720575940613497395, 720575940625887119,
        720575940631779532, 720575940621104628, 720575940639811469, 720575940632381536,
        720575940619569835, 720575940633483444, 720575940604285356, 720575940604201830,
        720575940620581748, 720575940626013958, 720575940640597237, 720575940634370751,
        720575940629687824, 720575940632985261, 720575940623804853, 720575940626217244,
        720575940605308082, 720575940606743170, 720575940634823449, 720575940624032611,
        720575940625194558, 720575940627201579, 720575940640521304, 720575940625449530,
        720575940643889608, 720575940621771502,
    ])


VISION_CALIBRATION = VisionCalibration()
MOTOR_CALIBRATION = MotorCalibration()
SIMULATION_PARAMS = SimulationParams()
FORAGING_PARAMS = ForagingParams()
VISION_DYNAMICS = VisionDynamics()
NEURAL_PARAMS = NeuralParams()
CAMERA_DETECTION = CameraDetection()
BRAIN_VIEW = BrainView()
GAME_LAUNCHER = GameLauncher()
EXPLORE_DYNAMICS = ExploreDynamics()
SEARCH_DYNAMICS = SearchDynamics()
DOOR_DYNAMICS = DoorDynamics()
SENSORY_NEURONS = SensoryNeurons()
CELL_POPULATIONS = CellPopulations()
TABLET_VISION = TabletVision()
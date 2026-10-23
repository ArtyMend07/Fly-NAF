from dataclasses import dataclass, field


@dataclass
class SensoryState:
    left_rate: float = 0.0
    right_rate: float = 0.0
    cam_inhib: float = 0.0
    check_left: bool = False
    check_right: bool = False
    camera_open: bool = False
    l_spike: bool = False
    r_spike: bool = False
    l_escape: bool = False
    r_escape: bool = False
    explore_spike: bool = False
    l_explore: bool = False
    r_explore: bool = False
    l_sensory_count: int = 0
    r_sensory_count: int = 0
    forage_bias: float = 0.0
    arousal: float = 0.0
    gaze_side: str = 'left'
    l_ring_count: int = 0
    r_ring_count: int = 0
    remembered: dict = field(default_factory=lambda: {'left': 0.0, 'right': 0.0})
    recalled: float = 0.0
    tablet_seen: bool = False
    blind_until: dict = field(default_factory=lambda: {'left': 0.0, 'right': 0.0})
    door_closed: dict = field(default_factory=lambda: {'left': False, 'right': False})
    cleared_at: dict = field(default_factory=lambda: {'left': 0.0, 'right': 0.0})
    view_cleared_at: dict = field(default_factory=dict)
    look_started: dict = field(default_factory=lambda: {'left': 0.0, 'right': 0.0})
    tablet_camera: str | None = None
    tablet_readable_at: float = 0.0
    tablet_drive: dict = field(default_factory=dict)


@dataclass
class MotorRefrac:
    left: float = 0.0
    right: float = 0.0


@dataclass
class SaccadeRequest:
    side: str | None = None
    reason: str = ''
    drive: float = 0.0
    busy: bool = False
    ready_at: float = 0.0

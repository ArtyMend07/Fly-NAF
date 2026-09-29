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
    l_sensory_count: int = 0
    r_sensory_count: int = 0
    forage_bias: float = 0.0
    office_centred: bool = True
    blind_until: dict = field(default_factory=lambda: {'left': 0.0, 'right': 0.0})


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

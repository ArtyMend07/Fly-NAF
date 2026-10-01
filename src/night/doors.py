import logging

import config
from night.state import MotorRefrac, SensoryState

_log = logging.getLogger(__name__)

SIDES = ('left', 'right')


class DoorControl:
    def __init__(self, controller, telemetry, state: SensoryState):
        dynamics = config.DOOR_DYNAMICS
        self._controller = controller
        self._telemetry = telemetry
        self._state = state
        self._hold_leak = dynamics.hold_leak_per_frame
        self._release_threshold = dynamics.release_threshold
        self._reopen_settle = dynamics.reopen_settle_sec
        self._nominal_fps = config.SIMULATION_PARAMS.target_fps
        self._motor_sec = config.FORAGING_PARAMS.motor_refractory_sec
        self._refrac = MotorRefrac()
        self.closed = {side: False for side in SIDES}
        self._closed_at = {side: 0.0 for side in SIDES}
        self._hold = {side: 0.0 for side in SIDES}

    def refractory(self, side: str, now: float) -> bool:
        return now <= getattr(self._refrac, side)

    def on_giant_fiber(self, side: str, now: float) -> bool:
        if self._state.camera_open:
            return False
        moved = self.slam(side, now, 'giant fiber') is not None
        setattr(self._refrac, side, now + self._motor_sec)
        return moved

    def slam(self, side: str, now: float, cause: str):
        self._hold[side] = 1.0
        if self.closed[side]:
            return None
        _log.warning('%s %s fired, door closed', side, cause)
        self._telemetry.record_door_panic(side, cause)
        self.closed[side] = True
        self._closed_at[side] = now
        return self._press(side, close=True)

    def release_decayed(self, now: float, frame_elapsed: float):
        decay = self._hold_leak ** (frame_elapsed * self._nominal_fps)
        for side in SIDES:
            if not self.closed[side]:
                continue
            self._state.blind_until[side] = now + self._reopen_settle
            self._hold[side] *= decay
            if self._hold[side] >= self._release_threshold or self._state.camera_open:
                continue
            held = now - self._closed_at[side]
            _log.info('%s escape drive decayed after %.1fs, door released', side, held)
            self._telemetry.record_door_release(side, held)
            self._press(side, close=False)
            self.closed[side] = False

    def _press(self, side: str, close: bool):
        if close:
            return getattr(self._controller, f'trigger_{side}_door')()
        return getattr(self._controller, f'open_{side}_door')()

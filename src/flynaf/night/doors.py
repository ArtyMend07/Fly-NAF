import logging

from flynaf import config
from flynaf.night.state import MotorRefrac, SensoryState

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
        self._motion_settle = dynamics.motion_settle_sec
        self._nominal_fps = config.SIMULATION_PARAMS.target_fps
        self._motor_sec = config.FORAGING_PARAMS.motor_refractory_sec
        self._refrac = MotorRefrac()
        self.closed = {side: False for side in SIDES}
        self._closed_at = {side: 0.0 for side in SIDES}
        self._renewed_at = {side: 0.0 for side in SIDES}
        self._calm_at = {side: None for side in SIDES}
        self._hold = {side: 0.0 for side in SIDES}
        self._moving = {side: None for side in SIDES}

    def refractory(self, side: str, now: float) -> bool:
        return now <= getattr(self._refrac, side)

    def on_giant_fiber(self, side: str, now: float) -> bool:
        if self._tablet_in_the_way():
            return False
        moved = self.slam(side, now, 'giant fiber') is not None
        setattr(self._refrac, side, now + self._motor_sec)
        return moved

    def slam(self, side: str, now: float, cause: str):
        self._hold[side] = 1.0
        self._renewed_at[side] = now
        self._calm_at[side] = None
        if self.closed[side]:
            _log.info('%s %s fired behind the closed door, hold renewed', side, cause)
            self._telemetry.record_door_hold_renewed(side, cause)
            return None
        _log.warning('%s %s fired, door closed', side, cause)
        self._telemetry.record_door_panic(side, cause)
        self.closed[side] = True
        self._state.door_closed[side] = True
        self._closed_at[side] = now
        return self._press(side, close=True, now=now)

    def update(self, now: float, frame_elapsed: float):
        decay = self._hold_leak ** (frame_elapsed * self._nominal_fps)
        for side in SIDES:
            self._shade_moving_door(side, now)
            if not self.closed[side]:
                continue
            self._hold[side] *= decay
            if self._hold[side] >= self._release_threshold:
                continue
            if self._calm_at[side] is None:
                self._calm_at[side] = now
            if self._tablet_in_the_way() or not self._verified_clear(side):
                continue
            self._release(side, now)

    def _tablet_in_the_way(self) -> bool:
        return self._state.camera_open or self._state.tablet_seen

    def _verified_clear(self, side: str) -> bool:
        return self._state.cleared_at[side] > self._renewed_at[side]

    def _release(self, side: str, now: float):
        held = now - self._closed_at[side]
        waited = now - self._calm_at[side]
        _log.info('%s escape drive decayed and the last look found the hallway empty, '
                  'door released after %.1fs', side, held)
        self._telemetry.record_door_release(side, held, waited)
        self.closed[side] = False
        self._state.door_closed[side] = False
        self._calm_at[side] = None
        self._press(side, close=False, now=now)

    def _shade_moving_door(self, side: str, now: float):
        moving = self._moving[side]
        if moving is None:
            return
        self._state.blind_until[side] = now + self._motion_settle
        if moving.is_set():
            self._moving[side] = None

    def _press(self, side: str, close: bool, now: float):
        action = f'trigger_{side}_door' if close else f'open_{side}_door'
        done = getattr(self._controller, action)()
        self._moving[side] = done
        self._state.blind_until[side] = now + self._motion_settle
        return done

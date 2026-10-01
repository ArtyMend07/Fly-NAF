import asyncio
import logging
import time

from flynaf import config
from flynaf.env.input_controller import FNAFController
from flynaf.env.vision import FNAFVision
from flynaf.night.motor import await_motor
from flynaf.night.state import SensoryState
from flynaf.night.tablet.watch import IdleTablet

_log = logging.getLogger(__name__)


async def office_comes_back(
    vision: FNAFVision, controller, settle_sec: float, confirm_sec: float
) -> bool:
    vision.clear_buffers()
    deadline = time.time() + confirm_sec
    agreed = 0
    while time.time() < deadline:
        await asyncio.sleep(settle_sec / 2.0)
        if controller is not None and controller.facing() != 'centre':
            agreed = 0
            continue
        if vision.is_camera_up():
            agreed = 0
            continue
        agreed += 1
        if agreed >= 2:
            return True
    return False


async def reanchor_office_reference(
    vision: FNAFVision, settle_sec: float, confirm_sec: float = 0.0, controller=None
) -> bool:
    if not await office_comes_back(vision, controller, settle_sec, max(confirm_sec, settle_sec)):
        return False
    vision.capture_camera_closed_reference()
    return True


async def lower_monitor(
    vision: FNAFVision, controller: FNAFController, settle_sec: float,
    confirm_sec: float, attempt: int, gesture_budget: int,
) -> bool:
    gesture = None
    if attempt < gesture_budget:
        if attempt % 2 == 0:
            gesture = 'sliding off the tablet bar'
            await await_motor(controller.close_camera(force=True))
        else:
            gesture = 'tapping the tablet bar'
            await await_motor(controller.nudge_camera_bar())

    if await reanchor_office_reference(vision, settle_sec, confirm_sec, controller):
        return True

    if gesture is None:
        return False

    _log.warning(
        'the monitor is still up after %s, attempt %d of %d, office patch %.0f mse from '
        'its reference', gesture, attempt + 1, gesture_budget, vision.camera_mse(),
    )
    return False


async def escape_from_tablet(
    vision: FNAFVision, controller: FNAFController, lower_settle_sec: float,
    settle_sec: float, confirm_sec: float, reflex,
) -> bool:
    await await_motor(controller.close_camera(force=True))
    await asyncio.sleep(lower_settle_sec)
    await reflex()
    await await_motor(controller.centre_view())
    return await reanchor_office_reference(vision, settle_sec, confirm_sec, controller)


def release_reason(explore, bored: bool) -> str:
    if not bored:
        return 'cap'
    return 'drive' if explore.spent else 'search'


class MonitorControl:
    def __init__(self, vision, controller, telemetry, state: SensoryState, tablet=None):
        foraging = config.FORAGING_PARAMS
        self._vision = vision
        self._controller = controller
        self._telemetry = telemetry
        self._state = state
        self._tablet = tablet or IdleTablet()
        self._lower_settle_sec = config.TABLET_VISION.lower_settle_sec
        self._watch_max_sec = foraging.camera_watch_max_sec
        self._watch_min_sec = foraging.camera_watch_min_sec
        self._release_bias = foraging.camera_release_forage_bias
        self._refractory_sec = foraging.camera_refractory_sec
        self._settle_sec = config.CAMERA_DETECTION.close_settle_sec
        self._retry_sec = config.CAMERA_DETECTION.lower_retry_sec
        self._confirm_sec = config.CAMERA_DETECTION.lower_confirm_sec
        self._gesture_budget = config.CAMERA_DETECTION.lower_gesture_attempts
        self._attempts = 0
        self.is_open = False
        self.ready_at = 0.0
        self._releasing = False
        self._lowering = None
        self._retry_at = 0.0
        self._opened_at = 0.0
        self._cap_at = 0.0

    def update(self, now: float, explore, forage_bias: float, look_pending: bool):
        self._collect_lowering(now)
        if self._lowering is not None:
            return
        if self.is_open:
            self._release(now, explore, forage_bias)
            return
        if explore.wants_monitor and now > self.ready_at and not look_pending:
            self._raise(now, explore)

    def _raise(self, now: float, explore):
        _log.info(
            'DNp09 %s, camera pull triggered',
            'fired' if explore.commanded
            else f'drive reached the bound ({explore.drive:.2f})',
        )
        self._telemetry.record_camera_pull(explore.commanded, explore.drive)
        self._controller.open_camera()
        self.is_open = True
        self._state.camera_open = True
        self._opened_at = now
        self._cap_at = now + self._watch_max_sec
        self._tablet.on_raise(now)

    def escape(self, now: float, reflex) -> bool:
        if not self.is_open or self._lowering is not None:
            return False
        if not self._releasing:
            self._telemetry.record_camera_release(now - self._opened_at, 'escape')
        self._releasing = True
        self._tablet.on_lower()
        self._lowering = asyncio.create_task(escape_from_tablet(
            self._vision, self._controller, self._lower_settle_sec,
            self._settle_sec, self._confirm_sec, reflex,
        ))
        self._attempts = max(self._attempts, 1)
        return True

    def _release(self, now: float, explore, forage_bias: float):
        watched_for = now - self._opened_at
        if not self._releasing:
            bored = watched_for >= self._watch_min_sec and (
                explore.spent or forage_bias >= self._release_bias
            )
            if now < self._cap_at and not bored:
                return
            self._releasing = True
            self._tablet.on_lower()
            self._telemetry.record_camera_release(watched_for, release_reason(explore, bored))
        if now < self._retry_at:
            return
        if self._attempts == self._gesture_budget:
            _log.warning(
                'neither gesture brought the monitor down in %d tries, so the fly has stopped '
                'reaching for it and is just watching the screen. Lower the tablet by hand and '
                'it picks up from there.', self._gesture_budget,
            )
        self._lowering = asyncio.create_task(
            lower_monitor(
                self._vision, self._controller, self._settle_sec, self._confirm_sec,
                self._attempts, self._gesture_budget,
            )
        )
        self._attempts += 1

    def _collect_lowering(self, now: float):
        if self._lowering is None or not self._lowering.done():
            return
        lowered = self._lowering.result()
        self._lowering = None
        if not lowered:
            self._telemetry.record_monitor_stuck()
            self._retry_at = now + self._retry_sec
            return
        if self._attempts > 1:
            _log.info('the office is back after %d lowering attempts', self._attempts)
        self.is_open = False
        self._releasing = False
        self._attempts = 0
        self._state.camera_open = False
        self.ready_at = now + self._refractory_sec

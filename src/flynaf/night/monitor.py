import asyncio
import logging

from flynaf import clock, config
from flynaf.night.motor import await_motor
from flynaf.night.state import SensoryState
from flynaf.night.tablet.watch import IdleTablet

_log = logging.getLogger(__name__)

ALREADY_THERE_SEC = 0.2


async def screen_shows(vision, up: bool, within_sec: float, poll_sec: float = 0.05) -> bool:
    deadline = clock.now() + within_sec
    while True:
        if vision.is_camera_up() if up else vision.is_camera_down():
            return True
        if clock.now() >= deadline:
            return False
        await asyncio.sleep(poll_sec)


async def put_tablet(vision, controller, up: bool, confirm_sec: float) -> bool:
    if await screen_shows(vision, up, ALREADY_THERE_SEC):
        return True
    await await_motor(controller.flip_tablet())
    return await screen_shows(vision, up, confirm_sec)


async def put_tablet_down(vision, controller, attempts: int | None = None) -> bool:
    detection = config.CAMERA_DETECTION
    for _ in range(attempts or detection.lower_gesture_attempts):
        if await put_tablet(vision, controller, False, detection.flip_confirm_sec):
            return True
    return False


async def escape_from_tablet(vision, controller, confirm_sec: float, reflex) -> bool:
    for _ in range(2):
        if await put_tablet(vision, controller, False, confirm_sec):
            await reflex()
            return True
    return False


def release_reason(explore, bored: bool) -> str:
    if not bored:
        return 'cap'
    return 'drive' if explore.spent else 'search'


class MonitorControl:
    def __init__(self, vision, controller, telemetry, state: SensoryState, tablet=None):
        foraging = config.FORAGING_PARAMS
        detection = config.CAMERA_DETECTION
        self._vision = vision
        self._controller = controller
        self._telemetry = telemetry
        self._state = state
        self._tablet = tablet or IdleTablet()
        self._watch_max_sec = foraging.camera_watch_max_sec
        self._watch_min_sec = foraging.camera_watch_min_sec
        self._release_bias = foraging.camera_release_forage_bias
        self._refractory_sec = foraging.camera_refractory_sec
        self._confirm_sec = detection.flip_confirm_sec
        self._retry_sec = detection.lower_retry_sec
        self._gesture_budget = detection.lower_gesture_attempts
        self._attempts = 0
        self.is_open = False
        self.ready_at = 0.0
        self._releasing = False
        self._gesture = None
        self._retry_at = 0.0
        self._opened_at = 0.0
        self._cap_at = 0.0

    @property
    def engaged(self) -> bool:
        return self.is_open or self._gesture is not None

    def update(self, now: float, explore, forage_bias: float, look_pending: bool):
        self._collect(now)
        if self._gesture is not None:
            return
        if self.is_open:
            self._release(now, explore, forage_bias)
            return
        if self._state.tablet_seen:
            self._tidy(now)
            return
        if explore.wants_monitor and now > self.ready_at and not look_pending:
            self._raise(now, explore)

    def escape(self, now: float, reflex) -> bool:
        if not self.is_open or self._gesture is not None:
            return False
        if not self._releasing:
            self._telemetry.record_camera_release(now - self._opened_at, 'escape')
        self._releasing = True
        self._tablet.on_lower()
        self._start('lower', escape_from_tablet(
            self._vision, self._controller, self._confirm_sec, reflex,
        ))
        return True

    def _raise(self, now: float, explore):
        _log.info(
            'DNp09 %s, camera pull triggered',
            'fired' if explore.commanded
            else f'drive reached the bound ({explore.drive:.2f})',
        )
        self._telemetry.record_camera_pull(explore.commanded, explore.drive)
        self._start('raise', put_tablet(self._vision, self._controller, True, self._confirm_sec))

    def _tidy(self, now: float):
        if now < self._retry_at:
            return
        _log.warning('the tablet is on screen while the fly believes it is down, putting it away')
        self._telemetry.record_tablet_found_up()
        self._start('tidy', put_tablet(self._vision, self._controller, False, self._confirm_sec))

    def _release(self, now: float, explore, forage_bias: float):
        watched_for = now - self._opened_at
        if not self._releasing:
            seen_for = now - max(self._opened_at, self._state.tablet_readable_at)
            bored = seen_for >= self._watch_min_sec and (
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
                'the tablet has not come down after %d gestures, the fly keeps trying. '
                'Lowering it by hand also works, the screen is what it believes.',
                self._gesture_budget,
            )
        self._start('lower', put_tablet(self._vision, self._controller, False, self._confirm_sec))

    def _start(self, kind: str, gesture):
        self._gesture = (kind, asyncio.create_task(gesture))

    def _collect(self, now: float):
        if self._gesture is None or not self._gesture[1].done():
            return
        kind, task = self._gesture
        self._gesture = None
        getattr(self, f'_after_{kind}')(now, task.result())

    def _after_raise(self, now: float, raised: bool):
        if not raised:
            _log.warning('the tablet did not come up on screen, the camera pull is dropped')
            self._telemetry.record_raise_missed()
            self.ready_at = now + self._retry_sec
            return
        self.is_open = True
        self._state.camera_open = True
        self._opened_at = now
        self._cap_at = now + self._watch_max_sec
        self._tablet.on_raise(now)

    def _after_lower(self, now: float, lowered: bool):
        self._attempts += 1
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

    def _after_tidy(self, now: float, lowered: bool):
        if not lowered:
            self._retry_at = now + self._retry_sec

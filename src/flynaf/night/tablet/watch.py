import logging

from flynaf import config
from flynaf.night.state import SensoryState
from flynaf.night.tablet.gaze import TabletGaze

_log = logging.getLogger(__name__)


def build_gaze(params=None) -> TabletGaze:
    params = params or config.TABLET_VISION
    return TabletGaze(
        params.cameras, params.first_camera, params.raise_settle_sec, params.switch_settle_sec,
    )


class TabletWatch:
    def __init__(self, gaze: TabletGaze, feed, controller, telemetry, state: SensoryState,
                 map_ready_sec: float | None = None):
        self._gaze = gaze
        self._map_ready_sec = (
            config.TABLET_VISION.map_ready_sec if map_ready_sec is None else map_ready_sec
        )
        self._feed = feed
        self._controller = controller
        self._telemetry = telemetry
        self._state = state

    @property
    def camera(self) -> str | None:
        return self._gaze.camera

    def on_raise(self, now: float):
        self._feed.activate()
        self._show(self._gaze.on_raised(now), 'raise', self._map_ready_sec)

    def on_lower(self):
        self._gaze.on_lowered()
        self._feed.deactivate()
        self._state.tablet_camera = None
        self._state.tablet_drive = {}

    def update(self, now: float, explore_fired: bool, escape_fired: dict) -> str | None:
        if self._gaze.camera is None:
            return None
        switched = self._gaze.pursue(now, explore_fired)
        if switched is not None:
            _log.info('DNp09 fired while watching, gaze follows to camera %s', switched)
            self._show(switched, 'pursuit', 0.0)
        for side in ('left', 'right'):
            if escape_fired.get(side):
                return side
        return None

    def _show(self, camera: str, cause: str, settle_sec: float):
        self._controller.select_camera(camera, settle_sec)
        self._state.tablet_camera = camera
        self._state.tablet_readable_at = self._gaze.readable_at
        self._telemetry.record_camera_view(camera, cause)


class IdleTablet:
    camera = None

    def on_raise(self, now: float):
        return None

    def on_lower(self):
        return None

    def update(self, now: float, explore_fired: bool, escape_fired: dict) -> str | None:
        return None

import logging

from flynaf import config
from flynaf.night.state import SensoryState
from flynaf.night.tablet.gaze import TabletGaze
from flynaf.night.tablet.memory import ObjectMemory

_log = logging.getLogger(__name__)


def build_gaze(params=None) -> TabletGaze:
    params = params or config.TABLET_VISION
    return TabletGaze(params.cameras, params.first_camera, params.raise_settle_sec)


def build_memory(params=None) -> ObjectMemory:
    params = params or config.TABLET_VISION
    return ObjectMemory(params.object_memory_sec)


class TabletWatch:
    def __init__(self, gaze: TabletGaze, feed, controller, telemetry, state: SensoryState,
                 memory: ObjectMemory | None = None, map_ready_sec: float | None = None):
        self._gaze = gaze
        self._memory = memory or build_memory()
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
        self._show(self._gaze.on_raised(now), self._map_ready_sec)

    def on_lower(self):
        self._gaze.on_lowered()
        self._feed.deactivate()
        self._state.tablet_camera = None
        self._state.tablet_drive = {}

    def update(self, now: float, explore_fired: bool, escape_fired: dict) -> str | None:
        if self._gaze.camera is None:
            return None
        pursued = self._gaze.pursued(now, explore_fired)
        if pursued is not None:
            self._remember(pursued, now)
        for side in ('left', 'right'):
            if escape_fired.get(side):
                return side
        return None

    def _remember(self, spec, now: float):
        strength = self._state.tablet_drive.get(f'figure_{spec.side}', 0.0)
        fresh = self._memory.level(now, spec.side) == 0.0
        if self._memory.remember(spec.side, strength, now) and fresh:
            _log.info('DNp09 fired on camera %s, the figure is remembered on the %s at %.2f',
                      spec.name, spec.side, strength)
            self._telemetry.record_figure_remembered(spec.name, spec.side, strength)

    def _show(self, camera: str, settle_sec: float):
        self._controller.select_camera(camera, settle_sec)
        self._state.tablet_camera = camera
        self._state.tablet_readable_at = self._gaze.readable_at
        self._telemetry.record_camera_view(camera)


class IdleTablet:
    camera = None

    def on_raise(self, now: float):
        return None

    def on_lower(self):
        return None

    def update(self, now: float, explore_fired: bool, escape_fired: dict) -> str | None:
        return None

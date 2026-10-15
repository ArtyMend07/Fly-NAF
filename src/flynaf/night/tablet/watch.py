import logging

from flynaf import config
from flynaf.night.memory import Memories
from flynaf.night.state import SensoryState
from flynaf.night.tablet.gaze import TabletGaze, watched_cameras

_log = logging.getLogger(__name__)


def build_gaze(params=None) -> TabletGaze:
    params = params or config.TABLET_VISION
    return TabletGaze(watched_cameras(params), params.first_camera, params.raise_settle_sec)


class TabletWatch:
    def __init__(self, gaze: TabletGaze, feed, controller, telemetry, state: SensoryState,
                 memories: Memories | None = None, map_ready_sec: float | None = None):
        self._gaze = gaze
        self._memories = memories or Memories()
        self._map_ready_sec = (
            config.TABLET_VISION.map_ready_sec if map_ready_sec is None else map_ready_sec
        )
        self._feed = feed
        self._controller = controller
        self._telemetry = telemetry
        self._state = state
        self._counted = 0.0

    @property
    def camera(self) -> str | None:
        return self._gaze.camera

    def on_raise(self, now: float):
        self._feed.activate()
        self._counted = 0.0
        self._show(self._gaze.on_raised(now, self._state.gaze_side), self._map_ready_sec)

    def on_lower(self):
        self._gaze.on_lowered()
        self._feed.deactivate()
        self._state.tablet_camera = None
        self._state.tablet_drive = {}

    def update(self, now: float, explore_fired: bool, escape_fired: dict) -> str | None:
        if self._gaze.camera is None:
            return None
        self._notice(now, explore_fired)
        for side in ('left', 'right'):
            if escape_fired.get(side):
                return side
        return None

    def _notice(self, now: float, explore_fired: bool):
        spec = self._gaze.pursued(now, explore_fired)
        if spec is None:
            return
        strength = self._state.tablet_drive.get(f'figure_{spec.side}', 0.0)
        if strength > self._counted:
            self._count_the_threat(spec, strength, now)

    def _count_the_threat(self, spec, strength: float, now: float):
        first_of_this_view = self._counted == 0.0
        level = self._memories.defence.threat(spec.side, strength - self._counted, now)
        self._counted = strength
        if not first_of_this_view:
            return
        _log.info('DNp09 fired on camera %s, the figure raises the defensive state on the %s to %.2f',
                  spec.name, spec.side, level)
        self._telemetry.record_figure_remembered(spec.name, spec.side, level)

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

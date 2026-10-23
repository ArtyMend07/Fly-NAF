import logging
from dataclasses import dataclass

from flynaf import config
from flynaf.night.memory import Memories
from flynaf.night.state import SensoryState
from flynaf.night.tablet.gaze import TabletGaze, watched_cameras

_log = logging.getLogger(__name__)

SIDES = ('left', 'right')


def build_gaze(params=None) -> TabletGaze:
    params = params or config.TABLET_VISION
    return TabletGaze(watched_cameras(params), params.first_camera, params.raise_settle_sec,
                      params.switch_settle_sec)


@dataclass(frozen=True)
class FinishedView:
    side: str
    found: bool


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
        self._source = None
        self._source_readable_at = 0.0
        self._counted = 0.0
        self._loom = 0.0
        self._read = self._escaped = False
        self.finished_views = 0
        self.last_view: FinishedView | None = None

    @property
    def camera(self) -> str | None:
        return self._gaze.camera

    @property
    def source(self) -> str | None:
        return self._source if self._gaze.camera is not None else None

    @property
    def side(self) -> str | None:
        spec = self._gaze.spec(self.source) if self.source else None
        return spec.side if spec else None

    def on_raise(self, now: float):
        self._feed.activate()
        self._counted = self._loom = 0.0
        self._read = self._escaped = False
        self._source = self._gaze.on_raised(now, self._state.gaze_side)
        self._source_readable_at = self._gaze.readable_at
        self._show(self._source, self._map_ready_sec)
        self._telemetry.record_camera_view(self._source)

    def on_lower(self, now: float):
        self._finish_the_view(now)
        if self._gaze.camera not in (None, self._source):
            self._controller.select_camera(self._source, 0.0)
        self._gaze.on_lowered()
        self._feed.deactivate()
        self._state.tablet_camera = None
        self._state.tablet_drive = {}

    def update(self, now: float, explore_fired: dict, escape_fired: dict) -> str | None:
        if self._gaze.camera is None:
            return None
        self._sense(now)
        self._notice(now, explore_fired)
        self._pursue(now, explore_fired)
        for side in SIDES:
            if escape_fired.get(side):
                self._escaped = self._escaped or side == self.side
                self._remember_the_escape(side, now)
                return side
        return None

    def _sense(self, now: float):
        drive = self._state.tablet_drive
        if self._gaze.camera != self._source or not drive or not self._gaze.readable(now):
            return
        self._read = True
        self._loom = drive.get(f'loom_size_{self.side}', 0.0)

    def _remember_the_escape(self, side: str, now: float):
        own = side == self.side
        loom = self._state.tablet_drive.get(f'loom_size_{side}', 0.0) or (self._loom if own else 0.0)
        if loom <= 0.0:
            return
        level = self._memories.defence.threat(side, loom, now)
        _log.info('DNp04 %s answered something large on camera %s, defensive state at %.2f',
                  side, self._source if own else self._gaze.camera, level)

    def _notice(self, now: float, explore_fired: dict):
        answered = [side for side, fired in explore_fired.items() if fired]
        spec = self._gaze.pursued(now, bool(answered))
        if spec is None:
            return
        for side in answered:
            strength = self._state.tablet_drive.get(f'figure_{side}', 0.0)
            if strength > self._counted:
                self._count_the_figure(spec, side, strength, now)

    def _pursue(self, now: float, explore_fired: dict):
        spec = self._gaze.spec()
        if spec is None or spec.pursue_to is None or not self._gaze.readable(now):
            return
        if not explore_fired.get(spec.side) or not self._state.door_closed[spec.side] or self._loom <= 0.0:
            return
        camera = self._gaze.follow(now)
        self._show(camera, 0.0)
        _log.info('DNp09 %s fired on camera %s behind the shut %s door, following to camera %s',
                  spec.side, spec.name, spec.side, camera)
        self._telemetry.record_pursuit(spec.side, spec.name, camera)

    def _count_the_figure(self, spec, side: str, strength: float, now: float):
        first_of_this_view = self._counted == 0.0
        added = strength - self._counted
        self._counted = strength
        vigilance = self._memories.vigilance.sighted(side, added, now)
        if not first_of_this_view:
            return
        _log.info('DNp09 %s fired on camera %s, vigilance on the %s at %.2f',
                  side, spec.name, side, vigilance)
        self._telemetry.record_figure_remembered(spec.name, side, vigilance)

    def _finish_the_view(self, now: float):
        spec = self._gaze.spec(self._source)
        if spec is None or now < self._source_readable_at:
            return
        self.last_view = FinishedView(spec.side, self._counted > 0.0 or self._escaped)
        self.finished_views += 1
        if self._read and not self._escaped:
            self._state.view_cleared_at[spec.name] = now

    def _show(self, camera: str, settle_sec: float):
        self._controller.select_camera(camera, settle_sec)
        self._state.tablet_camera = camera
        self._state.tablet_readable_at = self._gaze.readable_at


class IdleTablet:
    camera = None
    source = None
    side = None
    finished_views = 0
    last_view = None

    def on_raise(self, now: float):
        return None

    def on_lower(self, now: float):
        return None

    def update(self, now: float, explore_fired: dict, escape_fired: dict) -> str | None:
        return None

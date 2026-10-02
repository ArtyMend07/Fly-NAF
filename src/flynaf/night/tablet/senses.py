from flynaf import config
from flynaf.night.state import SensoryState
from flynaf.night.tablet.transduction import LoomChannel, camera_drive, figure_level


class TabletSenses:
    def __init__(self, feed, params=None):
        self._p = params or config.TABLET_VISION
        self._feed = feed
        self._cameras = {camera.name: camera for camera in self._p.cameras}
        self._loom = LoomChannel(
            self._p.loom_span_mse, self._p.loom_speed_span_mse_per_sec, self._p.loom_speed_decay_sec,
        )
        self._watching = None

    def read(self, state: SensoryState, now: float) -> dict:
        camera = state.tablet_camera if state.camera_open else None
        if camera != self._watching:
            self._watching = camera
            self._loom.reset()
        spec = self._cameras.get(camera)
        if spec is None or now < state.tablet_readable_at:
            return {}
        contrast = self._feed.contrast(camera)
        if contrast is None:
            return {}
        return camera_drive(spec.channel, spec.side, self._levels(spec, contrast, now))

    def _levels(self, spec, contrast: float, now: float) -> dict:
        noise = self._feed.noise(spec.name)
        if spec.channel == 'figure':
            return {'figure': figure_level(contrast, noise, self._p.figure_span_mse)}
        size, speed = self._loom.update(contrast, noise, now)
        return {'size': size, 'speed': speed}


class BlindSenses:
    def read(self, state: SensoryState, now: float) -> dict:
        return {}

from flynaf import config
from flynaf.night.state import SensoryState
from flynaf.night.tablet.transduction import figure_level, loom_level


class TabletSenses:
    def __init__(self, feed, params=None):
        self._p = params or config.TABLET_VISION
        self._feed = feed
        self._cameras = {camera.name: camera for camera in self._p.cameras}

    def read(self, state: SensoryState, now: float) -> dict:
        camera = state.tablet_camera if state.camera_open and state.tablet_seen else None
        spec = self._cameras.get(camera)
        if spec is None or now < state.tablet_readable_at:
            return {}
        reading = self._feed.reading(camera)
        if reading is None:
            return {}
        return transduce(spec, reading, self._feed.noise(camera))


def transduce(spec, reading, noise: float) -> dict:
    side = spec.side
    if reading.share >= spec.wide_field_share:
        return {f'wide_field_{side}': 1.0}
    drive = {f'figure_{side}': figure_level(reading.contrast, noise, spec.figure_span_mse)}
    loom = loom_level(reading.share, spec.loom_share_floor, spec.loom_share_span) if spec.defensive else 0.0
    if loom > 0.0:
        drive[f'loom_size_{side}'] = loom
        drive[f'loom_speed_{side}'] = loom
    return drive


class BlindSenses:
    def read(self, state: SensoryState, now: float) -> dict:
        return {}

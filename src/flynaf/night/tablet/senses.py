from flynaf import config
from flynaf.night.state import SensoryState
from flynaf.night.tablet.transduction import figure_level


class TabletSenses:
    def __init__(self, feed, memory=None, params=None):
        self._p = params or config.TABLET_VISION
        self._feed = feed
        self._memory = memory
        self._cameras = {camera.name: camera for camera in self._p.cameras}

    def read(self, state: SensoryState, now: float) -> dict:
        remembered = self._memory.drive(now) if self._memory is not None else {}
        return {**remembered, **self._seen(state, now)}

    def _seen(self, state: SensoryState, now: float) -> dict:
        camera = state.tablet_camera if state.camera_open else None
        spec = self._cameras.get(camera)
        if spec is None or now < state.tablet_readable_at:
            return {}
        contrast = self._feed.contrast(camera)
        if contrast is None:
            return {}
        level = figure_level(contrast, self._feed.noise(camera), self._p.figure_span_mse)
        return {f'figure_{spec.side}': level}


class BlindSenses:
    def read(self, state: SensoryState, now: float) -> dict:
        return {}

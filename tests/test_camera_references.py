import asyncio
import dataclasses
import threading
from unittest.mock import patch

import pytest

from flynaf import clock, config
from flynaf.night.tablet import references


class LateTablet:
    def __init__(self, latency_sec: float | None):
        self._latency = latency_sec
        self._up_at = None

    def flip(self):
        if self.is_camera_up():
            self._up_at = None
        elif self._latency is not None:
            self._up_at = clock.now() + self._latency

    def is_camera_up(self) -> bool:
        return self._up_at is not None and clock.now() >= self._up_at

    def is_camera_down(self) -> bool:
        return not self.is_camera_up()


class CountingController:
    def __init__(self, tablet: LateTablet):
        self._tablet = tablet
        self.flips = 0
        self.cameras = []

    def _done(self) -> threading.Event:
        done = threading.Event()
        done.set()
        return done

    def flip_tablet(self) -> threading.Event:
        self.flips += 1
        self._tablet.flip()
        return self._done()

    def select_camera(self, camera: str, settle_sec: float = 0.0) -> threading.Event:
        self.cameras.append(camera)
        return self._done()


class RecordingFeed:
    def activate(self):
        pass

    def deactivate(self):
        pass

    def capture_reference(self, camera: str) -> bool:
        return True


@pytest.fixture(autouse=True)
def quick_confirmations():
    detection = dataclasses.replace(config.CAMERA_DETECTION, flip_confirm_sec=0.1, lower_gesture_attempts=1)
    with patch.object(config, 'CAMERA_DETECTION', detection):
        yield


def _params(patience_sec: float):
    return dataclasses.replace(
        config.TABLET_VISION, start_raise_patience_sec=patience_sec, switch_settle_sec=0.0,
    )


@pytest.mark.parametrize('latency_sec, patience_sec, recorded', [
    (0.0, 0.3, True),
    (0.25, 0.5, True),
    (None, 0.2, False),
])
def test_a_tablet_that_comes_up_late_at_night_start_is_waited_for_and_never_flipped_twice(
    latency_sec, patience_sec, recorded,
):
    tablet = LateTablet(latency_sec)
    controller = CountingController(tablet)
    result = asyncio.run(references.capture_camera_references(
        RecordingFeed(), controller, tablet, _params(patience_sec),
    ))
    assert result is recorded
    assert controller.cameras == (['1C'] if recorded else [])
    raise_gestures = 1
    lower_gestures = 1 if recorded else 0
    assert controller.flips == raise_gestures + lower_gestures

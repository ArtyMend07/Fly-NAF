import asyncio
import dataclasses
import threading
from unittest.mock import patch

import pytest

from flynaf import clock, config
from flynaf.night.tablet import references


class LateTablet:
    def __init__(self, latency_sec: float | None, ignored_flips: int = 0):
        self._latency = latency_sec
        self._ignored = ignored_flips
        self._up_at = None

    def flip(self):
        if self._ignored:
            self._ignored -= 1
            return
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
    def __init__(self, on_disk=()):
        self.on_disk = set(on_disk)
        self.saved = []

    def activate(self):
        pass

    def deactivate(self):
        pass

    def capture_reference(self, camera: str) -> bool:
        return True

    def load_reference(self, camera: str, folder: str) -> bool:
        return camera in self.on_disk

    def save_reference(self, camera: str, folder: str):
        self.saved.append(camera)


@pytest.fixture(autouse=True)
def quick_confirmations():
    detection = dataclasses.replace(config.CAMERA_DETECTION, flip_confirm_sec=0.1, lower_gesture_attempts=1)
    with patch.object(config, 'CAMERA_DETECTION', detection):
        yield


ATTEMPTS = 3
FOLDER = 'unused'


def _params(patience_sec: float):
    return dataclasses.replace(
        config.TABLET_VISION, start_raise_patience_sec=patience_sec, switch_settle_sec=0.0,
        start_raise_attempts=ATTEMPTS,
    )


@pytest.mark.parametrize('latency_sec, patience_sec, ignored_flips, raise_gestures', [
    (0.0, 0.3, 0, 1),
    (0.25, 0.5, 0, 1),
    (0.0, 0.2, 1, 2),
    (0.0, 0.2, 2, 3),
])
def test_a_tablet_that_comes_up_late_or_only_once_the_night_opens_is_recorded(
    latency_sec, patience_sec, ignored_flips, raise_gestures,
):
    tablet = LateTablet(latency_sec, ignored_flips)
    controller = CountingController(tablet)
    result = asyncio.run(references.capture_camera_references(
        RecordingFeed(), controller, tablet, _params(patience_sec), FOLDER,
    ))
    assert result is True
    assert controller.cameras == ['1C', '4B']
    lower_gestures = 1
    assert controller.flips == raise_gestures + lower_gestures


@pytest.mark.parametrize('on_disk, recorded, flips', [
    (('1C', '4B'), [], 0),
    (('1C',), ['4B'], 2),
    ((), ['1C', '4B'], 2),
])
def test_only_the_cameras_missing_from_disk_raise_the_tablet_and_get_saved(on_disk, recorded, flips):
    tablet = LateTablet(0.0)
    controller = CountingController(tablet)
    feed = RecordingFeed(on_disk)
    assert asyncio.run(references.capture_camera_references(
        feed, controller, tablet, _params(0.3), FOLDER,
    )) is True
    assert controller.cameras == recorded
    assert feed.saved == recorded
    assert controller.flips == flips


def test_a_tablet_that_never_comes_up_is_tried_a_few_times_and_never_flipped_while_rising():
    tablet = LateTablet(None)
    controller = CountingController(tablet)
    result = asyncio.run(references.capture_camera_references(
        RecordingFeed(), controller, tablet, _params(0.2), FOLDER,
    ))
    assert result is False
    assert controller.cameras == []
    assert controller.flips == ATTEMPTS

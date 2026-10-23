from unittest.mock import patch

import cv2
import numpy as np
import pytest

from flynaf import config
from flynaf.env import tablet_feed
from flynaf.env.tablet_feed import Reading, feed_size
from flynaf.night.tablet.senses import new_share, transduce

COVE = next(camera for camera in config.TABLET_VISION.cameras if camera.name == '1C')


def scene(seed: int = 3) -> np.ndarray:
    rng = np.random.default_rng(seed)
    width, height = feed_size()
    texture = cv2.GaussianBlur(rng.uniform(0, 10, (height, width)).astype(np.float32), (9, 9), 0)
    return 60.0 + texture


def with_block(frame: np.ndarray, left: int, width: int, level: float = 240.0) -> np.ndarray:
    changed = frame.copy()
    changed[10:-10, left:left + width] = level
    return changed


def jittered(frame: np.ndarray, seed: int) -> np.ndarray:
    return frame + np.random.default_rng(seed).normal(0.0, 1.0, frame.shape).astype(np.float32)


def feed_with_reference(tmp_path, curtain: np.ndarray) -> tablet_feed.TabletFeed:
    for index in range(3):
        cv2.imwrite(str(tmp_path / f'1C_{index:02d}.png'), np.clip(jittered(curtain, index), 0, 255).astype(np.uint8))
    with patch.object(tablet_feed.threading, 'Thread'):
        feed = tablet_feed.TabletFeed()
    assert feed.load_reference('1C', str(tmp_path))
    return feed


def look(feed: tablet_feed.TabletFeed, frame: np.ndarray, seed: int) -> Reading:
    feed.reading('1C')
    feed._read('1C', jittered(frame, seed))
    reading = feed.reading('1C')
    feed.deactivate()
    return reading


@pytest.mark.parametrize('share, since, expected', [(0.4, None, 0.4), (0.4, 0.05, 0.05), (0.1, 0.6, 0.1)])
def test_only_what_changed_both_from_the_reference_and_since_the_last_look_is_new(share, since, expected):
    assert new_share(Reading(1000.0, share, since)) == expected


def test_a_figure_that_has_not_moved_since_the_last_look_stops_looming(tmp_path):
    """Foxy stood out of the curtain for two minutes on the night 3 of
    2026-10-21, and every look renewed the door hold as if he had just come
    out."""
    curtain = scene()
    out = with_block(curtain, 20, 60)
    feed = feed_with_reference(tmp_path, curtain)
    first, second = look(feed, out, 10), look(feed, out, 11)
    noise = feed.noise('1C')
    assert first.share_since_last_look is None
    assert transduce(COVE, first, noise).get('loom_size_left', 0.0) > 0.0
    assert transduce(COVE, second, noise).get('loom_size_left', 0.0) == 0.0
    assert transduce(COVE, second, noise)['figure_left'] > 0.0


def test_a_figure_that_leaves_between_two_looks_looms_again(tmp_path):
    curtain = scene()
    out, gone = with_block(curtain, 20, 60), with_block(curtain, 20, 60, level=10.0)
    feed = feed_with_reference(tmp_path, curtain)
    look(feed, out, 10)
    after = look(feed, gone, 11)
    assert transduce(COVE, after, feed.noise('1C')).get('loom_size_left', 0.0) > 0.0


def test_a_look_is_remembered_only_from_the_frames_the_senses_read(tmp_path):
    """The switching static and the camera left on screen by the last look are
    on the tablet before the view is readable, and they are not the cove."""
    curtain = scene()
    feed = feed_with_reference(tmp_path, curtain)
    feed._read('1C', jittered(with_block(curtain, 20, 60), 1))
    feed.deactivate()
    first = look(feed, curtain, 2)
    assert first.share_since_last_look is None

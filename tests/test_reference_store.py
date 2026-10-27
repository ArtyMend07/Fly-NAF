import os
import tempfile

import numpy as np
import pytest
from test_vision_reference_cache import filled, make_vision

from flynaf import config
from flynaf.env import anchor, reference_store
from flynaf.env.tablet_feed import TabletFeed, feed_size, view_mask


@pytest.fixture
def anchored_at():
    def place(rect):
        anchor.set_game_rect(rect)
    yield place
    anchor.set_game_rect(None)


def test_each_window_size_keeps_its_own_folder_wherever_the_window_sits(anchored_at):
    with tempfile.TemporaryDirectory() as root:
        anchored_at((0, 0, 1280, 720))
        first = reference_store.layout_folder('eye', root)
        anchored_at((640, 300, 1280, 720))
        moved = reference_store.layout_folder('eye', root)
        anchored_at((0, 0, 1920, 1080))
        bigger = reference_store.layout_folder('eye', root)
    assert first == moved
    assert first != bigger
    assert first.endswith(os.path.join('1280x720', 'eye'))


def test_moving_the_window_keeps_the_eye_references(anchored_at):
    with tempfile.TemporaryDirectory() as tmp:
        anchored_at((115, 169, 1280, 720))
        filled(make_vision(tmp)).save_reference_to_disk()
        anchored_at((8, 197, 1280, 720))
        assert make_vision(tmp).load_reference_from_disk() is True


def test_a_new_calibration_puts_the_previous_one_aside_instead_of_overwriting_it():
    with tempfile.TemporaryDirectory() as root:
        folder = os.path.join(root, 'eye')
        os.makedirs(folder)
        filled(make_vision(folder)).save_reference_to_disk()
        filled(make_vision(folder)).save_reference_to_disk()
        archived = os.listdir(os.path.join(root, reference_store.ARCHIVE))
        assert len(archived) == 1
        assert 'banks.json' in os.listdir(os.path.join(root, reference_store.ARCHIVE, archived[0]))
        assert make_vision(folder).load_reference_from_disk() is True


def _feed() -> TabletFeed:
    feed = TabletFeed.__new__(TabletFeed)
    feed._p = config.TABLET_VISION
    feed._size = feed_size(feed._p)
    feed._mask = view_mask(feed._p)
    feed._banks, feed._noise = {}, {}
    return feed


def test_a_camera_bank_survives_the_disk_and_keeps_its_noise_floor():
    width, height = feed_size()
    rng = np.random.default_rng(4)
    bank = [rng.integers(0, 255, (height, width)).astype(np.float32) for _ in range(5)]
    writer = _feed()
    writer._keep('4B', bank)
    with tempfile.TemporaryDirectory() as folder:
        writer.save_reference('4B', folder)
        reader = _feed()
        assert reader.load_reference('4B', folder) is True
        assert reader.load_reference('1C', folder) is False
    assert reader.noise('4B') == pytest.approx(writer.noise('4B'))
    assert all(np.array_equal(a, b) for a, b in zip(writer._banks['4B'], reader._banks['4B']))

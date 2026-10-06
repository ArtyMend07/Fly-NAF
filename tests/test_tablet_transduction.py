import cv2
import numpy as np

from flynaf import config
from flynaf.env.tablet_feed import (
    bank_distance,
    bank_noise,
    feed_size,
    prepare,
    spread_sample,
    view_mask,
)
from flynaf.night.tablet.transduction import figure_level

FIGURE_CASES = (
    (0.0, 100.0, 1000.0, 0.0),
    (100.0, 100.0, 1000.0, 0.0),
    (600.0, 100.0, 1000.0, 0.5),
    (5000.0, 100.0, 1000.0, 1.0),
    (50.0, 100.0, 1000.0, 0.0),
)


def test_figure_level_is_the_contrast_above_noise_over_the_span():
    for contrast, noise, span, expected in FIGURE_CASES:
        assert abs(figure_level(contrast, noise, span) - expected) < 1e-9, (contrast, noise)


def _scene(seed: int = 3) -> np.ndarray:
    rng = np.random.default_rng(seed)
    width, height = feed_size()
    return cv2.GaussianBlur(rng.uniform(0, 120, (height, width)).astype(np.float32), (5, 5), 0)


def _panned(scene: np.ndarray, columns: int) -> np.ndarray:
    return np.roll(scene, columns, axis=1)


def test_bank_distance_takes_the_nearest_reference():
    left = np.zeros((10, 10), np.float32)
    right = np.full((10, 10), 50.0, np.float32)
    assert bank_distance(right, [left, right]) == 0.0
    assert bank_distance(np.full((10, 10), 45.0, np.float32), [left, right]) == 25.0
    assert bank_distance(left, []) == 0.0


def test_the_camera_pan_is_aligned_away_before_comparing():
    scene = _scene()
    bank = [scene[:, 20:60]]
    for columns in (-12, -5, 0, 7, 15):
        assert bank_distance(_panned(scene, columns)[:, 20:60], bank) < 1.0, columns


def test_a_small_object_stands_out_instead_of_being_diluted_by_the_frame():
    scene = _scene()
    figure = scene.copy()
    figure[5:12, 30:37] = 255.0
    whole_frame_mse = float(np.mean((figure - scene) ** 2))
    assert bank_distance(figure, [scene]) > 10 * whole_frame_mse


def test_changes_under_the_hud_mask_are_ignored():
    scene = _scene()
    clock_changed = scene.copy()
    clock_changed[:10, 60:] = 255.0
    mask = np.ones(scene.shape, bool)
    mask[:10, 60:] = False
    assert bank_distance(clock_changed, [scene], mask) < 1.0
    assert bank_distance(clock_changed, [scene]) > 100.0


def test_bank_noise_is_the_worst_leave_one_out_distance():
    frames = [np.full((10, 10), value, np.float32) for value in (0.0, 1.0, 3.0)]
    assert bank_noise(frames) == 4.0
    assert bank_noise(frames[:1]) == 0.0


def test_the_view_mask_hides_the_camera_map_and_keeps_the_middle_of_the_feed():
    mask = view_mask()
    width, height = feed_size()
    assert mask.shape == (height, width)
    left, top, right, bottom = config.TABLET_VISION.view
    scale = config.TABLET_VISION.view_scale
    assert not mask[(400 - top) // scale, (1000 - left) // scale]
    assert mask[(200 - top) // scale, (900 - left) // scale]
    assert mask[(330 - top) // scale, (470 - left) // scale]


def test_spread_sample_keeps_the_whole_sweep():
    assert spread_sample(list(range(10)), 20) == list(range(10))
    assert spread_sample(list(range(100)), 4) == [0, 25, 50, 75]


def test_prepare_shrinks_colour_frames_to_the_feed_size():
    frame = np.random.default_rng(1).integers(0, 255, (120, 200, 4), dtype=np.uint8)
    patch = prepare(frame, (50, 30))
    assert patch.shape == (30, 50)
    assert patch.dtype == np.float32


if __name__ == '__main__':
    for name, fn in sorted(globals().items()):
        if name.startswith('test_'):
            fn()
    print('ok')

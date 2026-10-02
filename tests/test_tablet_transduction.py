import numpy as np

from flynaf.env.tablet_feed import bank_distance, bank_noise, prepare, spread_sample
from flynaf.night.tablet.transduction import LoomChannel, camera_drive, figure_level

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


def _loom() -> LoomChannel:
    return LoomChannel(size_span=1000.0, speed_span_per_sec=3000.0, speed_decay_sec=0.3)


def test_a_growing_shape_drives_speed_and_a_standing_one_only_size():
    loom = _loom()
    loom.update(0.0, 0.0, now=0.0)
    size, speed = loom.update(600.0, 0.0, now=0.1)
    assert size == 0.6
    assert speed > 0.9

    for step in range(2, 20):
        size, speed = loom.update(600.0, 0.0, now=step * 0.1)
    assert size == 0.6
    assert speed < 0.01


def test_speed_is_held_briefly_so_a_slow_engine_frame_can_still_read_it():
    loom = _loom()
    loom.update(0.0, 0.0, now=0.0)
    _, peak = loom.update(900.0, 0.0, now=0.05)
    _, after = loom.update(900.0, 0.0, now=0.10)
    assert 0.0 < after < peak


def test_a_shape_that_shrinks_is_not_looming():
    loom = _loom()
    loom.update(900.0, 0.0, now=0.0)
    _, speed = loom.update(100.0, 0.0, now=0.1)
    assert speed == 0.0


def test_reset_forgets_the_previous_camera():
    loom = _loom()
    loom.update(0.0, 0.0, now=0.0)
    loom.update(900.0, 0.0, now=0.1)
    loom.reset()
    _, speed = loom.update(900.0, 0.0, now=0.2)
    assert speed == 0.0


DRIVE_CASES = (
    ('figure', 'left', {'figure': 0.4}, {'figure_left': 0.4}),
    ('loom', 'left', {'size': 0.2, 'speed': 0.7}, {'loom_size_left': 0.2, 'loom_speed_left': 0.7}),
    ('loom', 'right', {}, {'loom_size_right': 0.0, 'loom_speed_right': 0.0}),
)


def test_camera_drive_names_the_population_on_the_camera_side():
    for channel, side, levels, expected in DRIVE_CASES:
        assert camera_drive(channel, side, levels) == expected, (channel, side)


def test_bank_distance_takes_the_nearest_reference_so_panning_is_not_a_threat():
    left = np.zeros((8, 8), np.float32)
    right = np.full((8, 8), 50.0, np.float32)
    assert bank_distance(right, [left, right]) == 0.0
    assert bank_distance(np.full((8, 8), 45.0, np.float32), [left, right]) == 25.0
    assert bank_distance(left, []) == 0.0


def test_bank_noise_is_the_worst_leave_one_out_distance():
    frames = [np.full((4, 4), value, np.float32) for value in (0.0, 1.0, 3.0)]
    assert bank_noise(frames) == 4.0
    assert bank_noise(frames[:1]) == 0.0


def test_spread_sample_keeps_the_whole_sweep():
    assert spread_sample(list(range(10)), 20) == list(range(10))
    assert spread_sample(list(range(100)), 4) == [0, 25, 50, 75]


def test_prepare_shrinks_colour_frames_to_a_square_grey_patch():
    frame = np.random.default_rng(1).integers(0, 255, (120, 120, 4), dtype=np.uint8)
    patch = prepare(frame, 32)
    assert patch.shape == (32, 32)
    assert patch.dtype == np.float32


if __name__ == '__main__':
    for name, fn in sorted(globals().items()):
        if name.startswith('test_'):
            fn()
    print('ok')

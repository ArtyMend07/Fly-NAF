import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import config
from env.overlay import (
    capture_regions,
    centered_rect,
    game_bounds,
    ingame_overlay_rect,
    motor_regions,
    pick_overlay_position,
    rects_overlap,
)

EDGE_MIN_WIDTH = 265


def test_rects_overlap_detects_intersection_and_separation():
    cases = [
        ((0, 0, 10, 10), (5, 5, 15, 15), True),
        ((0, 0, 10, 10), (10, 0, 20, 10), False),
        ((0, 0, 10, 10), (0, 10, 10, 20), False),
        ((0, 0, 100, 100), (40, 40, 50, 50), True),
        ((0, 0, 10, 10), (11, 11, 20, 20), False),
    ]
    for a, b, expected in cases:
        assert rects_overlap(a, b) is expected
        assert rects_overlap(b, a) is expected


def test_centered_rect_matches_vision_bbox_convention():
    assert centered_rect(100, 100, 50) == (75, 75, 125, 125)


def test_picked_position_never_overlaps_any_capture_region():
    forbidden = capture_regions()
    position = pick_overlay_position(1920, 1080, 300, 352, forbidden)

    assert position is not None
    x, y = position
    panel = (x, y, x + 300, y + 352)
    for region in forbidden:
        assert not rects_overlap(panel, region)


def test_position_stays_inside_the_screen():
    position = pick_overlay_position(1920, 1080, 300, 352, capture_regions())
    x, y = position

    assert 0 <= x and x + 300 <= 1920
    assert 0 <= y and y + 352 <= 1080


def test_returns_none_when_every_candidate_is_covered():
    everything = [(0, 0, 1920, 1080)]
    assert pick_overlay_position(1920, 1080, 300, 352, everything) is None


def test_panel_larger_than_screen_returns_none():
    assert pick_overlay_position(320, 240, 800, 600, []) is None


def test_real_config_regions_leave_room_on_this_layout():
    regions = capture_regions()
    vision = config.VISION_CALIBRATION

    assert len(regions) == 3
    assert regions[0] == centered_rect(
        vision.left_target_x, vision.left_target_y, vision.left_bbox_size
    )


def test_ingame_overlay_clears_every_capture_and_motor_region():
    params = config.BRAIN_VIEW
    position = ingame_overlay_rect(params.ingame_width, params.ingame_height, params.ingame_margin)

    assert position is not None
    x, y = position
    panel = (x, y, x + params.ingame_width, y + params.ingame_height)
    for region in capture_regions() + motor_regions():
        assert not rects_overlap(panel, region)


def test_ingame_panel_is_wide_enough_for_the_browser_to_honour_it():
    """Edge clamps an app window to 265 pixels wide. Asking for less silently
    gives back a wider window, which then sits over a capture region."""
    assert config.BRAIN_VIEW.ingame_width >= EDGE_MIN_WIDTH


def test_ingame_overlay_stays_inside_the_game_area():
    params = config.BRAIN_VIEW
    left, _top, right, bottom = game_bounds()
    x, y = ingame_overlay_rect(params.ingame_width, params.ingame_height, params.ingame_margin)

    assert x >= left
    assert x + params.ingame_width <= right
    assert y + params.ingame_height <= bottom


def test_ingame_overlay_returns_none_when_the_panel_cannot_fit():
    left, _top, right, _bottom = game_bounds()
    assert ingame_overlay_rect(right - left + 1, 100, margin=1) is None


def test_ingame_overlay_prefers_the_top_of_the_screen():
    params = config.BRAIN_VIEW
    _x, y = ingame_overlay_rect(params.ingame_width, params.ingame_height, params.ingame_margin)

    assert y == params.ingame_margin


if __name__ == '__main__':
    for name, fn in sorted(globals().items()):
        if name.startswith('test_'):
            fn()
    print('ok')

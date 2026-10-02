from unittest.mock import patch

import pytest

from flynaf.env import overlay

CLIENT = (910, 200, 260, 140)
OUTER = (900, 200, 280, 150)


def _frame(page_height):
    with patch.object(overlay.desktop, 'window_rect', return_value=CLIENT), \
            patch.object(overlay.desktop, 'outer_rect', return_value=OUTER):
        return overlay.frame_around_page(1, 900, 200, 280, 150, page_height)


def test_the_title_bar_ends_up_above_the_panel_and_outside_the_clip():
    window, page = _frame(98)

    title_bar = 140 - 98
    top = title_bar + overlay._PAGE_ROUNDING_PX
    assert window == (890, 200 - top, 300, 150 + top + 10)
    assert page == (10, top, 290, top + 150)


def test_the_clip_lands_on_the_requested_rectangle():
    window, page = _frame(98)

    assert (window[0] + page[0], window[1] + page[1]) == (900, 200)
    assert (page[2] - page[0], page[3] - page[1]) == (280, 150)


@pytest.mark.parametrize('page_height', [0, 200])
def test_a_page_height_that_does_not_fit_the_window_is_refused(page_height):
    assert _frame(page_height) is None

from unittest.mock import patch

import pytest

from flynaf.env import overlay

SCREEN_W = 1920
MIN_WIDTH = 420
MARGIN = 8


def dock(client: tuple, outer: tuple):
    moves = []
    with patch.object(overlay, 'find_game_window', return_value=7), \
            patch.object(overlay.desktop, 'window_rect', return_value=client), \
            patch.object(overlay.desktop, 'outer_rect', return_value=outer), \
            patch.object(overlay.desktop, 'move_window',
                         side_effect=lambda handle, x, y: moves.append((handle, x, y)) or True), \
            patch.object(overlay, 'anchor_to_game', return_value=True):
        docked = overlay.dock_game_for_panel(SCREEN_W, MIN_WIDTH, MARGIN)
    return docked, moves


def test_a_centred_game_moves_so_its_picture_starts_at_the_margin():
    docked, moves = dock(client=(208, 190, 1280, 720), outer=(197, 145, 1302, 776))

    assert docked
    assert moves == [(7, MARGIN - 11, 145)]


@pytest.mark.parametrize('client, outer', [
    ((0, 0, 1920, 1080), (0, 0, 1920, 1080)),
    ((100, 100, 1600, 900), (89, 55, 1622, 956)),
])
def test_a_game_too_wide_for_the_panel_stays_where_it_is(client, outer):
    docked, moves = dock(client, outer)

    assert not docked
    assert moves == []

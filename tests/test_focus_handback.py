import os
import sys
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import main

GAME = 4242
PANEL = 99


def _run(game, valid_handles=(GAME,), point_lookup=0, held=True):
    calls = {'held': [], 'lookups': 0}

    def fake_lookup():
        calls['lookups'] += 1
        return point_lookup

    def fake_hold(hwnd, timeout_sec):
        calls['held'].append(hwnd)
        return held

    with patch.object(main, 'find_game_window', side_effect=fake_lookup), \
         patch.object(main, 'hold_foreground', side_effect=fake_hold), \
         patch.object(main, 'is_window', side_effect=lambda h: h in valid_handles), \
         patch.object(main, 'window_title', side_effect=lambda h: f'window {h}'):
        main._restore_game_focus(game, PANEL, timeout_sec=1.0)

    return calls


def test_the_handle_captured_before_the_browser_opened_is_the_one_used():
    """WindowFromPoint cannot see a minimised window, and the game minimises the
    moment the browser takes the foreground. Looking it up after the launch
    therefore finds whatever was behind the game, and the game stays down."""
    calls = _run(GAME)

    assert calls['held'] == [GAME]
    assert calls['lookups'] == 0


def test_a_stale_handle_falls_back_to_looking_under_the_office():
    calls = _run(GAME, valid_handles=(), point_lookup=777)

    assert calls['lookups'] == 1
    assert calls['held'] == [777]


def test_nothing_is_focused_when_neither_route_finds_a_window():
    calls = _run(0, valid_handles=(), point_lookup=0)

    assert calls['held'] == []


def test_the_panel_is_never_handed_the_focus():
    calls = _run(PANEL, valid_handles=(PANEL,), point_lookup=PANEL)

    assert calls['held'] == []


if __name__ == '__main__':
    for name, fn in sorted(globals().items()):
        if name.startswith('test_'):
            fn()
    print('ok')

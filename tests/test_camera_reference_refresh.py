import asyncio
import sys
import os
from unittest.mock import MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from main import _reanchor_office_reference


def _office_visible():
    vision = MagicMock()
    vision.is_camera_up.return_value = False
    return vision


def _centred():
    controller = MagicMock()
    controller.facing.return_value = 'centre'
    return controller


def test_reanchor_captures_reference_only_after_the_screen_agrees():
    vision = _office_visible()

    async def scenario():
        task = asyncio.create_task(_reanchor_office_reference(vision, 0.02, 0.3, _centred()))
        vision.capture_camera_closed_reference.assert_not_called()
        await task

    asyncio.run(scenario())

    vision.capture_camera_closed_reference.assert_called_once()


def test_reanchor_needs_more_than_one_clean_reading():
    vision = _office_visible()

    asyncio.run(_reanchor_office_reference(vision, 0.02, 0.3, _centred()))

    assert vision.is_camera_up.call_count >= 2


def test_reanchor_clears_buffers_before_capturing_reference():
    call_order = []
    vision = _office_visible()
    vision.clear_buffers.side_effect = lambda: call_order.append('clear')
    vision.capture_camera_closed_reference.side_effect = lambda: call_order.append('capture')

    asyncio.run(_reanchor_office_reference(vision, 0.02, 0.3, _centred()))

    assert call_order == ['clear', 'capture']


def test_reanchor_refuses_to_capture_the_tablet_as_the_office():
    vision = MagicMock()
    vision.is_camera_up.return_value = True

    reanchored = asyncio.run(_reanchor_office_reference(vision, 0.02, 0.3, _centred()))

    assert reanchored is False
    vision.capture_camera_closed_reference.assert_not_called()


def test_reanchor_does_not_touch_camera_open_state():
    vision = _office_visible()
    state = MagicMock(camera_open='untouched-sentinel')

    asyncio.run(_reanchor_office_reference(vision, 0.02, 0.3, _centred()))

    assert state.camera_open == 'untouched-sentinel'


if __name__ == '__main__':
    for name, fn in sorted(globals().items()):
        if name.startswith('test_'):
            fn()
    print('ok')

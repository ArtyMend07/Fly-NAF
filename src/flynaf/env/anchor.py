import logging
import threading

_log = logging.getLogger(__name__)

DESIGN_WIDTH = 1280
DESIGN_HEIGHT = 720

_LOCK = threading.Lock()
_RECT = None


def set_game_rect(rect):
    global _RECT
    with _LOCK:
        if rect is None:
            _RECT = None
            return
        x, y, w, h = rect
        if w <= 0 or h <= 0:
            _RECT = None
            return
        _RECT = (int(x), int(y), int(w), int(h))
        _log.info(
            'anchored to the game window at %d,%d sized %dx%d (scale %.3fx%.3f)',
            _RECT[0], _RECT[1], _RECT[2], _RECT[3],
            _RECT[2] / DESIGN_WIDTH, _RECT[3] / DESIGN_HEIGHT,
        )


def game_rect():
    with _LOCK:
        return _RECT


def anchored() -> bool:
    return game_rect() is not None


def _scale() -> tuple:
    rect = game_rect()
    if rect is None:
        return (0, 0, 1.0, 1.0)
    return (rect[0], rect[1], rect[2] / DESIGN_WIDTH, rect[3] / DESIGN_HEIGHT)


def point(x: int, y: int) -> tuple:
    origin_x, origin_y, scale_x, scale_y = _scale()
    return (round(origin_x + x * scale_x), round(origin_y + y * scale_y))


def x(value: int) -> int:
    return point(value, 0)[0]


def y(value: int) -> int:
    return point(0, value)[1]


def size(value: int) -> int:
    _origin_x, _origin_y, scale_x, scale_y = _scale()
    return max(1, round(value * min(scale_x, scale_y)))


def span(value: int) -> int:
    _origin_x, _origin_y, scale_x, _scale_y = _scale()
    return max(1, round(value * scale_x))

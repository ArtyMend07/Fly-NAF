import dataclasses
import logging
import math

import pytest

from flynaf import config
from flynaf.night.memory import DefensiveState, Memories, OrientationMemory, Vigilance
from flynaf.night.state import SensoryState
from flynaf.night.tablet.gaze import TabletGaze, watched_cameras
from flynaf.night.tablet.watch import FinishedView, TabletWatch, build_gaze
from flynaf.telemetry import ConnectomeTelemetry

RAISE = 1.2
NOBODY = {'left': False, 'right': False}

COVE_ONLY = dataclasses.replace(config.TABLET_VISION, watched=('1C',))


def _fired(side: str | None) -> dict:
    return {**NOBODY, side: True} if side else dict(NOBODY)


def _gaze(params=None) -> TabletGaze:
    return TabletGaze(watched_cameras(params or config.TABLET_VISION), '1C', RAISE)


class _Done:
    def wait(self, timeout=None):
        return True


class RecordingController:
    def __init__(self):
        self.selected = []

    def select_camera(self, camera, settle_sec=0.0):
        self.selected.append((camera, settle_sec))
        return _Done()


class RecordingFeed:
    def __init__(self):
        self.active = False

    def activate(self):
        self.active = True

    def deactivate(self):
        self.active = False


def test_a_raise_with_no_leaning_opens_on_the_cove():
    gaze = _gaze()
    assert gaze.on_raised(now=10.0) == '1C'
    assert gaze.readable_at == 10.0 + RAISE
    assert not gaze.readable(10.0)
    assert gaze.readable(10.0 + RAISE)


PURSUIT_CASES = (
    ('no spike', 20.0, False, None),
    ('spike during the raise static', 10.1, True, None),
    ('spike once the cove is readable', 20.0, True, '1C'),
)


def test_pursuit_needs_a_dnp09_spike_on_a_readable_cove():
    for label, now, fired, expected in PURSUIT_CASES:
        gaze = _gaze()
        gaze.on_raised(now=10.0)
        pursued = gaze.pursued(now, fired)
        assert (pursued.name if pursued else None) == expected, label


def test_the_gaze_never_leaves_its_camera_on_its_own():
    gaze = _gaze()
    gaze.on_raised(now=0.0)
    gaze.pursued(5.0, True)
    assert gaze.camera == '1C'


@pytest.mark.parametrize('params, leaning, camera', [
    (COVE_ONLY, 'left', '1C'),
    (COVE_ONLY, 'right', '1C'),
    (config.TABLET_VISION, 'left', '1C'),
    (config.TABLET_VISION, 'right', '4B'),
    (config.TABLET_VISION, None, '1C'),
])
def test_the_tablet_opens_on_the_watched_camera_of_the_side_the_fly_leans_to(params, leaning, camera):
    assert _gaze(params).on_raised(now=0.0, side=leaning) == camera


def test_the_fly_watches_the_cove_and_the_east_hall_corner():
    assert [camera.name for camera in watched_cameras(config.TABLET_VISION)] == ['1C', '4B']
    assert build_gaze().on_raised(now=0.0, side='right') == '4B'
    assert build_gaze(COVE_ONLY).on_raised(now=0.0, side='right') == '1C'


def _watching(figure: float, camera: str = '1C', side: str = 'left'):
    state = SensoryState(camera_open=True, gaze_side=side)
    controller, telemetry = RecordingController(), ConnectomeTelemetry()
    memories = Memories(OrientationMemory(), DefensiveState(4.0), Vigilance(4.0))
    watch = TabletWatch(_gaze(), RecordingFeed(), controller, telemetry, state, memories)
    watch.on_raise(now=0.0)
    state.tablet_drive = {f'figure_{side}': figure}
    assert watch.camera == camera
    return watch, memories, controller, telemetry, state


@pytest.mark.parametrize('camera, side', [('1C', 'left'), ('4B', 'right')])
def test_a_figure_dnp09_answered_alerts_its_side_without_reaching_the_door(camera, side):
    watch, memories, controller, telemetry, _state = _watching(0.6, camera, side)
    watch.update(5.0, explore_fired=_fired(side), escape_fired={})
    assert memories.vigilance.level(5.0, side) == pytest.approx(0.6)
    assert memories.defence.level(5.0, side) == 0.0
    assert memories.orientation.level(5.0, side) == 0.0
    assert controller.selected == [(camera, config.TABLET_VISION.map_ready_sec)]
    assert telemetry.figures_remembered == {camera: 1}


@pytest.mark.parametrize('camera, side, other', [('1C', 'left', 'right'), ('4B', 'right', 'left')])
def test_the_dnp09_across_the_midline_does_not_count_a_figure_on_the_other_side(camera, side, other):
    watch, memories, _controller, telemetry, _state = _watching(0.6, camera, side)
    watch.update(5.0, explore_fired=_fired(other), escape_fired={})
    assert memories.defence.level(5.0, other) == 0.0
    assert memories.vigilance.arousal(5.0) == 0.0
    assert telemetry.figures_remembered == {}


def test_a_spontaneous_dnp09_spike_on_an_empty_view_remembers_nothing():
    watch, memories, _controller, telemetry, _state = _watching(0.0)
    watch.update(5.0, explore_fired=_fired('left'), escape_fired={})
    assert memories.vigilance.arousal(5.0) == 0.0
    assert telemetry.figures_remembered == {}


def test_a_figure_dnp09_never_answered_is_not_remembered():
    watch, memories, _controller, telemetry, _state = _watching(0.6)
    watch.update(5.0, explore_fired=_fired(None), escape_fired={})
    assert memories.vigilance.arousal(5.0) == 0.0
    assert telemetry.figures_remembered == {}


def test_nothing_is_remembered_from_the_static_of_a_camera_that_just_came_up():
    watch, memories, _controller, _telemetry, _state = _watching(0.6)
    watch.update(RAISE - 0.1, explore_fired=_fired('left'), escape_fired={})
    assert memories.vigilance.arousal(RAISE - 0.1) == 0.0


def test_one_view_counts_as_one_sighting_at_the_strongest_level_dnp09_answered():
    watch, memories, _controller, telemetry, state = _watching(0.2)
    watch.update(5.0, explore_fired=_fired('left'), escape_fired={})
    state.tablet_drive = {'figure_left': 0.7}
    watch.update(5.1, explore_fired=_fired('left'), escape_fired={})
    watch.update(5.2, explore_fired=_fired('left'), escape_fired={})
    fade = math.exp(-0.1 / 4.0)
    assert memories.vigilance.level(5.2, 'left') == pytest.approx((0.2 * fade + 0.5) * fade)
    assert telemetry.figures_remembered == {'1C': 1}


def test_a_second_view_adds_to_what_the_first_one_left():
    watch, memories, _controller, _telemetry, state = _watching(0.4)
    watch.update(5.0, explore_fired=_fired('left'), escape_fired={})
    left_over = memories.vigilance.level(9.0, 'left')
    watch.on_lower(now=6.0)
    watch.on_raise(now=7.0)
    state.tablet_drive = {'figure_left': 0.4}
    watch.update(9.0, explore_fired=_fired('left'), escape_fired={})
    assert memories.vigilance.level(9.0, 'left') == pytest.approx(left_over + 0.4)


@pytest.mark.parametrize('drive, defended', [
    ({'loom_size_left': 0.6, 'loom_speed_left': 0.6, 'figure_left': 0.5}, config.MEMORY_DYNAMICS.threat_per_escape),
    ({'loom_size_left': 0.3, 'loom_speed_left': 0.3, 'figure_left': 0.5}, config.MEMORY_DYNAMICS.threat_per_escape),
    ({'figure_left': 0.5}, 0.0),
])
def test_each_dnp04_escape_from_something_large_on_the_tablet_adds_the_same_threat(drive, defended):
    """Gibson et al. (2015) model the defensive state as a leaky integrator
    in which each shadow adds a constant value. Fed with the loom of the
    moment, an escape from a cove read against the last look left a state that
    stopped holding the door within a few seconds."""
    watch, memories, _controller, _telemetry, state = _watching(0.0)
    state.tablet_drive = drive
    assert watch.update(5.0, explore_fired=NOBODY, escape_fired={'left': True, 'right': False}) == 'left'
    assert memories.defence.level(5.0, 'left') == pytest.approx(defended)


@pytest.mark.parametrize('camera, side', [('1C', 'left'), ('4B', 'right')])
@pytest.mark.parametrize('figure, dnp09, lowered_at, found', [
    (0.0, False, RAISE + 1.0, False),
    (0.6, False, RAISE + 1.0, False),
    (0.6, True, RAISE + 1.0, True),
    (0.6, True, RAISE - 0.1, None),
])
def test_a_view_that_became_readable_is_remembered_with_whether_dnp09_found_something(
        camera, side, figure, dnp09, lowered_at, found):
    watch, _memories, _controller, _telemetry, _state = _watching(figure, camera, side)
    watch.update(RAISE + 0.5, explore_fired=_fired(side if dnp09 else None), escape_fired={})
    watch.on_lower(now=lowered_at)
    assert watch.last_view == (None if found is None else FinishedView(side, found))
    assert watch.finished_views == (0 if found is None else 1)


LOOMING = {'figure_left': 0.6, 'loom_size_left': 0.4, 'loom_speed_left': 0.4}


@pytest.mark.parametrize('label, drive, escaped, lowered_at, cleared', [
    ('the curtain closed', {'figure_left': 0.0}, False, RAISE + 1.0, True),
    ('Foxy peeking', {'figure_left': 0.3, 'loom_size_left': 0.18}, False, RAISE + 1.0, True),
    ('something large DNp04 did not answer', LOOMING, False, RAISE + 1.0, True),
    ('DNp04 answered', LOOMING, True, RAISE + 1.0, False),
    ('the feed gave nothing', {}, False, RAISE + 1.0, False),
    ('lowered in the switching static', {'figure_left': 0.0}, False, RAISE - 0.1, False),
])
def test_a_view_clears_its_camera_when_it_was_read_and_dnp04_stayed_silent(
        label, drive, escaped, lowered_at, cleared):
    """On the night 4 of 2026-10-21 a peek read a loom of 0.18 that DNp04
    never answered, and the door stayed shut for eighty seconds because any
    loom at all counted against the cove."""
    watch, _memories, _controller, _telemetry, state = _watching(0.0)
    state.tablet_drive = drive
    watch.update(min(lowered_at, RAISE + 0.5), explore_fired=NOBODY,
                 escape_fired={'left': escaped, 'right': False})
    watch.on_lower(now=lowered_at)
    assert ('1C' in state.view_cleared_at) is cleared, label


def test_a_view_dnp04_escaped_from_counts_as_one_that_found_something():
    watch, _memories, _controller, _telemetry, state = _watching(0.0)
    state.tablet_drive = LOOMING
    watch.update(RAISE + 0.5, explore_fired=NOBODY, escape_fired={'left': True, 'right': False})
    watch.on_lower(now=RAISE + 0.6)
    assert watch.last_view == FinishedView('left', True)


def _came_down_from_the_cove(drive: dict):
    watch, memories, _controller, _telemetry, state = _watching(0.0)
    state.tablet_drive = drive
    watch.update(RAISE + 0.5, explore_fired=NOBODY, escape_fired=NOBODY)
    watch.on_lower(now=RAISE + 1.0)
    return watch, memories, state


@pytest.mark.parametrize('cleared_before', [None, 0.3])
def test_a_dnp04_spike_as_the_tablet_comes_down_is_an_escape_from_the_view_it_left(cleared_before):
    """On the night 4 of 2026-10-26 the fly lowered the tablet from a cove
    Foxy had just left, a loom of 0.27 still in the network, and DNp04 fired
    0.22 seconds into the lowering. The spike was dropped, the cove counted as
    clear, the door opened and Foxy came in 16 seconds later."""
    watch, memories, _controller, _telemetry, state = _watching(0.0)
    if cleared_before is not None:
        state.view_cleared_at['1C'] = cleared_before
    state.tablet_drive = {'figure_left': 1.0, 'loom_size_left': 0.27}
    watch.update(RAISE + 0.5, explore_fired=NOBODY, escape_fired=NOBODY)
    watch.on_lower(now=RAISE + 1.0)
    assert state.view_cleared_at['1C'] == RAISE + 1.0

    assert watch.update(RAISE + 1.2, explore_fired=NOBODY, escape_fired={'left': True, 'right': False}) == 'left'
    assert watch.source == '1C'
    assert state.view_cleared_at.get('1C') == cleared_before
    assert watch.last_view == FinishedView('left', True)
    assert memories.defence.level(RAISE + 1.2, 'left') == pytest.approx(config.MEMORY_DYNAMICS.threat_per_escape)


@pytest.mark.parametrize('label, escape, office_back', [
    ('DNp04 on the other side', {'left': False, 'right': True}, False),
    ('DNp04 once the office is back', {'left': True, 'right': False}, True),
])
def test_only_dnp04_on_the_side_of_the_view_before_the_office_is_back_counts(label, escape, office_back):
    watch, _memories, state = _came_down_from_the_cove(LOOMING)
    if office_back:
        watch.on_office(RAISE + 1.5)
    assert watch.update(RAISE + 1.6, explore_fired=NOBODY, escape_fired=escape) is None, label
    assert '1C' in state.view_cleared_at, label


def test_a_lowering_counts_one_escape():
    watch, _memories, _state = _came_down_from_the_cove(LOOMING)
    left = {'left': True, 'right': False}
    first = watch.update(RAISE + 1.2, explore_fired=NOBODY, escape_fired=left)
    second = watch.update(RAISE + 1.3, explore_fired=NOBODY, escape_fired=left)
    assert (first, second) == ('left', None)


def _alarmed(memories: Memories, now: float = RAISE):
    memories.defence.threat('left', 1.0, now=now)


@pytest.mark.parametrize('label, door_shut, fired, at, defended, followed', [
    ('DNp09 on the cove while the defensive state holds the shut door', True, 'left', RAISE + 0.5, True, True),
    ('a door shut for Bonnie', True, 'left', RAISE + 0.5, False, False),
    ('the door still open', False, 'left', RAISE + 0.5, True, False),
    ('DNp09 silent', True, None, RAISE + 0.5, True, False),
    ('only the DNp09 across the midline', True, 'right', RAISE + 0.5, True, False),
    ('the switching static', True, 'left', RAISE - 0.1, True, False),
])
def test_dnp09_follows_the_cove_to_the_west_hall_only_from_behind_a_door_shut_for_it(label, door_shut, fired, at,
                                                                                     defended, followed):
    """Foxy reaches the left door 1.7 seconds after CAM 2A shows him, so the
    hall is only safe to look at once the door is already shut, and only while
    the escape from the cove still holds it. On the night 4 of 2026-10-21 the
    door was shut for Bonnie, and every look at Foxy standing out of the
    curtain sent the gaze to the empty hall."""
    watch, memories, controller, telemetry, state = _watching(0.8)
    state.tablet_drive = LOOMING
    state.door_closed['left'] = door_shut
    if defended:
        _alarmed(memories)
    watch.update(at, explore_fired=_fired(fired), escape_fired={})
    assert watch.camera == ('2A' if followed else '1C'), label
    assert controller.selected[-1] == (('2A', 0.0) if followed else ('1C', config.TABLET_VISION.map_ready_sec))
    assert telemetry.pursuits == ({'1C to 2A': 1} if followed else {}), label


@pytest.mark.parametrize('alarmed_at, followed', [(RAISE, True), (RAISE - 8.0, False)])
def test_an_unchanged_cove_is_followed_until_the_defensive_state_lets_the_door_go(alarmed_at, followed):
    """Foxy gone from the cove looks the same on every look after the first,
    and only CAM 2A shown from behind the shut door sends him into it before
    the door reopens. On the night 4 of 2026-10-22 the cove was seen empty on
    three looks in a row before he came through the open left door."""
    watch, memories, _controller, _telemetry, state = _watching(0.8)
    state.door_closed['left'] = True
    _alarmed(memories, alarmed_at)
    watch.update(RAISE + 0.5, explore_fired=_fired('left'), escape_fired={})
    assert watch.camera == ('2A' if followed else '1C')


def test_the_corner_has_nowhere_to_follow_to():
    watch, _memories, _controller, telemetry, state = _watching(0.8, '4B', 'right')
    state.door_closed['right'] = True
    watch.update(RAISE + 0.5, explore_fired=_fired('right'), escape_fired={})
    assert watch.camera == '4B'
    assert telemetry.pursuits == {}


@pytest.mark.parametrize('late_escape', [False, True])
def test_the_cove_view_stays_open_while_the_gaze_follows_to_the_west_hall(late_escape):
    """DNp04 answers the cove one to four frames after the gaze has left it,
    so a spike during the CAM 2A view still belongs to the cove. A view the
    gaze left clears nothing either way. On the night 4 of 2026-10-22 the
    empty cove was followed to CAM 2A, DNp04 stayed silent, and the left door
    reopened 2.6 seconds later."""
    watch, memories, _controller, _telemetry, state = _watching(0.0)
    state.door_closed['left'] = True
    _alarmed(memories)
    state.tablet_drive = LOOMING
    watch.update(RAISE + 0.5, explore_fired=_fired('left'), escape_fired={})
    assert watch.camera == '2A'
    state.tablet_drive = {}
    watch.update(RAISE + 0.6, explore_fired=NOBODY, escape_fired={'left': late_escape, 'right': False})
    watch.on_lower(now=RAISE + 3.0)
    assert watch.finished_views == 1
    assert watch.last_view == FinishedView('left', True)
    assert '1C' not in state.view_cleared_at
    assert (memories.defence.level(RAISE + 0.6, 'left') == pytest.approx(1.0)) is late_escape


@pytest.mark.parametrize('followed, last_tap', [(True, ('1C', 0.0)), (False, ('1C', config.TABLET_VISION.map_ready_sec))])
def test_the_tablet_goes_down_on_the_camera_it_was_raised_on(followed, last_tap):
    """The game reopens the tablet on the last camera, and CAM 2A shown while
    Foxy is out of the cove sends him running at once."""
    watch, memories, controller, _telemetry, state = _watching(0.8)
    _alarmed(memories)
    state.tablet_drive = LOOMING
    state.door_closed['left'] = followed
    watch.update(RAISE + 0.5, explore_fired=_fired('left'), escape_fired={})
    watch.on_lower(now=RAISE + 3.0)
    assert controller.selected[-1] == last_tap


def test_a_dnp04_spike_in_the_frame_the_gaze_follows_is_put_on_the_cove(caplog):
    watch, memories, _controller, _telemetry, state = _watching(0.0)
    _alarmed(memories)
    state.door_closed['left'] = True
    state.tablet_drive = LOOMING
    with caplog.at_level(logging.INFO, logger='flynaf.night.tablet.watch'):
        watch.update(RAISE + 0.5, explore_fired=_fired('left'), escape_fired={'left': True})
    assert watch.camera == '2A'
    assert 'something large on camera 1C' in caplog.text


def test_the_watch_taps_the_map_and_tells_the_senses_where_it_looks():
    state = SensoryState(camera_open=True)
    controller, feed, telemetry = RecordingController(), RecordingFeed(), ConnectomeTelemetry()
    watch = TabletWatch(_gaze(), feed, controller, telemetry, state)

    watch.on_raise(now=0.0)
    assert feed.active
    assert state.tablet_camera == '1C'
    assert state.tablet_readable_at == RAISE
    assert telemetry.camera_views == {'1C': 1}

    watch.on_lower(now=0.5)
    assert not feed.active
    assert state.tablet_camera is None
    assert state.tablet_drive == {}


ESCAPE_CASES = (
    ({'left': True, 'right': False}, 'left'),
    ({'left': False, 'right': True}, 'right'),
    ({'left': False, 'right': False}, None),
)


def test_a_dnp04_spike_while_watching_names_the_door():
    for fired, expected in ESCAPE_CASES:
        watch = TabletWatch(_gaze(), RecordingFeed(), RecordingController(), ConnectomeTelemetry(),
                            SensoryState(camera_open=True))
        watch.on_raise(now=0.0)
        assert watch.update(0.1, explore_fired=NOBODY, escape_fired=fired) == expected, fired


def test_nothing_is_read_from_the_watch_while_the_tablet_is_down():
    watch = TabletWatch(_gaze(), RecordingFeed(), RecordingController(), ConnectomeTelemetry(),
                        SensoryState())
    assert watch.update(1.0, explore_fired=_fired('left'), escape_fired={'left': True}) is None

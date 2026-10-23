import pytest

from flynaf.night.tablet.watch import FinishedView
from flynaf.night.tasks import habituate_to_an_empty_view
from flynaf.search_drive import SearchDrive

DT = 0.1
SPAN = 100


def _settled(seconds: float, left_count: int = 0, right_count: int = 0, viewed: str | None = None):
    drive = SearchDrive(SPAN)
    if viewed:
        drive.viewed(viewed)
    for frame in range(int(seconds / DT)):
        drive.update(0.0, left_count, right_count, DT, frame * DT, False)
    return drive


@pytest.mark.parametrize('viewed, seconds, camera', [
    (None, 1.0, 'left'),
    ('left', 1.0, 'right'),
    ('right', 1.0, 'left'),
    ('left', 20.0, 'right'),
    ('left', 90.0, 'left'),
])
def test_the_camera_just_watched_gives_way_to_the_other_until_the_habituation_fades(viewed, seconds, camera):
    faint_pull_to_the_left = (3, 0)
    assert _settled(seconds, *faint_pull_to_the_left, viewed=viewed).camera_leaning == camera


@pytest.mark.parametrize('side, counts', [('right', (0, 60)), ('left', (60, 0))])
def test_a_threat_still_drawing_the_eye_after_the_refractory_wins_over_the_habituation(side, counts):
    assert _settled(15.0, *counts, viewed=side).camera_leaning == side


def test_a_view_leaves_the_hallway_search_alone():
    plain, viewed = _settled(5.0), _settled(5.0, viewed='left')
    assert viewed.drive == plain.drive
    assert viewed.leaning == plain.leaning


@pytest.mark.parametrize('alert, camera', [(0.0, 'left'), (-0.6, 'right'), (0.6, 'left')])
def test_a_side_where_a_figure_was_seen_draws_the_next_camera_back(alert, camera):
    drive = SearchDrive(SPAN)
    drive.viewed('right')
    for frame in range(int(15.0 / DT)):
        drive.update(0.0, 3, 0, DT, frame * DT, False, alert=alert)
    assert drive.camera_leaning == camera


@pytest.mark.parametrize('alert, threat, camera', [(0.6, 0.0, 'right'), (0.6, 0.6, 'left'), (0.0, 0.0, 'right')])
def test_a_door_held_by_the_defensive_state_keeps_the_camera_on_its_side(alert, threat, camera):
    """On the night 4 of 2026-10-21 the left door was held for a Foxy out of the
    curtain while the hallway search leaned right, and three raises opened on
    CAM 4B in the gaps in which Foxy left the cove."""
    drive = SearchDrive(SPAN)
    for frame in range(int(15.0 / DT)):
        drive.update(0.0, 0, SPAN, DT, frame * DT, False, alert=alert, threat=threat)
    assert drive.camera_leaning == camera


class _Tablet:
    def __init__(self, finished_views: int, last_view):
        self.finished_views = finished_views
        self.last_view = last_view


class _Search:
    def __init__(self):
        self.sides = []

    def viewed(self, side):
        self.sides.append(side)


@pytest.mark.parametrize('finished, seen, last_view, habituated', [
    (0, 0, None, []),
    (1, 0, FinishedView('right', False), ['right']),
    (1, 0, FinishedView('right', True), []),
    (1, 1, FinishedView('right', False), []),
    (2, 1, FinishedView('left', False), ['left']),
])
def test_only_a_view_that_found_nothing_habituates_its_side(finished, seen, last_view, habituated):
    search = _Search()
    assert habituate_to_an_empty_view(search, _Tablet(finished, last_view), seen) == finished
    assert search.sides == habituated

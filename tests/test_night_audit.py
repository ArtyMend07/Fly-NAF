import json
from unittest.mock import patch

import cv2
import numpy as np
import pytest

from flynaf import config
from flynaf.audit import hud, power, report, timeline, trace_view, windows
from flynaf.audit.timeline import Sample
from flynaf.env import frame_recorder
from flynaf.env.frame_recorder import frame_name, frame_time

AUDIT = config.NIGHT_AUDIT
MOTOR = config.MOTOR_CALIBRATION
GREEN, YELLOW, RED = (40, 230, 40), (0, 235, 250), (0, 40, 220)
BAR_COLOURS = (GREEN, GREEN, YELLOW, RED, RED)
MAP_BUTTONS = [(840 + 70 * column, 380 + 70 * row) for row in range(2) for column in range(4)]


def screen(usage: int = 1, doors: dict | None = None, tablet: bool = False, lit: str | None = None,
           window_level: int = 0) -> np.ndarray:
    frame = np.zeros((720, 1280, 3), np.uint8)
    top, bottom = AUDIT.usage_bar_rows
    for centre, colour in zip(AUDIT.usage_bar_centres[:usage], BAR_COLOURS):
        frame[top - 4:bottom + 4, centre - 9:centre + 9] = colour
    for side, closed in (doors or {}).items():
        x, y = getattr(MOTOR, f'{side}_door_button_x'), getattr(MOTOR, f'{side}_door_button_y')
        frame[y - 12:y + 12, x - 12:x + 12] = GREEN if closed else RED
    for x, y in MAP_BUTTONS if tablet else ():
        frame[y:y + 30, x:x + 50] = 255
    if lit:
        left, top, right, bottom = getattr(config.VISION_CALIBRATION, f'{lit}_window')
        frame[top:bottom, left:right] = window_level
        x, y = getattr(MOTOR, f'{lit}_light_button_x'), getattr(MOTOR, f'{lit}_light_button_y')
        frame[y - 12:y + 12, x - 12:x + 12] = 255
    return frame


def sample(t: float, usage: int = 1, tablet: bool = False, windows: dict | None = None, brightness: float = 40.0,
           **seen) -> Sample:
    return Sample(t, usage, tablet, {side: seen.get(side) for side in timeline.SIDES},
                  {side: (windows or {}).get(side) for side in timeline.SIDES}, brightness)


def believed(t: float, left: bool = False, right: bool = False, camera=None, drive=None) -> dict:
    return {'t': t, 'door_left': left, 'door_right': right, 'tablet_camera': camera, 'tablet_drive': drive or {}}


@pytest.mark.parametrize('usage', range(len(AUDIT.usage_bar_centres) + 1))
def test_the_usage_bars_are_counted_from_the_hud(usage):
    assert hud.usage_bars(screen(usage)) == usage


@pytest.mark.parametrize('closed, read', [(True, True), (False, False), (None, None)])
def test_a_door_is_read_from_the_colour_of_its_button(closed, read):
    doors = {} if closed is None else {'right': closed}
    assert hud.door_closed(screen(doors=doors), 'right') is read


@pytest.mark.parametrize('tablet', [True, False])
def test_the_tablet_is_up_when_the_camera_map_is_on_screen(tablet):
    assert hud.tablet_up(screen(tablet=tablet)) is tablet


@pytest.mark.parametrize('lit, level, someone', [('left', 40, False), ('left', 52, True), (None, 40, None)])
def test_a_closed_door_window_is_read_against_its_reference_only_with_the_light_on(lit, level, someone):
    left, top, right, bottom = config.VISION_CALIBRATION.left_window
    references = {'left': [np.full((bottom - top, right - left), 40, np.float32)]}
    frame = screen(lit=lit, window_level=level)
    assert windows.someone_at_the_window(frame, 'left', references) is someone


def test_closed_door_time_follows_readings_two_frames_agree_on():
    """The frame in which the light goes off still shows the button lit over a
    dark window, which reads like someone standing there."""
    readings = (None, False, False, True, None, True, True)
    night = [sample(t, left=True, windows={'left': seen}) for t, seen in enumerate(readings)]
    doors = [{'left': True, 'right': False}] * len(night)
    spent = timeline.closed_door_seconds(night, doors, AUDIT.longest_step_sec)
    assert spent['left'] == {'someone': 1.0, 'empty': 4.0, 'unchecked': 1.0}
    assert spent['right'] == {'someone': 0.0, 'empty': 0.0, 'unchecked': 0.0}


def test_frame_names_keep_the_trace_clock():
    assert frame_time(frame_name(12.3456)) == pytest.approx(12.346)


class StillScreen:
    def grab(self, box):
        return np.full((box['height'], box['width'], 4), 128, np.uint8)


@pytest.mark.parametrize('rect, written', [((0, 0, 8, 6), ['000001.500.jpg']), (None, [])])
def test_the_recorder_names_each_frame_by_the_trace_clock(tmp_path, rect, written):
    recorder = frame_recorder.FrameRecorder(str(tmp_path), origin=10.0)
    with patch.object(frame_recorder.anchor, 'game_rect', return_value=rect), \
         patch.object(frame_recorder.clock, 'now', return_value=11.5), \
         patch.object(frame_recorder.time, 'sleep'):
        recorder._grab_once(StillScreen())
    assert sorted(path.name for path in tmp_path.iterdir()) == written


def test_the_night_ends_where_the_hud_stays_away():
    """After 6 AM the game runs straight into the next night, and the frames
    keep coming while the fly keeps playing it."""
    samples = [sample(t, 2) for t in range(6)] + [sample(30, 0)] + [sample(t, 2) for t in range(60, 70)]
    assert [s.t for s in timeline.first_night(samples, AUDIT.night_gap_sec)] == list(range(6))


@pytest.mark.parametrize('length, after, ran_out', [
    (300, 4.5, True),
    (300, 120.0, False),
    (AUDIT.night_length_sec, 4.5, False),
])
def test_a_night_whose_hud_gives_way_to_a_dark_office_ran_out_of_power(length, after, ran_out):
    """Freddy's song plays in the dark office, while a catch with power left
    cuts to the jumpscare and a full night reaches the 6 AM screen."""
    night = [sample(0, 2), sample(length, 2)]
    samples = night + [sample(length + step, 0, brightness=after) for step in (1, 2, 3)]
    assert timeline.ran_out_of_power(samples, night, AUDIT) is ran_out


def test_a_door_keeps_the_state_it_was_last_seen_in():
    night = [sample(0, left=True), sample(1, tablet=True), sample(2, right=True), sample(3, left=False)]
    closed = [state['left'] for state in timeline.doors_over(night)]
    assert closed == [True, True, True, False]


@pytest.mark.parametrize('night_number, passive', [(1, 0.0), (3, 0.2), (5, 1 / 3)])
def test_power_is_split_between_the_office_and_what_the_fly_turned_on(night_number, passive):
    night = [sample(t, 4, tablet=True) for t in range(11)]
    doors = [{'left': True, 'right': False}] * len(night)
    percent, seconds = power.power_spent(night, doors, night_number)
    assert percent['base'] == pytest.approx(1.0)
    assert percent['night'] == pytest.approx(passive)
    assert {name: round(percent[name], 6) for name in power.COMPONENTS} == {
        'tablet': 1.0, 'left_door': 1.0, 'right_door': 0.0, 'lights': 1.0}
    assert seconds['tablet'] == pytest.approx(10.0)


def test_the_minutes_add_up_to_the_night():
    night = [sample(t, 2, tablet=True) for t in range(130)]
    doors = [{'left': False, 'right': False}] * len(night)
    minutes = power.power_by_minute(night, doors, 1)
    totals = [round(sum(minute.values()), 6) for minute in minutes]
    assert totals == [11.8, 12.0, 2.0]
    assert sum(totals) == pytest.approx(sum(power.power_spent(night, doors, 1)[0].values()))


def test_a_door_seen_against_what_the_fly_believed_is_reported_in_phases():
    """On 2026-10-21 a release click did not land, so the next close opened
    the right door, and the fly held a door it believed shut for the rest of
    the night while the screen showed it open."""
    trace = [believed(0.0, right=True), believed(4.0), believed(8.0, right=True)]
    night = ([sample(t, right=True) for t in (0, 1)] + [sample(t, right=True) for t in (4, 5, 6, 7)]
             + [sample(t, right=False) for t in (8, 9, 10, 11)] + [sample(12, right=False)])
    runs = trace_view.door_desyncs(night, trace, AUDIT.door_desync_shortest_sec)
    assert [(run['from'], run['to'], run['closed_on_screen']) for run in runs] == [(4, 7, True), (8, 12, False)]


def test_a_door_that_lags_its_click_by_a_frame_is_not_reported():
    trace = [believed(0.0), believed(1.0, left=True)]
    night = [sample(0, left=False), sample(1, left=False), sample(2, left=True)]
    assert trace_view.door_desyncs(night, trace, AUDIT.door_desync_shortest_sec) == []


def test_each_look_at_the_cove_is_one_view_with_its_strongest_reading():
    cove = AUDIT.cove_camera
    trace = [believed(0.0, camera=cove), believed(0.1, camera=cove, drive={'figure_left': 0.3}),
             believed(0.2, camera=cove, drive={'figure_left': 0.6, 'loom_size_left': 0.4}),
             believed(0.3, camera='4B', drive={'figure_right': 1.0}),
             believed(0.4, left=True, camera=cove, drive={'figure_left': 0.2})]
    views = trace_view.cove_views(trace, cove)
    assert [(view['t'], view['frames'], view['figure'], view['loom'], view['door_closed']) for view in views] == [
        (0.1, 2, 0.6, 0.4, False), (0.4, 1, 0.2, 0.0, True)]


def test_a_recorded_night_is_audited_from_its_frames_and_its_trace(tmp_path):
    frames = tmp_path / 'frames'
    frames.mkdir()
    for t in range(6):
        cv2.imwrite(str(frames / frame_name(float(t))), screen(2, doors={'left': t >= 3}))
    trace = tmp_path / 'trace_20261021_210713.jsonl'
    rows = [{'kind': 'header'}] + [{'kind': 'frame', **believed(float(t), left=t >= 3)} for t in range(6)]
    trace.write_text('\n'.join(json.dumps(row) for row in rows), encoding='utf-8')

    audit = report.audit_night(str(trace), str(frames), 3, references={})
    saved = report.save(audit, str(tmp_path / 'audits'))

    assert audit['power_percent']['left_door'] == pytest.approx(0.3)
    assert audit['door_desyncs'] == []
    assert audit['power_ran_out'] is False
    assert 'left_door' in report.describe(audit)
    assert saved.endswith('audit_20261021_210713.json')

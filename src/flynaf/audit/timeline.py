import os
from dataclasses import dataclass

import cv2

from flynaf.audit import hud, windows
from flynaf.env.frame_recorder import FRAME_SUFFIX, frame_time

SIDES = ('left', 'right')
VERDICTS = ('someone', 'empty', 'unchecked')


@dataclass(frozen=True)
class Sample:
    t: float
    usage: int
    tablet: bool
    doors_seen: dict
    windows_seen: dict
    brightness: float


def read_sample(t: float, frame, references: dict) -> Sample:
    up = hud.tablet_up(frame)
    doors = {side: None if up else hud.door_closed(frame, side) for side in SIDES}
    seen = {side: windows.someone_at_the_window(frame, side, references) if doors[side] else None
            for side in SIDES}
    return Sample(t, hud.usage_bars(frame), up, doors, seen, float(frame.mean()))


def read_samples(folder: str, references: dict) -> list:
    names = sorted((name for name in os.listdir(folder) if name.endswith(FRAME_SUFFIX)), key=frame_time)
    return [read_sample(frame_time(name), hud.to_design(cv2.imread(os.path.join(folder, name))), references)
            for name in names]


def first_night(samples: list, gap_sec: float) -> list:
    lit = [sample for sample in samples if sample.usage]
    night = lit[:1]
    for sample in lit[1:]:
        if sample.t - night[-1].t > gap_sec:
            break
        night.append(sample)
    return night


def ran_out_of_power(samples: list, night: list, params) -> bool:
    if night[-1].t - night[0].t >= params.night_length_sec:
        return False
    after = [sample for sample in samples
             if night[-1].t < sample.t <= night[-1].t + params.power_out_look_sec]
    return bool(after) and all(sample.brightness < params.power_out_dark_level for sample in after)


def doors_over(night: list) -> list:
    closed = dict.fromkeys(SIDES, False)
    timeline = []
    for sample in night:
        closed.update({side: seen for side, seen in sample.doors_seen.items() if seen is not None})
        timeline.append(dict(closed))
    return timeline


def closed_door_seconds(night: list, doors: list, longest_step_sec: float) -> dict:
    spent = {side: dict.fromkeys(VERDICTS, 0.0) for side in SIDES}
    verdict = dict.fromkeys(SIDES, 'unchecked')
    for previous, sample, closed in zip(night, night[1:], doors[1:]):
        step = min(sample.t - previous.t, longest_step_sec)
        for side in SIDES:
            if not closed[side]:
                verdict[side] = 'unchecked'
                continue
            seen, before = sample.windows_seen[side], previous.windows_seen[side]
            if seen is not None and seen == before:
                verdict[side] = 'someone' if seen else 'empty'
            spent[side][verdict[side]] += step
    return spent


def tablet_watches(night: list) -> list:
    watches, raised_at = [], None
    for sample in night:
        if sample.tablet and raised_at is None:
            raised_at = sample.t
        elif not sample.tablet and raised_at is not None:
            watches.append((raised_at, sample.t - raised_at))
            raised_at = None
    return watches

import bisect

from flynaf import config


def belief_at(trace_frames: list, times: list, t: float) -> dict | None:
    index = bisect.bisect_right(times, t) - 1
    return trace_frames[index] if index >= 0 else None


def door_desyncs(night: list, trace_frames: list, shortest_sec: float) -> list:
    times = [frame['t'] for frame in trace_frames]
    found, running = [], {}
    for sample in night:
        believed = belief_at(trace_frames, times, sample.t)
        if believed is None:
            continue
        for side, seen in sample.doors_seen.items():
            if seen is not None:
                follow_the_door(found, running, side, seen, seen != believed[f'door_{side}'], sample.t)
    found.extend(running.values())
    return sorted((run for run in found if run['to'] - run['from'] >= shortest_sec), key=lambda run: run['from'])


def follow_the_door(found: list, running: dict, side: str, closed_on_screen: bool, wrong: bool, t: float):
    run = running.get(side)
    if run is not None and (not wrong or run['closed_on_screen'] != closed_on_screen):
        found.append(running.pop(side))
    if wrong:
        running.setdefault(side, {'side': side, 'from': t, 'to': t, 'closed_on_screen': closed_on_screen})['to'] = t


def cove_views(trace_frames: list, camera: str) -> list:
    side = next(spec.side for spec in config.TABLET_VISION.cameras if spec.name == camera)
    views, current = [], None
    for frame in trace_frames:
        if frame.get('tablet_camera') != camera:
            current = None
            continue
        drive = frame.get('tablet_drive') or {}
        if not drive:
            continue
        if current is None:
            current = {'t': frame['t'], 'frames': 0, 'figure': 0.0, 'loom': 0.0, 'door_closed': frame[f'door_{side}']}
            views.append(current)
        current['frames'] += 1
        current['figure'] = max(current['figure'], drive.get(f'figure_{side}', 0.0))
        current['loom'] = max(current['loom'], drive.get(f'loom_size_{side}', 0.0))
    return views

import json
import os

from flynaf import config
from flynaf.audit import power, timeline, trace_view, windows
from flynaf.recorder import load_trace

AUDITS_FOLDER = os.path.join(config.PROJECT_ROOT, 'logs', 'audits')


def audit_night(trace_path: str, frames_folder: str, night_number: int, params=None,
                references: dict | None = None) -> dict:
    params = params or config.NIGHT_AUDIT
    references = windows.closed_door_references() if references is None else references
    _header, trace_frames, _events = load_trace(trace_path)
    samples = timeline.read_samples(frames_folder, references)
    night = timeline.first_night(samples, params.night_gap_sec)
    if not night:
        raise ValueError(f'no frame in {frames_folder} shows the power HUD')
    doors = timeline.doors_over(night)
    percent, seconds = power.power_spent(night, doors, night_number, params)
    watches = timeline.tablet_watches(night)
    ran_out = timeline.ran_out_of_power(samples, night, params)
    return {
        'trace': os.path.basename(trace_path),
        'night': night_number,
        'hud_from': night[0].t,
        'hud_to': night[-1].t,
        'power_ran_out': ran_out,
        'unseen_drain_percent': params.full_battery_percent - sum(percent.values()) if ran_out else None,
        'power_percent': percent,
        'seconds_on': seconds,
        'closed_door_seconds': timeline.closed_door_seconds(night, doors, params.longest_step_sec),
        'tablet_watches': [{'t': t, 'sec': length} for t, length in watches],
        'minutes': power.power_by_minute(night, doors, night_number, params),
        'door_desyncs': trace_view.door_desyncs(night, trace_frames, params.door_desync_shortest_sec),
        'cove_views': trace_view.cove_views(trace_frames, params.cove_camera),
    }


def clock_text(audit: dict, t: float) -> str:
    minutes, seconds = divmod(max(t - audit['hud_from'], 0.0), 60.0)
    return f'{int(minutes):02d}:{seconds:04.1f}'


def power_lines(audit: dict) -> list:
    spent = audit['power_percent']
    lines = ['power spent, percent']
    for name, value in sorted(spent.items(), key=lambda item: -item[1]):
        on = audit['seconds_on'].get(name)
        lines.append(f'  {name:<11}{value:6.1f}' + (f'   {on:5.0f} s on' if on is not None else ''))
    lines.append(f"  {'total':<11}{sum(spent.values()):6.1f}")
    if audit['power_ran_out']:
        lines.append(f"the power ran out at {clock_text(audit, audit['hud_to'])}, so "
                     f"{audit['unseen_drain_percent']:.1f} percent went where the usage bars do not show it, "
                     f'such as Foxy hitting a closed door, 1, 6, 11 and 16 percent for each hit in turn')
    return lines


def door_lines(audit: dict) -> list:
    lines = ['closed doors: seconds with someone at the lit window, with it empty, and not looked at yet']
    for side, spent in audit['closed_door_seconds'].items():
        lines.append(f"  {side:<6}{spent['someone']:6.0f}{spent['empty']:6.0f}{spent['unchecked']:6.0f}")
    lines += ['', 'doors the fly believed wrong']
    lines += [f"  {run['side']} from {clock_text(audit, run['from'])} to {clock_text(audit, run['to'])}, "
              f"{'closed' if run['closed_on_screen'] else 'open'} on screen and believed "
              f"{'open' if run['closed_on_screen'] else 'closed'}"
              for run in audit['door_desyncs']] or ['  none']
    return lines


def minute_lines(audit: dict) -> list:
    starts = [watch['t'] - audit['hud_from'] for watch in audit['tablet_watches']]
    lines = ['minute by minute: percent spent in all, on the tablet, the doors and the lights, and watches begun']
    for index, minute in enumerate(audit['minutes']):
        doors = minute['left_door'] + minute['right_door']
        begun = sum(1 for start in starts if index * 60 <= start < (index + 1) * 60)
        lines.append(f'  {index:2d}  {sum(minute.values()):5.1f}  {minute["tablet"]:5.1f}  {doors:5.1f}  '
                     f'{minute["lights"]:5.1f}  {begun:2d}')
    return lines


def cove_lines(audit: dict) -> list:
    lines = ['cove views: start, frames read, strongest figure and loom, left door believed closed']
    lines += [f"  {clock_text(audit, view['t'])}  {view['frames']:3d}  {view['figure']:.2f}  {view['loom']:.2f}  "
              f"{'yes' if view['door_closed'] else 'no'}"
              for view in audit['cove_views']] or ['  none']
    return lines


def describe(audit: dict) -> str:
    watches = audit['tablet_watches']
    mean = sum(watch['sec'] for watch in watches) / len(watches) if watches else 0.0
    sections = [
        [f"night {audit['night']}, {audit['trace']}, power HUD on screen for {clock_text(audit, audit['hud_to'])}"],
        power_lines(audit),
        [f'tablet: {len(watches)} watches, {mean:.1f} s each'],
        door_lines(audit),
        minute_lines(audit),
        cove_lines(audit),
    ]
    return '\n\n'.join('\n'.join(section) for section in sections)


def save(audit: dict, folder: str = AUDITS_FOLDER) -> str:
    os.makedirs(folder, exist_ok=True)
    stamp = os.path.splitext(audit['trace'])[0].removeprefix('trace_')
    path = os.path.join(folder, f'audit_{stamp}.json')
    with open(path, 'w', encoding='utf-8') as handle:
        json.dump(audit, handle, indent=2)
    return path

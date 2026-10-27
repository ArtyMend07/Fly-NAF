from flynaf import config

COMPONENTS = ('tablet', 'left_door', 'right_door', 'lights')
SECONDS_PER_MINUTE = 60


def night_drain_per_sec(night_number: int, params=None) -> float:
    params = params or config.NIGHT_AUDIT
    intervals = params.night_drain_interval_sec
    interval = intervals[min(night_number, len(intervals)) - 1]
    return params.night_drain_percent / interval if interval else 0.0


def bars_in_use(sample, closed: dict) -> dict:
    bars = {'tablet': float(sample.tablet), 'left_door': float(closed['left']),
            'right_door': float(closed['right'])}
    bars['lights'] = max(0.0, sample.usage - 1 - sum(bars.values()))
    return bars


def charges(night: list, doors: list, night_number: int, params=None):
    params = params or config.NIGHT_AUDIT
    rate = params.percent_per_bar_second
    passive = night_drain_per_sec(night_number, params)
    for previous, sample, closed in zip(night, night[1:], doors[1:]):
        step = min(sample.t - previous.t, params.longest_step_sec)
        bars = bars_in_use(sample, closed)
        charged = {'base': rate * step, 'night': passive * step}
        charged.update({name: rate * count * step for name, count in bars.items()})
        yield sample.t, step, bars, charged


def power_spent(night: list, doors: list, night_number: int, params=None) -> tuple:
    percent = dict.fromkeys(('base', 'night', *COMPONENTS), 0.0)
    seconds = dict.fromkeys(COMPONENTS, 0.0)
    for _t, step, bars, charged in charges(night, doors, night_number, params):
        for name, value in charged.items():
            percent[name] += value
        for name, count in bars.items():
            seconds[name] += count * step
    return percent, seconds


def power_by_minute(night: list, doors: list, night_number: int, params=None) -> list:
    minutes = {}
    for t, _step, _bars, charged in charges(night, doors, night_number, params):
        minute = minutes.setdefault(int((t - night[0].t) // SECONDS_PER_MINUTE), dict.fromkeys(charged, 0.0))
        for name, value in charged.items():
            minute[name] += value
    return [minutes[index] for index in sorted(minutes)]

import dataclasses
import logging
import os
import tomllib

import config

_log = logging.getLogger(__name__)

TUNING_PATH = os.path.join(config.PROJECT_ROOT, 'tuning.toml')


@dataclasses.dataclass(frozen=True)
class Knob:
    name: str
    singleton: str
    field: str
    default: float
    low: float
    high: float
    integer: bool
    note: str


KNOBS = (
    Knob(
        'arousal_multiplier', 'SIMULATION_PARAMS', 'arousal_multiplier',
        3.0, 1.0, 3.0, False,
        'Global gain on every synaptic weight. ADR 0013 measured 10.0 as a seizure, '
        'with 5.55 percent of the brain firing at rest. Above this range the network '
        'rings at its own delay frequency and the biological claim no longer holds.',
    ),
    Knob(
        'subliminal_noise_hz', 'FORAGING_PARAMS', 'subliminal_noise_hz',
        1.0, 0.5, 8.0, False,
        'Background drive added to every neuron. ADR 0013 cut this sixteenfold and the '
        'firing rate moved four tenths of a percent, so it does less than it looks.',
    ),
    Knob(
        'mse_threshold', 'FORAGING_PARAMS', 'mse_threshold',
        1500.0, 200.0, 20000.0, False,
        'How different a lit hallway must look before the eye drives its cluster. '
        'Lower means more door slams and more false alarms.',
    ),
    Knob(
        'starvation_sec', 'SEARCH_DYNAMICS', 'starvation_sec',
        30.0, 5.0, 300.0, False,
        'The one guard that is not the connectome. Below the saccade cycle it overrides '
        'the drive entirely and the fly degenerates into a metronome. The session report '
        'counts every look it causes.',
    ),
    Knob(
        'target_fps', 'SIMULATION_PARAMS', 'target_fps',
        10, 5, 20, True,
        'Engine frames per second, and the anchor for every leak in the system. Doubling '
        'it halves how long a door stays shut and how fast every drive decays.',
    ),
    Knob(
        'habituation_gain', 'SEARCH_DYNAMICS', 'habituation_gain',
        3.0, 0.0, 6.0, False,
        'How strongly a hallway just looked at pushes the drive away. At zero the fly '
        'stares at one side until the guard fires.',
    ),
    Knob(
        'camera_watch_max_sec', 'FORAGING_PARAMS', 'camera_watch_max_sec',
        6.0, 1.0, 30.0, False,
        'Hard cap on how long the tablet stays up. The fly is blind for all of it.',
    ),
)

_BY_NAME = {knob.name: knob for knob in KNOBS}


def write_template(path: str = TUNING_PATH) -> str:
    lines = [
        '# Fly-NAF tuning. Every value here is safe to change within the stated range.',
        '# Values outside the range are clamped and reported when the run starts.',
        '# Delete this file to go back to the defaults.',
        '',
    ]
    for knob in KNOBS:
        lines.append('# %s' % knob.note.replace('\n', ' '))
        lines.append('# range %s to %s, default %s' % (knob.low, knob.high, knob.default))
        lines.append('%s = %s' % (knob.name, knob.default))
        lines.append('')
    text = '\n'.join(lines)
    with open(path, 'w', encoding='utf-8') as handle:
        handle.write(text)
    return path


def read(path: str = TUNING_PATH) -> dict:
    if not os.path.isfile(path):
        return {}
    try:
        with open(path, 'rb') as handle:
            return tomllib.load(handle)
    except (OSError, tomllib.TOMLDecodeError) as exc:
        _log.warning('tuning file ignored, it could not be read: %s', exc)
        return {}


def resolve(raw: dict) -> tuple:
    settings, notices = {}, []
    for name, value in raw.items():
        knob = _BY_NAME.get(name)
        if knob is None:
            notices.append('%s is not a tunable setting, ignored' % name)
            continue
        try:
            number = int(value) if knob.integer else float(value)
        except (TypeError, ValueError):
            notices.append('%s is not a number, keeping %s' % (name, knob.default))
            continue
        clamped = min(max(number, knob.low), knob.high)
        if clamped != number:
            notices.append(
                '%s was set to %s, which is outside the measured range %s to %s, using %s'
                % (name, number, knob.low, knob.high, clamped)
            )
        if clamped != knob.default:
            settings[name] = clamped
    return settings, notices


def apply(settings: dict) -> list:
    applied = []
    grouped: dict = {}
    for name, value in settings.items():
        knob = _BY_NAME[name]
        grouped.setdefault(knob.singleton, {})[knob.field] = value
        applied.append('%s = %s (default %s)' % (name, value, knob.default))

    for singleton, fields in grouped.items():
        current = getattr(config, singleton)
        setattr(config, singleton, dataclasses.replace(current, **fields))
    return applied


def load(path: str = TUNING_PATH) -> list:
    if not os.path.isfile(path):
        write_template(path)
        _log.info('wrote a tuning file you can edit at %s', path)
        return []
    settings, notices = resolve(read(path))
    for notice in notices:
        _log.warning('%s', notice)
    applied = apply(settings)
    for line in applied:
        _log.info('tuning: %s', line)
    return applied + notices

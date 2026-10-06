import math

from flynaf.night.state import SensoryState
from flynaf.night.tablet.memory import ObjectMemory
from flynaf.night.tablet.senses import TabletSenses


class ScriptedFeed:
    def __init__(self, contrasts: dict, noise: float = 100.0):
        self.contrasts = contrasts
        self._noise = noise

    def contrast(self, camera):
        return self.contrasts.get(camera)

    def noise(self, camera):
        return self._noise


def _watching(camera, readable_at=0.0, camera_open=True) -> SensoryState:
    return SensoryState(camera_open=camera_open, tablet_camera=camera, tablet_readable_at=readable_at)


SILENT_CASES = (
    ('tablet down', _watching('1C', camera_open=False)),
    ('no camera chosen', _watching(None)),
    ('camera still in its switching static', _watching('1C', readable_at=99.0)),
    ('a camera the fly does not read', _watching('2A')),
)


def test_nothing_reaches_the_brain_unless_a_known_camera_is_readable():
    senses = TabletSenses(ScriptedFeed({'1C': 5000.0}))
    for label, state in SILENT_CASES:
        assert senses.read(state, now=1.0) == {}, label


def test_the_cove_drives_the_figure_population_on_its_side():
    senses = TabletSenses(ScriptedFeed({'1C': 850.0}))
    drive = senses.read(_watching('1C'), now=1.0)
    assert drive == {'figure_left': 0.5}


def _remembering(strength: float, now: float = 0.0) -> ObjectMemory:
    memory = ObjectMemory(decay_sec=4.0)
    memory.remember('left', strength, now)
    return memory


def test_a_remembered_figure_drives_the_looming_populations_on_its_side_with_the_tablet_down():
    senses = TabletSenses(ScriptedFeed({'1C': 5000.0}), _remembering(0.6))
    drive = senses.read(_watching('1C', camera_open=False), now=0.0)
    assert drive == {'loom_size_left': 0.6, 'loom_speed_left': 0.6}


def test_the_remembered_figure_and_the_cove_reach_the_brain_together():
    senses = TabletSenses(ScriptedFeed({'1C': 850.0}), _remembering(0.6))
    drive = senses.read(_watching('1C'), now=4.0)
    assert drive['figure_left'] == 0.5
    assert abs(drive['loom_size_left'] - 0.6 * math.exp(-1.0)) < 1e-9


if __name__ == '__main__':
    for name, fn in sorted(globals().items()):
        if name.startswith('test_'):
            fn()
    print('ok')

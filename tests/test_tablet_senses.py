from flynaf.night.state import SensoryState
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
    ('a camera with no reference', _watching('2A')),
)


def test_nothing_reaches_the_brain_unless_a_known_camera_is_readable():
    senses = TabletSenses(ScriptedFeed({'1C': 5000.0}))
    for label, state in SILENT_CASES:
        assert senses.read(state, now=1.0) == {}, label


def test_the_cove_drives_the_figure_population_on_its_side():
    senses = TabletSenses(ScriptedFeed({'1C': 600.0}))
    drive = senses.read(_watching('1C'), now=1.0)
    assert drive == {'figure_left': 0.5}


def test_the_west_hall_drives_the_looming_populations():
    feed = ScriptedFeed({'2A': 100.0})
    senses = TabletSenses(feed)
    state = _watching('2A')
    senses.read(state, now=1.0)
    feed.contrasts['2A'] = 1100.0
    drive = senses.read(state, now=1.1)
    assert set(drive) == {'loom_size_left', 'loom_speed_left'}
    assert drive['loom_size_left'] == 1.0
    assert drive['loom_speed_left'] > 0.9


def test_switching_cameras_does_not_count_the_cut_as_motion():
    feed = ScriptedFeed({'1C': 100.0, '2A': 5000.0})
    senses = TabletSenses(feed)
    senses.read(_watching('2A'), now=0.0)
    senses.read(_watching('1C'), now=0.5)
    drive = senses.read(_watching('2A'), now=1.0)
    assert drive['loom_speed_left'] == 0.0


if __name__ == '__main__':
    for name, fn in sorted(globals().items()):
        if name.startswith('test_'):
            fn()
    print('ok')

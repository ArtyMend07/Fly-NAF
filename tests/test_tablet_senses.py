import pytest

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
    ('a camera the fly does not read', _watching('2A')),
)


def test_nothing_reaches_the_brain_unless_a_known_camera_is_readable():
    senses = TabletSenses(ScriptedFeed({'1C': 5000.0}))
    for label, state in SILENT_CASES:
        assert senses.read(state, now=1.0) == {}, label


@pytest.mark.parametrize('camera, population', [
    ('1C', 'figure_left'),
    ('4B', 'figure_right'),
])
def test_a_camera_drives_the_figure_population_on_its_side(camera, population):
    senses = TabletSenses(ScriptedFeed({camera: 850.0}))
    assert senses.read(_watching(camera), now=1.0) == {population: 0.5}


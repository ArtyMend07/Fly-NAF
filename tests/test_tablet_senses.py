import dataclasses

import pytest

from flynaf import config
from flynaf.env.tablet_feed import Reading
from flynaf.night.state import SensoryState
from flynaf.night.tablet.senses import TabletSenses, transduce

COVE = config.CameraButton('1C', 0, 0, 'left')
CORNER = config.CameraButton('4B', 0, 0, 'right', defensive=False)
NOISE = 100.0


class ScriptedFeed:
    def __init__(self, readings: dict, noise: float = NOISE):
        self.readings = readings
        self._noise = noise

    def reading(self, camera):
        return self.readings.get(camera)

    def noise(self, camera):
        return self._noise


def _watching(camera, readable_at=0.0, camera_open=True, on_screen=True) -> SensoryState:
    return SensoryState(camera_open=camera_open, tablet_seen=on_screen, tablet_camera=camera,
                        tablet_readable_at=readable_at)


SILENT_CASES = (
    ('tablet down', _watching('1C', camera_open=False)),
    ('the game dropped the tablet, as when the power runs out', _watching('1C', on_screen=False)),
    ('no camera chosen', _watching(None)),
    ('camera still in its switching static', _watching('1C', readable_at=99.0)),
    ('a camera the fly does not read', _watching('2A')),
)


def test_nothing_reaches_the_brain_unless_a_known_camera_is_readable():
    senses = TabletSenses(ScriptedFeed({'1C': Reading(5000.0, 0.05)}))
    for label, state in SILENT_CASES:
        assert senses.read(state, now=1.0) == {}, label


@pytest.mark.parametrize('camera, population', [
    ('1C', 'figure_left'),
    ('4B', 'figure_right'),
])
def test_a_small_change_drives_the_figure_population_on_its_side(camera, population):
    senses = TabletSenses(ScriptedFeed({camera: Reading(850.0, 0.05)}))
    assert senses.read(_watching(camera), now=1.0) == {population: 0.5}


@pytest.mark.parametrize('camera, level', [('1C', 0.25), ('4B', 0.5)])
def test_each_camera_scales_its_contrast_by_its_own_span(camera, level):
    params = dataclasses.replace(config.TABLET_VISION, cameras=(
        config.CameraButton('1C', 0, 0, 'left', figure_span_mse=1600.0),
        config.CameraButton('4B', 0, 0, 'right', figure_span_mse=800.0),
    ))
    senses = TabletSenses(ScriptedFeed({camera: Reading(500.0, 0.05)}), params)
    assert list(senses.read(_watching(camera), now=1.0).values()) == [level]


@pytest.mark.parametrize('label, share, loom', [
    ('Foxy peeking through the gap', 0.06, 0.0),
    ('Foxy out of the curtain', 0.27, pytest.approx(0.57, abs=0.01)),
    ('the cove empty with the curtain open', 0.37, pytest.approx(0.9)),
    ('a change over most of the cove', 0.70, 1.0),
])
def test_the_share_of_the_cove_that_changed_decides_how_much_it_looms(label, share, loom):
    drive = transduce(COVE, Reading(1200.0, share), NOISE)
    assert drive.get('loom_size_left', 0.0) == loom, label
    assert drive.get('loom_speed_left', 0.0) == loom, label
    assert drive['figure_left'] > 0.0, label


def test_a_large_change_in_the_corner_stays_a_figure_and_never_looms():
    assert transduce(CORNER, Reading(1200.0, 0.5), NOISE) == {'figure_right': pytest.approx(0.73, abs=0.01)}


@pytest.mark.parametrize('camera, population', [(COVE, 'wide_field_left'), (CORNER, 'wide_field_right')])
def test_a_flash_or_a_knocked_out_feed_is_a_wide_field_event_and_no_object(camera, population):
    assert transduce(camera, Reading(55000.0, 0.95), NOISE) == {population: 1.0}

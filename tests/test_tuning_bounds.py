import os
import tempfile

from flynaf import config, tuning


def test_every_knob_points_at_a_real_config_field():
    for knob in tuning.KNOBS:
        singleton = getattr(config, knob.singleton)
        assert hasattr(singleton, knob.field), knob.name
        assert getattr(singleton, knob.field) == knob.default, knob.name


def test_values_inside_the_range_are_kept():
    settings, notices = tuning.resolve({'arousal_multiplier': 2.0})
    assert settings == {'arousal_multiplier': 2.0}
    assert notices == []


def test_values_above_the_range_are_clamped_and_reported():
    settings, notices = tuning.resolve({'arousal_multiplier': 10.0})
    assert settings == {}
    assert len(notices) == 1
    assert 'outside the measured range' in notices[0]


def test_a_clamp_that_lands_away_from_the_default_is_applied():
    settings, notices = tuning.resolve({'subliminal_noise_hz': 99.0})
    assert settings == {'subliminal_noise_hz': 8.0}
    assert 'outside the measured range' in notices[0]


def test_values_below_the_range_are_clamped():
    settings, _notices = tuning.resolve({'subliminal_noise_hz': 0.0})
    assert settings == {'subliminal_noise_hz': 0.5}


def test_a_zero_frame_rate_can_never_reach_the_engine():
    settings, notices = tuning.resolve({'target_fps': 0})
    assert settings['target_fps'] == 5
    assert notices


def test_the_frame_rate_stays_an_integer():
    settings, _notices = tuning.resolve({'target_fps': 12.7})
    assert settings['target_fps'] == 12
    assert isinstance(settings['target_fps'], int)


def test_unknown_names_are_reported_and_ignored():
    settings, notices = tuning.resolve({'w_scale': 0.5})
    assert settings == {}
    assert 'not a tunable setting' in notices[0]


def test_the_blocked_neural_parameters_are_not_exposed():
    exposed = {knob.name for knob in tuning.KNOBS}
    for blocked in ('w_scale', 'scale_poisson', 'dt', 'v_threshold', 'tau_mem', 'base_sensory_rate_hz'):
        assert blocked not in exposed


def test_text_that_is_not_a_number_keeps_the_default():
    settings, notices = tuning.resolve({'mse_threshold': 'loud'})
    assert settings == {}
    assert 'not a number' in notices[0]


def test_apply_changes_the_singleton_and_can_be_put_back():
    original = config.SIMULATION_PARAMS.arousal_multiplier
    try:
        tuning.apply({'arousal_multiplier': 1.5})
        assert config.SIMULATION_PARAMS.arousal_multiplier == 1.5
    finally:
        tuning.apply({'arousal_multiplier': original})
    assert config.SIMULATION_PARAMS.arousal_multiplier == original


def test_a_written_template_reads_back_as_the_defaults():
    with tempfile.TemporaryDirectory() as folder:
        path = os.path.join(folder, 'tuning.toml')
        tuning.write_template(path)
        settings, notices = tuning.resolve(tuning.read(path))
        assert settings == {}
        assert notices == []


def test_a_broken_file_is_ignored_rather_than_fatal():
    with tempfile.TemporaryDirectory() as folder:
        path = os.path.join(folder, 'tuning.toml')
        with open(path, 'w', encoding='utf-8') as handle:
            handle.write('this is not = = toml')
        assert tuning.read(path) == {}


if __name__ == '__main__':
    for name, fn in sorted(globals().items()):
        if name.startswith('test_'):
            fn()
    print('ok')

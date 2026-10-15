import json
import os

import pytest

from flynaf import replay_page

FRAME_KEYS = {
    'kind', 't', 'left_rate', 'right_rate', 'cam_inhib', 'left_mse', 'right_mse', 'camera_open',
    'gf_left', 'gf_right', 'escape_left', 'escape_right', 'explore_spike', 'tablet_camera',
    'tablet_drive', 'memory_drive', 'door_left', 'door_right', 'eye_membrane_diff', 'explore_membrane',
}
HEADER_KEYS = {'kind', 'trace_version', 'recorded_at', 'connectome', 'settings'}


@pytest.mark.parametrize('frames', [
    [],
    [[]],
    [[0, 1, 2], [], [138638]],
    [[5, 3, 900000, 127, 128, 16384]],
])
def test_spikes_come_back_sorted_from_their_compact_form(frames):
    decoded = replay_page.decode_spikes(replay_page.encode_spikes(frames))
    assert decoded == [sorted(frame) for frame in frames]


def test_the_page_loads_the_player_before_any_script_of_the_panel():
    page = replay_page.replay_page()
    player = page.index('<script src="player.js"></script>')
    assert player < page.index('<script>')
    assert replay_page.LIVE_TITLE not in page


def test_a_built_page_carries_the_player_and_the_recording(tmp_path):
    recording = tmp_path / 'recording'
    recording.mkdir()
    for name in replay_page.RECORDING_FILES:
        (recording / name).write_bytes(b'{}')
    out = tmp_path / 'site'
    replay_page.build(str(out), str(recording))
    assert sorted(os.listdir(out)) == sorted(['.nojekyll', 'index.html', 'player.js', *replay_page.RECORDING_FILES])


def _bundled_trace() -> list:
    with open(replay_page.EXAMPLE_TRACE, encoding='utf-8') as handle:
        return [json.loads(line) for line in handle if line.strip()]


def test_the_bundled_night_holds_numbers_and_camera_names_only():
    header, *frames = _bundled_trace()
    assert set(header) <= HEADER_KEYS
    assert frames and all(set(frame) <= FRAME_KEYS for frame in frames)
    texts = {frame['tablet_camera'] for frame in frames if frame.get('tablet_camera') is not None}
    assert texts <= {'1C', '2A', '4B'}, texts


def test_the_bundled_night_names_nothing_on_the_machine_that_recorded_it():
    with open(replay_page.EXAMPLE_TRACE, encoding='utf-8') as handle:
        text = handle.read().lower()
    for marker in ('users', '\\\\', '/home/', 'c:/', '.exe'):
        assert marker not in text, marker

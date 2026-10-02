import os
import tempfile

from flynaf import recorder, replay
from flynaf.night.state import SensoryState


def FakeState(left, right, inhib, **tablet):
    return SensoryState(left_rate=left, right_rate=right, cam_inhib=inhib, **tablet)


class FakeEngine:
    eye_membrane_diff = 0.25
    explore_membrane = -48.5


def _write_trace(path: str, rows: list):
    trace = recorder.SessionRecorder(path=path)
    for left, right, inhib, gf_l, gf_r in rows:
        trace.frame(
            0.1, FakeState(left, right, inhib), FakeEngine(),
            gf_l, gf_r, 120.0, 340.0, False,
        )
    trace.event(1.0, 'door', 'left slammed')
    trace.close()


def test_a_written_trace_reads_back_with_its_header_and_frames():
    with tempfile.TemporaryDirectory() as folder:
        path = os.path.join(folder, 'trace.jsonl')
        _write_trace(path, [(1.0, 0.0, 0.0, True, False), (0.0, 0.0, 0.0, False, False)])

        header, frames, events = recorder.load_trace(path)
        assert header['trace_version'] == recorder.TRACE_VERSION
        assert 'arousal_multiplier' in header['settings']
        assert len(frames) == 2
        assert frames[0]['left_rate'] == 1.0
        assert frames[0]['gf_left'] is True
        assert len(events) == 1


def test_the_tablet_drive_survives_the_trace_and_reaches_replay():
    with tempfile.TemporaryDirectory() as folder:
        path = os.path.join(folder, 'trace.jsonl')
        trace = recorder.SessionRecorder(path=path)
        state = FakeState(0.0, 0.0, 1000.0, camera_open=True, tablet_camera='2A',
                          tablet_drive={'loom_size_left': 0.4, 'loom_speed_left': 0.9},
                          l_escape=True)
        trace.frame(0.1, state, FakeEngine(), False, False, 0.0, 0.0, True)
        trace.close()

        _header, frames, _events = recorder.load_trace(path)
        assert frames[0]['tablet_camera'] == '2A'
        assert frames[0]['escape_left'] is True
        assert replay.FrameInput(frames[0]).tablet_drive == {'loom_size_left': 0.4, 'loom_speed_left': 0.9}


def test_a_disabled_recorder_writes_nothing():
    with tempfile.TemporaryDirectory() as folder:
        path = os.path.join(folder, 'trace.jsonl')
        trace = recorder.SessionRecorder(path=path, enabled=False)
        trace.frame(0.1, FakeState(1.0, 0.0, 0.0), FakeEngine(), True, False, 0.0, 0.0, False)
        trace.close()
        assert not os.path.exists(path)


def test_latency_counts_driven_frames_until_the_fiber_answers():
    driven = [(False, False), (True, False), (True, False), (True, True), (True, True)]
    assert replay._reflex_latencies(driven) == [3]


def test_a_threat_that_is_never_answered_contributes_no_latency():
    driven = [(True, False)] * 12
    assert replay._reflex_latencies(driven) == []


def test_each_separate_threat_is_counted_once():
    driven = [
        (True, False), (True, True), (True, True),
        (False, False),
        (True, False), (True, False), (True, True),
    ]
    assert replay._reflex_latencies(driven) == [2, 3]


def test_a_spike_with_no_drive_is_not_counted_as_an_answer():
    driven = [(False, True), (False, True), (True, True)]
    assert replay._reflex_latencies(driven) == [1]


def test_frame_input_reads_every_field_the_engine_needs():
    payload = {'left_rate': 1.0, 'right_rate': 0.0, 'cam_inhib': 1000.0, 't': 4.2}
    frame = replay.FrameInput(payload)
    assert (frame.left_rate, frame.right_rate, frame.cam_inhib, frame.t) == (1.0, 0.0, 1000.0, 4.2)


def test_a_frame_missing_fields_falls_back_to_silence():
    frame = replay.FrameInput({})
    assert (frame.left_rate, frame.right_rate, frame.cam_inhib) == (0.0, 0.0, 0.0)
    assert frame.tablet_drive == {}


if __name__ == '__main__':
    for name, fn in sorted(globals().items()):
        if name.startswith('test_'):
            fn()
    print('ok')

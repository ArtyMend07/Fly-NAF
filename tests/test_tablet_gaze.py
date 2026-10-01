from flynaf import config
from flynaf.night.state import SensoryState
from flynaf.night.tablet.gaze import TabletGaze
from flynaf.night.tablet.watch import TabletWatch
from flynaf.telemetry import ConnectomeTelemetry

RAISE = 1.2
SWITCH = 0.5


def _gaze() -> TabletGaze:
    return TabletGaze(config.TABLET_VISION.cameras, '1C', RAISE, SWITCH)


class _Done:
    def wait(self, timeout=None):
        return True


class RecordingController:
    def __init__(self):
        self.selected = []

    def select_camera(self, camera, settle_sec=0.0):
        self.selected.append((camera, settle_sec))
        return _Done()


class RecordingFeed:
    def __init__(self):
        self.active = False

    def activate(self):
        self.active = True

    def deactivate(self):
        self.active = False


def test_raising_the_tablet_always_opens_on_the_cove():
    gaze = _gaze()
    assert gaze.on_raised(now=10.0) == '1C'
    assert gaze.readable_at == 10.0 + RAISE
    assert not gaze.readable(10.0)
    assert gaze.readable(10.0 + RAISE)


PURSUIT_CASES = (
    ('no spike', 20.0, False, None),
    ('spike during the raise static', 10.1, True, None),
    ('spike once the cove is readable', 20.0, True, '2A'),
)


def test_pursuit_needs_a_dnp09_spike_on_a_readable_cove():
    for label, now, fired, expected in PURSUIT_CASES:
        gaze = _gaze()
        gaze.on_raised(now=10.0)
        assert gaze.pursue(now, fired) == expected, label


def test_pursuit_happens_once_per_raise_and_never_from_the_hall():
    gaze = _gaze()
    gaze.on_raised(now=0.0)
    assert gaze.pursue(5.0, True) == '2A'
    assert gaze.camera == '2A'
    assert gaze.pursue(10.0, True) is None

    gaze.on_lowered()
    gaze.on_raised(now=20.0)
    assert gaze.pursue(25.0, True) == '2A'


def test_the_watch_taps_the_map_and_tells_the_senses_where_it_looks():
    state = SensoryState(camera_open=True)
    controller, feed, telemetry = RecordingController(), RecordingFeed(), ConnectomeTelemetry()
    watch = TabletWatch(_gaze(), feed, controller, telemetry, state)

    watch.on_raise(now=0.0)
    assert feed.active
    assert state.tablet_camera == '1C'
    assert state.tablet_readable_at == RAISE

    watch.update(5.0, explore_fired=True, escape_fired={})
    assert controller.selected == [('1C', config.TABLET_VISION.map_ready_sec), ('2A', 0.0)]
    assert state.tablet_camera == '2A'
    assert telemetry.camera_view_causes == {'raise': 1, 'pursuit': 1}

    watch.on_lower()
    assert not feed.active
    assert state.tablet_camera is None
    assert state.tablet_drive == {}


ESCAPE_CASES = (
    ({'left': True, 'right': False}, 'left'),
    ({'left': False, 'right': True}, 'right'),
    ({'left': False, 'right': False}, None),
)


def test_a_dnp04_spike_while_watching_names_the_door():
    for fired, expected in ESCAPE_CASES:
        watch = TabletWatch(_gaze(), RecordingFeed(), RecordingController(), ConnectomeTelemetry(),
                            SensoryState(camera_open=True))
        watch.on_raise(now=0.0)
        assert watch.update(0.1, explore_fired=False, escape_fired=fired) == expected, fired


def test_nothing_is_read_from_the_watch_while_the_tablet_is_down():
    watch = TabletWatch(_gaze(), RecordingFeed(), RecordingController(), ConnectomeTelemetry(),
                        SensoryState())
    assert watch.update(1.0, explore_fired=True, escape_fired={'left': True}) is None


if __name__ == '__main__':
    for name, fn in sorted(globals().items()):
        if name.startswith('test_'):
            fn()
    print('ok')

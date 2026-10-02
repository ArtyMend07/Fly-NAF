import pytest

from flynaf import config
from flynaf.night.engine import has_settled

WINDOW = config.SIMULATION_PARAMS.settle_window_frames
RATIO = config.SIMULATION_PARAMS.settle_growth_ratio

MEASURED_RECRUITMENT = [
    153, 153, 131, 156, 156, 186, 259, 278, 387, 527, 569, 778, 932, 1428, 1406, 2434,
    2270, 2685, 2224, 2607, 2383, 2692, 2339, 2907, 2200, 2700, 2391, 2872, 2446, 2925,
    2399, 3191, 2702, 3070, 2904, 3430, 2775, 3299, 2855, 3317,
]
LAST_SPURIOUS_GIANT_FIBER_FRAME = 17


def first_settled_frame(activity: list) -> int | None:
    for end in range(1, len(activity) + 1):
        if has_settled(activity[:end], WINDOW, RATIO):
            return end
    return None


@pytest.mark.parametrize('activity, expected', [
    ([], False),
    ([3000] * (2 * WINDOW - 1), False),
    ([3000] * (2 * WINDOW), True),
    ([150] * WINDOW + [3000] * WINDOW, False),
    ([3000] * WINDOW + [2000] * WINDOW, True),
])
def test_settling_needs_two_full_windows_without_growth(activity, expected):
    assert has_settled(activity, WINDOW, RATIO) is expected


def test_the_measured_recruitment_wave_is_over_before_the_network_counts_as_settled():
    settled_at = first_settled_frame(MEASURED_RECRUITMENT)

    assert settled_at is not None
    assert settled_at > LAST_SPURIOUS_GIANT_FIBER_FRAME
    assert settled_at < config.SIMULATION_PARAMS.settle_max_frames

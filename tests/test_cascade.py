
import numpy as np

from flynaf.env.cascade import CascadeTracer


def _tracer(synapses: list, size: int, frames: list, **limits) -> CascadeTracer:
    synapses = sorted(synapses, key=lambda edge: edge[1])
    crow = np.zeros(size + 1, dtype=np.int64)
    for _pre, post, _w in synapses:
        crow[post + 1] += 1
    crow = np.cumsum(crow)
    col = np.array([pre for pre, _post, _w in synapses], dtype=np.int32)
    weight = np.array([w for _pre, _post, w in synapses], dtype=np.float32)
    tracer = CascadeTracer(crow, col, weight, **limits)
    for frame in frames:
        tracer.record(np.array(frame))
    return tracer


def _links(result: dict) -> set:
    return {(pre, post) for pre, post, *_rest in result['edges']}


CHAIN = [(0, 1, 5.0), (1, 2, 4.0), (2, 3, 6.0), (4, 3, -3.0), (5, 3, 1.0)]


def test_the_trace_follows_synapses_that_fired_in_order():
    result = _tracer(CHAIN, 6, [[0], [1], [2, 4], [3]]).trace(3, sources=[0])
    assert _links(result) == {(2, 3), (1, 2), (0, 1)}
    assert result['reached_source'] == 3
    assert result['depth'] == 3


def test_a_neuron_that_never_fired_is_never_in_the_trace():
    result = _tracer(CHAIN, 6, [[0], [1], [2], [3]]).trace(3)
    assert 5 not in {pre for pre, *_rest in result['edges']}


def test_inhibitory_inputs_are_counted_but_not_drawn_as_causes():
    result = _tracer(CHAIN, 6, [[0], [1], [2, 4], [3]]).trace(3)
    assert (4, 3) not in _links(result)
    assert result['inhibitory_inputs'] == 1


def test_one_hop_can_happen_inside_a_frame_but_not_two():
    synapses = [(0, 1, 1.0), (1, 2, 1.0), (2, 3, 1.0)]
    result = _tracer(synapses, 4, [[], [0, 1, 2], [3]]).trace(3)
    assert _links(result) == {(2, 3), (1, 2)}


def test_the_strongest_inputs_win_when_the_fan_in_is_capped():
    synapses = [(1, 0, 1.0), (2, 0, 9.0), (3, 0, 5.0)]
    result = _tracer(synapses, 4, [[1, 2, 3], [0]], fan_in=2).trace(0)
    assert _links(result) == {(2, 0), (3, 0)}


def test_nothing_recorded_means_nothing_traced():
    result = _tracer(CHAIN, 6, []).trace(3)
    assert result['edges'] == [] and result['reached_source'] is None


if __name__ == '__main__':
    for name, fn in sorted(globals().items()):
        if name.startswith('test_'):
            fn()
    print('ok')

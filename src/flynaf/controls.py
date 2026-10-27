from flynaf import config
from flynaf.neural.rewiring import shuffled_targets, without_outgoing
from flynaf.night.neurons import NeuronMap

SIDES = ('left', 'right')
TABLET_UP = config.SIMULATION_PARAMS.base_sensory_rate_hz
READOUTS = (('DNp01', 'giant_fiber'), ('DNp04', 'looming_escape'), ('DNp09', 'explore'))
CONDITIONS = (
    ('nothing on screen', {}),
    ('left hallway', {'left_rate': 1.0}),
    ('right hallway', {'right_rate': 1.0}),
    ('left hallway, tablet up', {'left_rate': 1.0, 'cam_inhib': TABLET_UP}),
    ('right hallway, tablet up', {'right_rate': 1.0, 'cam_inhib': TABLET_UP}),
    ('figure on 1C', {'cam_inhib': TABLET_UP, 'tablet_drive': {'figure_left': 0.5}}),
    ('figure on 4B', {'cam_inhib': TABLET_UP, 'tablet_drive': {'figure_right': 0.5}}),
    ('loom on 1C', {'cam_inhib': TABLET_UP,
                    'tablet_drive': {'loom_size_left': 0.5, 'loom_speed_left': 0.5}}),
)


def shuffled(seed: int):
    return lambda weights, _neurons: shuffled_targets(weights, seed)


def unwired(weights, _neurons):
    return weights * 0.0


def inhibitors_cut(weights, neurons: NeuronMap):
    return without_outgoing(weights, neurons.inputs['inhibitors_left'] + neurons.inputs['inhibitors_right'])


def crossed(name: str) -> str:
    for side, other in (('_left', '_right'), ('_right', '_left')):
        if name.endswith(side):
            return name[:-len(side)] + other
    return name


def eyes_swapped(neurons: NeuronMap) -> NeuronMap:
    return NeuronMap({crossed(name): indices for name, indices in neurons.inputs.items()}, neurons.outputs)


def readouts(engine) -> dict:
    outputs = engine.neurons.outputs
    return {f'{name} {side[0].upper()}': outputs[f'{role}_{side}'] for name, role in READOUTS for side in SIDES}

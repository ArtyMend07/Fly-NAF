from dataclasses import dataclass

from flynaf import config

SIDES = ('left', 'right')
STIMULUS_ROLES = ('eye', 'wide_field', 'figure', 'loom_size', 'loom_speed')
HALLWAY_ROLES = ('eye', 'wide_field')
READOUT_ROLES = ('giant_fiber', 'looming_escape', 'orientation', 'explore')


@dataclass(frozen=True)
class NeuronMap:
    inputs: dict
    outputs: dict

    def stimulus_indices(self) -> list:
        chosen = set()
        for role in STIMULUS_ROLES:
            for side in SIDES:
                chosen.update(self.inputs.get(f'{role}_{side}', ()))
        return sorted(chosen)

    def sizes(self) -> dict:
        return {name: len(indices) for name, indices in {**self.inputs, **self.outputs}.items()}


def build_neuron_map(cell_index, to_indices) -> NeuronMap:
    roles = config.CELL_POPULATIONS
    inhibitors = config.SENSORY_NEURONS
    inputs, outputs = {}, {}

    for side in SIDES:
        for role in STIMULUS_ROLES:
            types = getattr(roles, role)
            inputs[f'{role}_{side}'] = to_indices(
                cell_index.root_ids(types, side), f'{side} {"+".join(types)}',
            )
        for role in READOUT_ROLES:
            types = getattr(roles, role)
            outputs[f'{role}_{side}'] = to_indices(
                cell_index.root_ids(types, side), f'{side} {"+".join(types)}',
            )

    inputs['inhibitors_left'] = to_indices(inhibitors.camera_inhibitor_left, 'left camera inhibitors')
    inputs['inhibitors_right'] = to_indices(inhibitors.camera_inhibitor_right, 'right camera inhibitors')
    outputs['explore'] = to_indices(cell_index.root_ids(roles.explore), '+'.join(roles.explore))
    return NeuronMap(inputs, outputs)


def side_of(population: str) -> str:
    return population.rsplit('_', 1)[1]


def stimulus_rates(neurons: NeuronMap, state, base_rate_hz: float):
    graded = {side_of(population) for population in state.hallway_drive}
    for side in SIDES:
        if side in graded:
            continue
        rate = state.left_rate if side == 'left' else state.right_rate
        for role in HALLWAY_ROLES:
            yield neurons.inputs[f'{role}_{side}'], base_rate_hz * rate
    yield neurons.inputs['inhibitors_left'], state.cam_inhib
    yield neurons.inputs['inhibitors_right'], state.cam_inhib
    for population, level in (*state.hallway_drive.items(), *state.tablet_drive.items()):
        yield neurons.inputs[population], base_rate_hz * level

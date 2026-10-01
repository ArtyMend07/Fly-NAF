from dataclasses import dataclass

import config

SIDES = ('left', 'right')
STIMULUS_ROLES = ('eye', 'figure', 'loom_size', 'loom_speed')
READOUT_ROLES = ('giant_fiber', 'looming_escape')


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


def stimulus_rates(neurons: NeuronMap, state, base_rate_hz: float):
    yield neurons.inputs['eye_left'], base_rate_hz * state.left_rate
    yield neurons.inputs['eye_right'], base_rate_hz * state.right_rate
    yield neurons.inputs['inhibitors_left'], state.cam_inhib
    yield neurons.inputs['inhibitors_right'], state.cam_inhib
    for population, level in state.tablet_drive.items():
        yield neurons.inputs[population], base_rate_hz * level

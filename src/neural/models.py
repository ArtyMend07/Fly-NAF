import torch
import torch.nn as nn
import numpy as np

# ============================================================================
# PyTorch Model Parameters (matching Drosophila benchmark defaults)
# ============================================================================
MODEL_PARAMS = {
    'tauSyn': 5.0,        # ms
    'tDelay': 1.8,        # ms
    'v0': -52.0,          # mV
    'vReset': -52.0,      # mV
    'vRest': -52.0,       # mV
    'vThreshold': -45.0,  # mV
    'tauMem': 20.0,       # ms
    'tRefrac': 2.2,       # ms
    'scalePoisson': 250,
    'wScale': 0.275,
}

DT = 0.1  # Simulation timestep in ms

class PoissonSpikeGenerator(nn.Module):
    """Generates one timestep of Poisson-distributed spikes from firing rates."""

    def __init__(self, dt, scale, device='cpu'):
        super().__init__()
        self.prob_scale = dt / 1000.0
        self.scale = scale
        self.device = device

    def forward(self, rates, generator=None):
        return torch.bernoulli(rates * self.prob_scale, generator=generator) * self.scale


class AlphaSynapse(nn.Module):
    """Alpha-function synapse dynamics with configurable delay."""

    def __init__(self, batch, size, dt, params, device='cpu'):
        super().__init__()
        self.time_factor = dt / params['tauSyn']
        self.steps_delay = int(params['tDelay'] / dt)
        self.size = size
        self.device = device
        self.batch = batch

    def state_init(self):
        conductance = torch.zeros(self.batch, self.size, device=self.device)
        delay_buffer = torch.zeros(
            self.batch, self.steps_delay + 1, self.size, device=self.device
        )
        return conductance, delay_buffer

    def forward(self, input_, conductance, delay_buffer, refrac):
        conductance_new = (
            conductance * (1 - self.time_factor) + delay_buffer[:, 0, :] * refrac
        )
        delay_buffer = torch.roll(delay_buffer, shifts=-1, dims=1)
        delay_buffer[:, -1, :] = input_
        return conductance_new, delay_buffer


class LIFNeuron(nn.Module):
    """Leaky Integrate-and-Fire neuron with surrogate gradient (ATan)."""

    def __init__(self, batch, size, dt, params, device='cpu'):
        super().__init__()
        self.size = size
        self.dt = dt
        self.tau_mem = params['tauMem']
        self.v_reset = params['vReset']
        self.v_rest = params['vRest']
        self.v_threshold = params['vThreshold']
        self.v_0 = params['v0']
        self.time_factor = dt / self.tau_mem
        self.spike_gradient = self.ATan.apply
        self.device = device
        self.batch = batch

    def state_init(self):
        v = torch.zeros(self.batch, self.size, device=self.device) + self.v_0
        spikes = torch.zeros(self.batch, self.size, device=self.device)
        return spikes, v

    def forward(self, conductance, voltage_stim, v):
        v = v + voltage_stim
        v = v + self.time_factor * (conductance - (v - self.v_rest))

        spike = self.spike_gradient(v - self.v_threshold)

        reset = ((v - self.v_reset) * spike).detach()
        v = v - reset

        return spike, v

    @staticmethod
    class ATan(torch.autograd.Function):
        @staticmethod
        def forward(ctx, v):
            spike = (v > 0).float()
            ctx.save_for_backward(v)
            return spike

        @staticmethod
        def backward(ctx, grad_output):
            (v,) = ctx.saved_tensors
            grad = 1 / (1 + (np.pi * v).pow_(2)) * grad_output
            return grad


class AlphaLIF(nn.Module):
    """LIF neuron with alpha-function synapse dynamics and refractory period."""

    def __init__(self, batch, size, dt, params, exc_indices=None, device='cpu'):
        super().__init__()
        self.size = size
        self.synapse = AlphaSynapse(batch, size, dt, params, device=device)
        self.neuron = LIFNeuron(batch, size, dt, params, device=device)
        base_refrac = int(round(params['tRefrac'] / dt))

        self.refrac_steps = torch.full(
            (size,),
            base_refrac,
            dtype=torch.long,
            device=device,
        )

        if exc_indices is not None:
            self.refrac_steps[exc_indices] = 0

    def state_init(self):
        conductance, delay_buffer = self.synapse.state_init()
        spikes, v = self.neuron.state_init()
        refrac = self.refrac_steps.unsqueeze(0).repeat(self.neuron.batch, 1).float()
        return conductance, delay_buffer, spikes, v, refrac

    def forward(self, recurrent_input, voltage_stim, conductance, delay_buffer, spikes, v, refrac):
        refrac = torch.where(
            spikes > 0,
            torch.zeros_like(refrac),
            refrac + 1,
        )
        conductance_new, delay_buffer = self.synapse(
            recurrent_input,
            conductance,
            delay_buffer,
            (refrac >= self.refrac_steps.unsqueeze(0)).float()
        )

        spikes, v_new = self.neuron(
            conductance,
            voltage_stim,
            v
        )
        conductance_reset = (conductance_new * spikes).detach()
        conductance_new = conductance_new - conductance_reset
        return conductance_new, delay_buffer, spikes, v_new, refrac


class FlyBrainModel(nn.Module):
    def __init__(self, size, weights, exc_indices=None, device='cpu', batch=1):
        super().__init__()
        self.dt = DT
        self.device = device
        self.batch = batch
        self.size = size
        self.weights = weights
        
        self.neurons = AlphaLIF(
            batch,
            size,
            self.dt,
            MODEL_PARAMS,
            exc_indices=exc_indices,
            device=device
        )
        self.poisson = PoissonSpikeGenerator(self.dt, MODEL_PARAMS['scalePoisson'], device=device)
        self.scale = MODEL_PARAMS['wScale']
        
        self.conductance = None
        self.delay_buffer = None
        self.spikes = None
        self.v = None
        self.refrac = None

    def reset_state(self):
        self.conductance, self.delay_buffer, self.spikes, self.v, self.refrac = self.neurons.state_init()

    def step(self, sensory_rates):
        if self.conductance is None:
            self.reset_state()

        with torch.no_grad():
            poisson_spikes = self.poisson(sensory_rates)
            voltage_stim = self.scale * poisson_spikes

            weighted_spikes = torch.matmul(
                self.spikes,
                self.weights.transpose(0, 1)
            )
            recurrent_input = self.scale * weighted_spikes

            self.conductance, self.delay_buffer, self.spikes, self.v, self.refrac = self.neurons(
                recurrent_input,
                voltage_stim,
                self.conductance,
                self.delay_buffer,
                self.spikes,
                self.v,
                self.refrac,
            )
            
        return self.spikes

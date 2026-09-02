# 02. Phase 2 Signal Decay and Biological Inhibition

## Context
After successfully using Dijkstra's algorithm to map a 10-hop excitatory anatomical pathway from the sensory gateway (Index `69093`) to the motor cortex (Index `83620`), I removed the Phase 1 Biological Bypass from the main engine. 

When testing the visual integration in real-time, the vision threshold triggered perfectly, injecting a 10,000 Hz signal into the fly's sensory gateway. However, the motor neuron never fired, and the door never closed.

## The Experiment
To isolate the cause, I updated the structural bottleneck analyzer to focus exclusively on the exact 10-hop path discovered by Dijkstra. I ran a 5,000-timestep simulation locally using the following command:

```bash
uv run python src/scripts/analyze_pathways.py
```

## Results & The Concept of "Steps"
In computational neuroscience (specifically Leaky Integrate-and-Fire networks), a "step" represents a fraction of a millisecond of biological time. During a single step, a neuron accumulates electrical voltage. If the voltage crosses a threshold, it fires a spike, transferring voltage to the next neuron in the *next* step. 

The console output from the experiment proved a severe case of exponential biological decay:
- **Sensory Node (Step 0):** Fired 5,000 times (100% activation).
- **Interneuron (Step 1):** Fired 106 times (~2% activation).
- **Interneuron (Step 2):** Fired 0 times.
- **Motor Node (Step 10):** Fired 0 times.

## Conclusion
This is not a software bug, but a biological reality. The 15 million synapses in the connectome include massive inhibitory networks. Even though an excitatory anatomical wire exists, the synaptic weights are too weak to carry a chain reaction across 10 hops based on a single sensory node's input. The signal leaks and is biologically suppressed.

To overcome this, I must either simulate a chemical stimulant (globally multiplying synaptic weights) or mimic "Spatial Summation" by mapping a massive cluster of sensory neurons (e.g., 50+ nodes) to act as a single eye, overwhelming the inhibitory threshold through brute-force parallel signaling.

# ADR 0006: Biological Inhibition over Boolean Logic

## Status
Accepted

## Context
When the agent raises the camera tablet in the game, the screen is instantly obscured by a massive gray UI overlay. The LPLC2 visual neurons mathematically interpret this sudden visual change as a massive Looming Threat, which triggers a panic response through the Giant Fiber (DNp01), causing the fly to slam the door shut. 
The standard software engineering solution is to wrap the visual detection in a simple conditional check (`if not is_camera_up(): run_vision()`). However, this breaks the biological fidelity of the connectome simulation that I desire (in some way)...

## Decision
I decided to entirely reject boolean conditional locks due to the fact that if I can make the fly connectome faithful to their biological reality, I'll do it (unless its so difficult that it isn't worth it anymore). Therefore, I mined the FlyWire connectome for GABAergic interneurons (specifically LHAD1g1 cells) that physically synapse onto the Giant Fibers with high weight counts. 
When the camera tablet is raised, the sensory processing unit injects a 200 Hz stimulus directly into a cluster of 50 GABAergic neurons. These neurons naturally output negative voltage in the PyTorch `AlphaLIF` model, completely overriding the excitatory 200 Hz stimulus from the 50 LPLC2 visual neurons. The Giant Fiber threshold is never reached through pure tensor mathematics.

## Consequences
- **Positive:** Biological authenticity. The connectome resolves the conflict internally via Leaky Integrate-and-Fire mechanics without arbitrary software overrides.
- **Positive:** It validates the dataset. By pitting 50 top excitatory synapses against 50 top inhibitory synapses, the network correctly zeroes out.
- **Negative:** Requires deeper data mining (in this case, i had to extract the top 50 presynaptic GABA IDs) to ensure the spatial summation of the inhibitors can match the excitatory drive.

| Version | Description | Author(s) | Date | Reviewer(s) | Review Date |
|---|---|---|---|---|---|
| 1.0 | Initial ADR for biological inhibition | [Artur Mendonça Arruda](https://github.com/ArtyMend07) | 2026-09-07 | [Artur Mendonça Arruda](https://github.com/ArtyMend07) | 2026-09-07 |

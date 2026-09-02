# 0003. Biological Bypass of Sensory-Motor Pathways for Phase 1

## Status
Accepted

## Context
Phase 1 aims to prove the end-to-end integration of the FNAF game environment, the PyTorch biological tensor (138,000 neurons), and the Windows OS output. 
Initially, I mapped the visual stimulus (Bonnie at the door) to the Sugar GRN sensory neurons, expecting the signal to naturally propagate through the connectome and trigger the P9 motor neurons (walking/legs). 
A structural analysis via `analyze_pathways.py` revealed that despite injecting maximum biological saturation (10,000 Hz, equating to 1.0 probability per step) into the Sugar GRNs, the signal died out within the interneuron network. Out of 138,639 neurons, only 617 fired, and 0 spikes reached the motor cortex. The natural inhibitory mechanisms of the fly's brain block this specific artificial reflex.

## Decision
For Phase 1 (Proof of Concept), I will enact a "Biological Bypass". The OpenCV visual stimulus will bypass the sensory apparatus entirely and inject its firing rate directly into the P9 motor neurons (`motor_indices`). 

## Consequences
**Positive:**
- Immediately validates the structural pipeline (`vision.py` -> `main.py` -> `input_controller.py`) in real-time gameplay.
- Proves that the PyTorch engine can run at 30+ FPS synchronously with game inputs.

**Negative:**
- Philosophically breaks the premise of "playing the game through the mind of a fly", as I am just puppeteering the motor cortex.
- Mandates the creation of Phase 2 (Graph Search), where I must programmatically mine the 100MB parquet connectome to discover which actual sensory neurons possess unobstructed excitatory pathways to the motor cortex.

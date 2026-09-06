# Experiment 04: Sensory Overload and Emergent Motor Spasms

## Objective
To analyze the motor output of the Giant Fiber when the LPLC2 projection neurons are subjected to a massive, continuous sensory disruption.

## Methodology
During some of the testing, while trying to validate foraging loop, a timing desynchronization occurred. The visual baseline was captured outside of the game environment. Upon entering the game, the Mean Squared Error between the baseline and the live game feed exceeded 7,000. 

This continuous global visual variance caused the simulated sensory neurons to drive the fly crazy.

## Observations
The spatial summation of 50 LPLC2 neurons firing at 200Hz created a runaway excitatory cascade through the connectome. The resulting behavior was highly revealing of the biological limitations of the network:
1. **Bilateral Panic:** Both the Left and Right Giant Fibers fired simultaneously and continuously.
2. **Motor Spasms:** Because the PyTorch simulation lacked a biophysical refractory period at the neuromuscular junction, the Giant Fibers spammed the output command.
3. **Environmental Sabotage:** In the context of FNAF, doors operate on a toggle switch. The motor spasms caused the system to rapidly double-click the doors, essentially opening and closing them in an infinite loop, rendering the defense mechanism useless.

## Input and Panning Quirks
I also noticed the fly seemed extremely rigid when turning its head, and sometimes it failed to click the light button altogether. It turns out the game engine (Clickteam Fusion) polls inputs at 60Hz, so my original 20ms click was occasionally getting swallowed by the game frame rate. I bumped the click duration to around 100ms just to be safe.

Additionally, the game takes a fraction of a second to pan the camera left or right. Giving the fly a universal 1.2s delay for every action made it too slow to defend itself. I ended up separating the logic: turning the head gets a 1.2s delay to let the camera settle, but hitting a button on the side it's already looking at is almost instantaneous.

## Conclusion and Biophysical Correction
The observed behavior seems biologically accurate for a nervous system lacking synaptic depletion. 

To maintain biological authenticity, I might have to implement some sort of Synaptic Depression at the motor output layer. A strict cooldown would likely simulate enough the time required for the Giant Fiber to biologically reset before it can issue another escape command.

| Version | Description | Author(s) | Date | Reviewer(s) | Review Date |
|---------|-------------|-----------|------|-------------|-------------|
| 1.0 | Initial documentation of sensory overload spasms | [Artur Mendonça Arruda](https://github.com/ArtyMend07) | 2026-09-06 | [Artur Mendonça Arruda](https://github.com/ArtyMend07) | 2026-09-06 |


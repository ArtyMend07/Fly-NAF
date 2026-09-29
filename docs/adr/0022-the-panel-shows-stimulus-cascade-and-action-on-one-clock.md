# ADR 0022: The Panel Shows Stimulus, Cascade And Action On One Clock

## Status
Accepted. Extends ADR 0009 on where the panel sits and ADR 0016 on how the cloud is drawn.

## Context
The panel showed every neuron glowing when it fired, and nothing in it connected that glow to the game. A viewer saw a cloud and a door closing and had to take the link on trust. Any emphasis added by hand, such as a flash when the door closes or a camera move toward the escape circuit, would make the problem worse, because an effect keyed to the game reads as staged even when the brain really caused the door.

Laboratories that show a brain and a behaviour together solve the same problem by putting the stimulus, the neural recording and the motor output on one time axis. The closest case is the fictively behaving larval zebrafish, which is immobilised in front of a projected world while its motor nerve is read out and the whole brain is imaged (Vladimirov et al., Nature Methods 2014). The fly here is in the same position, with Five Nights at Freddy's as the projected world. Whole-brain imaging of freely moving worms and fish is presented the same way (Nguyen et al., PNAS 2016; Cong et al., eLife 2017). Browser viewers of the FlyWire connectome such as fly-with-a-real-brain draw the spikes as a glow with an exponential tail and the synapses that carried them as lines, restricted to pairs where the presynaptic neuron fired first.

What the model actually receives constrains what the panel may claim. Each hallway is one screen patch, compared against a reference, and the comparison is binary. When the mean squared error passes `mse_threshold` while the light on that side is on, the 50 neurons of that side's eye cluster are driven. There is no retinotopic image. A panel that painted the whole screen through a compound eye filter would claim a visual system the model does not have.

## Decision
The panel shows three bands, and every element in them is a readout of a variable the simulation already holds. None of them is triggered by game state.

The stimulus band shows each hallway patch as it was last captured, the error against the threshold, and whether the input reaching the eye cluster is on. It is greyed out while that side's light is off, because the eye is then not read at all.

The brain band keeps the cloud of ADR 0016 with the glow decay moved to the GPU, where each neuron stores the time of its last spike and the shader computes the tail. When a DNp01 spike passes the motor refractory, which is the same spike the motor loop reads, `CascadeTracer` walks backwards from it through the connectome. From each neuron it follows the excitatory synapses whose presynaptic neuron fired in the same frame or the frame before, keeps the three strongest, and continues from those neurons, over the last 16 frames and up to 160 synapses. A frame is two steps of one millisecond and the synaptic delay is one millisecond, so at most one hop can fall inside a frame, and the walk allows exactly that. The page replays the trace over the real soma positions, pulse by pulse in the order the spikes happened, 150 times slower than simulated time, and says so on screen. A caption gives the number of synapses, the depth in frames and in simulated milliseconds, whether the trace reached the eye cluster and how many frames before, and whether the spike moved the door, found it already shut, or met the tablet.

The timeline band plots the last 20 seconds for each side, light and input, eye cluster spikes, DNp01 spikes and the door, plus the tablet and the share of the whole brain firing. Each traced cascade is marked as a bracket spanning the frames it covers, so the delay between the eye and the door can be read off the axis.

When the game runs in a window, the full panel sits beside it at the height of the game, so a single screen recording holds the game and the brain. The in-game corner overlay remains for a game that fills the screen.

## Consequences
The replay differs every time, because it is computed from the spikes of that moment. It also shows the cases that a staged effect would hide, including DNp01 spikes with no input, where the trace does not reach the eye cluster, and spikes that arrive with the door already shut. A first run against the real connectome with the left input driven produced traces reaching the eye cluster two to four frames before the spike, and one spontaneous spike whose trace did not reach it at all.

The trace shows contribution and not proof of causation. A presynaptic neuron that fired just before is drawn whether or not the target would have fired without it, the cap on fan in hides weaker inputs, and inhibitory inputs are counted in the caption data but not drawn. The caption words it as synapses that fired in order for this reason.

The replay is only as honest as the soma positions under it. The panel reads the FlyWire Codex positions by root id and draws the FlyWire brain surface from navis-flybrains in the same frame, as a translucent shell lit at its silhouette. The earlier soma file carried unrelated coordinates, which experiment 12 records, so every panel before this revision placed each neuron where another one should be.

The tracer keeps a CPU copy of the weight matrix, about 120 MB, and one boolean mask per frame. A trace took between 6 and 14 ms against the full connectome with up to 5% of neurons firing, and it runs after the door click has been issued, at most once per motor refractory per side, so it cannot delay the reflex. Nothing in the engine reads from the panel, so the behaviour is unchanged.

| Version | Description | Author(s) | Date | Reviewer(s) | Review Date |
|---|---|---|---|---|---|
| 1.0 | Recorded the stimulus, cascade and timeline bands and the rule that only simulation variables drive them | [Artur Mendonça Arruda](https://github.com/ArtyMend07) | 2026-09-28 | [Artur Mendonça Arruda](https://github.com/ArtyMend07) | 2026-09-28 |
| 1.1 | Added the brain outline and recorded that positions are read by root id | [Artur Mendonça Arruda](https://github.com/ArtyMend07) | 2026-09-29 | [Artur Mendonça Arruda](https://github.com/ArtyMend07) | 2026-09-29 |

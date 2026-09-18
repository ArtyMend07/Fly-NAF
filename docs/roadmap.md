# FNAF Fly Brain Connectome: Project Roadmap

This document outlines the strategic phases for the cybernetic integration of the *Drosophila melanogaster* connectome with the interactive environment of Five Nights at Freddy's.

## Phase 1: Proof of Concept & Infrastructure
**Status:** Completed
**Objective:** Validate the technical bridge between the game environment, computer vision, biological simulation, and the operating system.
**Scope:**
- Real-time screen capture via OpenCV.
- Tensor injection into the PyTorch simulation engine.
- Low-level OS mouse control via Win32 ctypes.
- Implemented a temporary biological bypass (ADR 0003) to inject visual stimuli directly into the motor cortex due to signal decay in default sensory pathways.

## Phase 2: Biological Graph Routing
**Status:** Pending
**Objective:** Replace the artificial bypass with anatomically accurate neural pathways.
**Scope:**
- Parse the 100MB sparse connectivity matrix.
- Implement Dijkstra's algorithm to compute the shortest and most excitatory paths from sensory clusters to motor output nodes.
- Map the four primary game inputs to the discovered biological sensory nodes, ensuring stimuli propagate naturally through the connectome to trigger the required motor reflexes.

## Phase 3: Autonomous Cybernetic Survival
**Status:** Pending
**Objective:** Establish full autonomy driven by biological constraints and game state translation.
**Scope:**
- Inject constant low-level stimuli to induce exploratory behavior (randomized viewport checking).
- Implement computer vision tracking for in-game power levels.
- Translate battery depletion into simulated biological fatigue by dampening the firing rates dynamically.
- Prove embodied connectomics by forcing the biological network to manage digital resources under stress.

| Version | Description | Author(s) | Date | Reviewer(s) | Review Date |
|---------|-------------|-----------|------|-------------|-------------|
| 1.0 | Initial version | [Artur Mendonça Arruda](https://github.com/ArtyMend07) | 2026-09-02 | [Artur Mendonça Arruda](https://github.com/ArtyMend07) | 2026-09-02 |
| 1.1 | ADR reference style aligned with the rest of the documentation | [Artur Mendonça Arruda](https://github.com/ArtyMend07) | 2026-09-18 | [Artur Mendonça Arruda](https://github.com/ArtyMend07) | 2026-09-18 |
